export interface CypherQuery {
  cypher: string
  params: Record<string, unknown>
}

export interface DebugInfo {
  level: number
  intents: string[]
  entities: Record<string, string[]>
  cypher_queries: CypherQuery[]
  result_count: number
}

export interface GraphNode {
  id: string
  label: string
}

export interface GraphEdge {
  source: string
  target: string
  label: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface ChatResponse {
  answer: string
  debug: DebugInfo
  graph_data: GraphData
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  debug?: DebugInfo
  graph_data?: GraphData
}

// ---- GraphRAG ----
export interface GraphRAGDebugInfo {
  entities_raw: Array<{ name: string; type: string }>
  entities_normalized: Record<string, string[]>
  subgraph_stats: {
    total_nodes: number
    total_edges: number
    retrieval_time_ms: number
  }
  context_preview: string
  context_char_count: number
  generation_time_ms: number
  model_used: string
  total_time_ms: number
}

export interface GraphRAGChatMessage {
  role: 'user' | 'assistant'
  content: string
  debug?: GraphRAGDebugInfo
  graph_data?: GraphData
  mode?: string
}

/** 统一聊天消息（模板 / GraphRAG 由后端自动路由） */
export interface UnifiedMessage {
  role: 'user' | 'assistant'
  content: string
  mode?: string
  /** LLM 模型名（仅 LLM 兜底路径有值） */
  llm_model?: string
  /** 当前路由阶段（status 事件推送，用于前端显示进度） */
  status_stage?: string
  /** 当前阶段提示文本（status 事件推送） */
  status_message?: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  debug?: any
  graph_data?: GraphData
}

/** SSE done 事件载荷（qa_engine stream_qa） */
export interface StreamDoneData {
  answer: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  debug: any
  graph_data: GraphData
  mode: string
  /** LLM 模型名（仅 LLM 兜底路径有值，用于前端动态标签） */
  llm_model?: string
  session_id?: string
  total_time_ms?: number
}

export interface ChatStreamRequest {
  question: string
  session_id?: string
}
