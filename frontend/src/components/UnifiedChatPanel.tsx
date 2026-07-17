import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { streamChat, WEB_SESSION_ID, type StatusData } from '@/api/client'
import type { GraphData, StreamDoneData, UnifiedMessage } from '@/types'
import { normalizeDebug } from '@/utils/debugNormalize'
import { Send, Loader2 } from 'lucide-react'

interface Props {
  onResponse: (msg: UnifiedMessage) => void
}

/** 根据 mode/status_stage + llm_model 动态生成标签文本 */
function getModeLabel(
  mode: string,
  llmModel?: string,
): { text: string; className: string } {
  const modelName = llmModel || 'AI'
  const llmClass = 'bg-indigo-50 text-indigo-700 border-indigo-200'
  const blue = 'bg-blue-50 text-blue-700 border-blue-200'
  const green = 'bg-emerald-50 text-emerald-700 border-emerald-200'

  const gray = 'bg-gray-50 text-gray-600 border-gray-200'
  // 中间状态（status 事件 stage）和最终路由（done 事件 mode）统一处理
  switch (mode) {
    case 'analyze':
      return { text: '分析问题', className: gray }
    case 'template':
      return { text: '模板检索', className: green }
    case 'graphrag':
      return { text: 'GraphRAG', className: blue }
    case 'template_to_graphrag':
      return { text: '模板检索 → GraphRAG', className: blue }
    case 'template_to_llm':
      return { text: `模板检索 → ${modelName} 回答`, className: llmClass }
    case 'llm':
    case 'llm_fallback':
      return { text: `${modelName} 回答`, className: llmClass }
    case 'graphrag_to_llm':
      return { text: `GraphRAG → ${modelName} 回答`, className: llmClass }
    case 'template_to_graphrag_to_llm':
      return { text: `模板检索 → GraphRAG → ${modelName} 回答`, className: llmClass }
    default:
      return { text: mode, className: 'bg-muted text-muted-foreground border-muted' }
  }
}

function handleStreamMeta(
  data: { debug?: unknown; graph_data?: GraphData; mode?: string; llm_model?: string },
  onResponse: Props['onResponse'],
): { mode: string; debug: ReturnType<typeof normalizeDebug>; graph_data?: GraphData; llm_model?: string } | null {
  if (!data.debug) return null
  const mode = data.mode ?? 'template'
  const debug = normalizeDebug(data.debug, mode)
  onResponse({
    role: 'assistant',
    content: '',
    debug,
    graph_data: data.graph_data,
    mode,
    llm_model: data.llm_model,
  })
  return { mode, debug, graph_data: data.graph_data, llm_model: data.llm_model }
}

