# API 契约 (API Contract)

版本：v1.0.0 | 状态：Current（描述当前代码实际状态）

---

## 1. 端点总览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 统一非流式问答 |
| POST | `/api/chat/stream` | 统一 SSE 流式问答（推荐） |
| GET | `/api/graph/neighbors/{name}` | 节点邻居查询 |
| GET | `/api/health` | 健康检查 |

---

## 2. 请求模型

### 2.1 ChatRequest

```json
{
  "question": "感冒有什么症状？",
  "session_id": "web-session"
}
```

| 字段 | 类型 | 必填 | 约束 | 说明 |
|------|------|------|------|------|
| `question` | string | 是 | 1-500 字符 | 用户问题 |
| `session_id` | string | 否 | ≤128 字符 | 会话 ID，不传则服务端生成 UUID |

---

## 3. 响应模型

### 3.1 ChatResponse（非流式 `/api/chat`）

```json
{
  "answer": "感冒的主要症状包括...",
  "debug": {
    "level": 1,
    "intents": ["disease_symptom"],
    "entities": {"disease": ["感冒"]},
    "cypher_queries": [
      {"cypher": "MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) WHERE m.name = $name RETURN m.name, r.name, n.name", "params": {"name": "感冒"}}
    ],
    "result_count": 5
  },
  "graph_data": {
    "nodes": [{"id": "感冒", "label": "Disease"}, {"id": "咳嗽", "label": "Symptom"}],
    "edges": [{"source": "感冒", "target": "咳嗽", "label": "症状"}]
  },
  "session_id": "web-session"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer` | string | 最终回答文本 |
| `debug.level` | int | 降级等级：1=全LLM, 2=LLM实体+关键词, 3=离线NER |
| `debug.intents` | string[] | 识别的意图列表 |
| `debug.entities` | dict | 归一化实体（类型→名称列表） |
| `debug.cypher_queries` | object[] | 执行的 Cypher 查询 |
| `debug.result_count` | int | 查询结果数量 |
| `graph_data.nodes` | object[] | 图谱节点 `{id, label}` |
| `graph_data.edges` | object[] | 图谱边 `{source, target, label}` |
| `session_id` | string | 本次会话 ID |

---

## 4. SSE 流式事件协议（`/api/chat/stream`）

### 4.1 事件类型

| event | 载荷 | 触发时机 |
|-------|------|----------|
| `status` | `{stage, message}` | 路由阶段切换 |
| `delta` | `{chunk}` | LLM 生成每个 token |
| `done` | `{answer, debug, graph_data, mode, llm_model, session_id}` | 工作流完成 |
| `error` | `{message}` | 发生异常 |

### 4.2 status 事件

```
event: status
data: {"stage": "analyze", "message": "正在分析问题..."}
```

| stage 值 | 说明 |
|----------|------|
| `analyze` | 分析问题中 |
| `template` | 模板检索中 |
| `graphrag` | 子图检索中 |
| `template_to_graphrag` | 模板无匹配，切换子图检索 |
| `llm` | AI 模型兜底生成中 |

### 4.3 delta 事件

```
event: delta
data: {"chunk": "感冒"}
```

### 4.4 done 事件

```
event: done
data: {
  "answer": "感冒的主要症状包括...",
  "debug": {
    "analysis_level": 1,
    "route": "template",
    "intents": ["disease_symptom"],
    "entities": {"disease": ["感冒"]},
    "cypher_queries": [...],
    "result_count": 5,
    "nodes": [...],
    "total_time_ms": 850.2
  },
  "graph_data": {"nodes": [...], "edges": [...]},
  "mode": "template",
  "llm_model": "",
  "session_id": "web-session"
}
```

| mode 值 | 说明 |
|---------|------|
| `template` | 模板检索直接成功 |
| `graphrag` | GraphRAG 子图检索成功 |
| `template_to_graphrag` | 模板无结果 → GraphRAG 回退成功 |
| `llm_fallback` | 直接 LLM 兜底 |
| `graphrag_to_llm` | GraphRAG 不足 → LLM 兜底 |
| `template_to_graphrag_to_llm` | 模板→GraphRAG→LLM 三级回退 |

### 4.5 error 事件

```
event: error
data: {"message": "流式问答服务异常: ..."}
```

---

## 5. 邻居查询

### 请求

```
GET /api/graph/neighbors/{name}?limit=50
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | (必填) | 节点名称（URL 编码） |
| `limit` | int | 50 | 返回邻居数量上限 |

### 响应

```json
{
  "center": "感冒",
  "graph_data": {
    "nodes": [
      {"id": "感冒", "label": "Disease"},
      {"id": "咳嗽", "label": "Symptom"}
    ],
    "edges": [
      {"source": "感冒", "target": "咳嗽", "label": "has_symptom"}
    ]
  }
}
```

---

## 6. 健康检查

### 请求

```
GET /api/health
```

### 响应

```json
{
  "status": "ok",
  "neo4j": true,
  "ollama": true,
  "graphrag": true
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `ok` 或 `degraded` |
| `neo4j` | bool | Neo4j 连通性 |
| `ollama` | bool | LLM 可用性 |
| `graphrag` | bool | qa_engine 工作流可构建 |

---

## 7. 错误码

| HTTP 状态码 | 场景 |
|-------------|------|
| 200 | 正常响应 |
| 422 | 请求参数校验失败（Pydantic） |
| 500 | 服务内部错误（Neo4j 连接失败等） |

---

## 8. CORS

开发模式允许所有来源，生产模式通过 `ALLOWED_ORIGINS` 环境变量限制：

```env
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

---

## 9. 变更规则

- 新增字段：允许
- 删除字段：禁止
- 修改字段类型：禁止
- 修改 Endpoint 路径：禁止
- 需要破坏性修改时：创建新版本（如 `/api/v2/chat`）
