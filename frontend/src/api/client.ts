import type { ChatResponse, GraphData, StreamDoneData, ChatStreamRequest } from '@/types'

/** 浏览器端固定会话 ID（多轮对话，与后端 MemorySaver 线程绑定） */
export const WEB_SESSION_ID = 'web-session'

const BASE = '/api'

export async function sendChat(question: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  return res.json()
}

export async function fetchNeighbors(name: string, limit = 50): Promise<{ center: string; graph_data: GraphData }> {
  const res = await fetch(`${BASE}/graph/neighbors/${encodeURIComponent(name)}?limit=${limit}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  return res.json()
}

// ---------------------------------------------------------------------------
// SSE 流式接口
// ---------------------------------------------------------------------------
export interface StatusData {
  stage: string  // template | graphrag | template_to_graphrag | llm
  message: string
}

export interface SSECallbacks {
  /** 旧 ChatBot 在检索完成时推送；新引擎在 done 中一并返回 */
  onRetrieval?: (data: { debug: unknown; graph_data: GraphData; mode?: string }) => void
  onDelta?: (chunk: string) => void
  /** 路由阶段状态（前端展示进度标签和提示） */
  onStatus?: (data: StatusData) => void
  onDone?: (data: StreamDoneData) => void
  onError?: (err: Error) => void
}

async function consumeSSE(
  url: string,
  payload: ChatStreamRequest,
  cb: SSECallbacks,
) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    cb.onError?.(new Error(`请求失败: ${res.status}`))
    return
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })

    const parts = buf.split('\n\n')
    buf = parts.pop()!
    for (const part of parts) {
      let event = ''
      let data = ''
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (!event || !data) continue
      try {
        const parsed = JSON.parse(data)
        if (event === 'retrieval') {
          cb.onRetrieval?.(parsed)
        } else if (event === 'delta') {
          cb.onDelta?.(parsed.chunk)
        } else if (event === 'status') {
          cb.onStatus?.(parsed)
        } else if (event === 'done') {
          cb.onDone?.(parsed as StreamDoneData)
        } else if (event === 'error') {
          cb.onError?.(new Error(parsed.message ?? '未知错误'))
        }
      } catch { /* 忽略解析错误 */ }
    }
  }
}

/** 统一流式问答（后端自动路由 template / graphrag） */
export function streamChat(
  question: string,
  cb: SSECallbacks,
  sessionId: string = WEB_SESSION_ID,
) {
  return consumeSSE(
    `${BASE}/chat/stream`,
    { question, session_id: sessionId },
    cb,
  )
}