export default function UnifiedChatPanel({ onResponse }: Props) {
  const [messages, setMessages] = useState<UnifiedMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  /** 与后端 LangGraph MemorySaver 绑定的会话线程 */
  const sessionId = WEB_SESSION_ID
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(async () => {
    const q = input.trim()
    if (!q || loading) return

    const userMsg: UnifiedMessage = { role: 'user', content: q }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    const botIdx = { current: -1 }
    setMessages(prev => {
      botIdx.current = prev.length
      return [...prev, { role: 'assistant', content: '' }]
    })

    let lastMeta: ReturnType<typeof handleStreamMeta> = null

    try {
      await streamChat(q, {
        // 旧 ChatBot 兼容；新引擎不发 retrieval
        onRetrieval(data) {
          lastMeta = handleStreamMeta(data, onResponse)
          if (!lastMeta) return
          setMessages(prev => {
            const updated = [...prev]
            const msg = updated[botIdx.current]
            if (msg) {
              updated[botIdx.current] = {
                ...msg,
                mode: lastMeta!.mode,
                debug: lastMeta!.debug,
                graph_data: lastMeta!.graph_data,
              }
            }
            return updated
          })
        },
        onDelta(chunk) {
          setMessages(prev => {
            const updated = [...prev]
            const msg = updated[botIdx.current]
            if (msg) {
              // 只有进入 LLM 兜底阶段才开始追加内容，清空前期分析阶段的中间输出
              const prevContent = msg.status_stage === 'llm' ? msg.content : ''
              updated[botIdx.current] = { ...msg, content: prevContent + chunk }
            }
            return updated
          })
        },
        onStatus(data: StatusData) {
          setMessages(prev => {
            const updated = [...prev]
            const msg = updated[botIdx.current]
            if (msg) {
              updated[botIdx.current] = {
                ...msg,
                status_stage: data.stage,
                status_message: data.message,
                // 进入 LLM 阶段时清空之前 LLM 分析阶段泄漏的垃圾内容
                content: data.stage === 'llm' ? '' : msg.content,
              }
            }
            return updated
          })
        },
        onDone(data: StreamDoneData) {
          lastMeta = handleStreamMeta(data, onResponse)
          setMessages(prev => {
            const updated = [...prev]
            const msg = updated[botIdx.current]
            if (msg) {
              updated[botIdx.current] = {
                ...msg,
                content: data.answer || msg.content,
                mode: lastMeta?.mode ?? data.mode,
                llm_model: lastMeta?.llm_model ?? data.llm_model,
                debug: lastMeta?.debug,
                graph_data: lastMeta?.graph_data ?? data.graph_data,
              }
            }
            return updated
          })
        },
        onError(err) {
          setMessages(prev => {
            const updated = [...prev]
            updated[botIdx.current] = {
              role: 'assistant',
              content: `请求失败: ${err.message}`,
            }
            return updated
          })
        },
      }, sessionId)
    } catch (e) {
      setMessages(prev => {
        const updated = [...prev]
        updated[botIdx.current] = {
          role: 'assistant',
          content: `请求失败: ${e instanceof Error ? e.message : '未知错误'}`,
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }, [input, loading, onResponse])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 min-h-0 p-4">
        <div className="space-y-3">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground py-16">
              <p className="text-sm leading-relaxed">
                系统自动路由模板检索 / GraphRAG / LLM 兜底，支持疾病、症状、食物等多类医疗问题
              </p>
              <p className="text-sm mt-2 text-muted-foreground/60">
                试试：感冒有什么症状？ / 糖尿病和高血压有什么共同并发症？ / 布洛芬有哪些副作用？
              </p>
            </div>
          )}

          {messages.map((msg, i) => {
            const isLastAssistant = msg.role === 'assistant' && i === messages.length - 1
            const isStreaming = isLastAssistant && loading
            // 关键：只有进入 LLM 阶段后的内容才认为是"有效内容"
            const hasValidContent = !!msg.content && msg.status_stage === 'llm'
            const hasStatus = !!msg.status_stage
            return (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <Card
                className={`max-w-[80%] px-4 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary'
                }`}
              >
                {/* Badge：已完成 → 用 mode；进行中 → 用 status_stage */}
                {msg.role === 'assistant' && (
                  ((!isStreaming && msg.mode) || (isStreaming && hasStatus)) && (
                  <div className="mb-1">
                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        getModeLabel(
                          !isStreaming && msg.mode ? msg.mode : (msg.status_stage || ''),
                          msg.llm_model
                        ).className
                      }`}
                    >
                      {getModeLabel(
                        !isStreaming && msg.mode ? msg.mode : (msg.status_stage || ''),
                        msg.llm_model
                      ).text}
                    </Badge>
                  </div>
                ))}

                {isStreaming && !hasValidContent ? (
                  /* 阶段进行中：转圈 + 提示文字（默认显示模板检索，收到 status 后更新） */
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-xs text-muted-foreground">
                      {msg.status_message || '正在分析问题...'}
                    </span>
                  </div>
                ) : (
                  /* 有有效内容：流式输出 或 最终答案 */
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">
                    {msg.content}
                    {isStreaming && hasValidContent && (
                      <span className="inline-block w-2 h-4 ml-0.5 bg-foreground/30 animate-pulse align-middle" />
                    )}
                  </p>
                )}
              </Card>
            </div>
          )})}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="p-4 border-t flex gap-2">
        <Input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入医疗问题，如：感冒有什么症状？"
          disabled={loading}
          className="flex-1"
        />
        <Button onClick={handleSend} disabled={loading || !input.trim()} size="icon">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  )
}
