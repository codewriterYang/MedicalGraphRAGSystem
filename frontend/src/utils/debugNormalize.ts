import type { CypherQuery, DebugInfo, GraphRAGDebugInfo } from '@/types'

/** 后端 qa_engine stream done 事件中的原始 debug（两类字段可能混在一起） */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type EngineDebugRaw = Record<string, any>

/** 模板路径 → DebugPanel 所需格式 */
function toTemplateDebug(raw: EngineDebugRaw): DebugInfo {
  const level = raw.analysis_level ?? raw.level ?? 0
  return {
    level: typeof level === 'number' ? level : Number(level) || 0,
    intents: Array.isArray(raw.intents) ? raw.intents : [],
    entities: raw.entities ?? {},
    cypher_queries: (raw.cypher_queries as CypherQuery[]) ?? [],
    result_count: typeof raw.result_count === 'number' ? raw.result_count : 0,
  }
}

/** GraphRAG 路径 → GraphRAGDebugPanel 所需格式 */
function toGraphRAGDebug(raw: EngineDebugRaw): GraphRAGDebugInfo {
  const entitiesRaw = raw.entities_raw
  const normalized = raw.entities_normalized ?? raw.entities ?? {}

  return {
    entities_raw: Array.isArray(entitiesRaw) ? entitiesRaw : [],
    entities_normalized: normalized,
    subgraph_stats: raw.subgraph_stats ?? {},
    context_preview: String(raw.context_preview ?? ''),
    context_char_count:
      typeof raw.context_char_count === 'number' ? raw.context_char_count : 0,
    generation_time_ms:
      typeof raw.generation_time_ms === 'number' ? raw.generation_time_ms : 0,
    model_used: String(raw.model_used ?? 'langgraph_engine'),
    total_time_ms: typeof raw.total_time_ms === 'number' ? raw.total_time_ms : 0,
  }
}

/**
 * 根据后端路由 mode 从统一 debug 中提取对应字段。
 * - template: analysis_level → level, intents, entities, cypher_queries, result_count
 * - graphrag: entities_raw, entities_normalized, subgraph_stats, context_preview 等
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeDebug(debug: any, mode: string): DebugInfo | GraphRAGDebugInfo {
  const raw: EngineDebugRaw = debug && typeof debug === 'object' ? debug : {}
  const route =
    mode ||
    (String(raw.route) === 'graphrag' ? 'graphrag' : 'template')

  return route === 'graphrag' ? toGraphRAGDebug(raw) : toTemplateDebug(raw)
}

export function isGraphRAGRoute(mode?: string | null): boolean {
  return mode === 'graphrag'
}
