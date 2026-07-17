# backend/api — FastAPI Web 服务

## 概述

`backend/api` 层提供 **REST API + SSE 流式接口**，将底层 `qa_engine` 问答能力封装为 HTTP 服务，供 `frontend/` React 前端消费。同时提供图谱邻居查询和健康检查。

---

## API 端点

### 问答接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 统一问答（非流式），返回完整答案 |
| `/api/chat/stream` | POST | 统一问答（SSE 流式），逐字返回 |
| `/api/graphrag/chat` | POST | GraphRAG 问答（兼容路径，引擎内部自动路由） |
| `/api/graphrag/chat/stream` | POST | GraphRAG 流式问答（兼容路径） |

### 图谱接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/graph/neighbors/{name}?limit=50` | GET | 查询指定节点的邻居（前端图谱探索） |

### 运维接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查（Neo4j + LLM + qa_engine 可用性） |

---

## 请求/响应模型

### ChatRequest

```json
{
  "question": "感冒有什么症状？",
  "session_id": "web-session"
}
```

### ChatResponse（非流式）

```json
{
  "answer": "感冒的主要症状包括...",
  "debug": {
    "level": 1,
    "intents": ["disease_symptom"],
    "entities": {"disease": ["感冒"]},
    "cypher_queries": [...],
    "result_count": 5
  },
  "graph_data": {
    "nodes": [...],
    "edges": [...]
  },
  "session_id": "web-session"
}
```

### SSE 流式事件

```
event: delta
data: {"chunk": "感冒"}

event: delta
data: {"chunk": "的主要"}

...

event: done
data: {"answer": "感冒的主要症状...", "debug": {...}, "graph_data": {...}, "mode": "template", "session_id": "web-session"}
```

---

## 日志

```
2025-06-01 18:00:00 server INFO ChatBot 初始化完成（用于邻居查询和健康检查，问答已由 qa_engine 接管）
```

日志级别通过 Python `logging` 控制：

```bash
python -m backend.api.app --port 8000 2>&1 | grep -E "server|qa_engine"
```

---

## 目录结构

```
backend/api/
├── __init__.py        # 包初始化（空文件）
├── app.py             # FastAPI 应用 + 路由 + CLI 入口
│                      #   - lifespan: 启动时初始化 ChatBot
│                      #   - /api/chat: 统一非流式问答
│                      #   - /api/chat/stream: SSE 流式问答
│                      #   - /api/graph/neighbors: 邻居查询
│                      #   - /api/health: 健康检查
├── models.py          # Pydantic 请求/响应模型
│                      #   - ChatRequest / ChatResponse
│                      #   - GraphRAGChatResponse
│                      #   - NeighborResponse
│                      #   - HealthResponse
│                      #   - DebugInfo / GraphData / CypherQuery
└── qa_response.py     # 响应转换工具
                       #   - done_to_chat_response()
                       #   - done_to_graphrag_response()
```

---

## 启动

```bash
# 默认启动
python -m backend.api.app

# 自定义端口
python -m backend.api.app --port 8080

# 自定义 Neo4j 和 LLM
python -m backend.api.app \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-password your_password \
  --llm-model deepseek-ai/DeepSeek-V4-Pro
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `0.0.0.0` | 监听地址 |
| `--port` | `8000` | 监听端口 |
| `--neo4j-uri` | 来自 `.env` | Neo4j 连接地址 |
| `--neo4j-user` | 来自 `.env` | Neo4j 用户名 |
| `--neo4j-password` | 来自 `.env` | Neo4j 密码 |
| `--llm-provider` | 来自 `.env` | LLM 提供商 (ollama/openai/anthropic) |
| `--llm-model` | 来自 `.env` | LLM 模型名 |
| `--answer-mode` | `template` | 答案模式 (template/llm) |

---

## 与前端的关系

React 前端（`frontend/`）通过 Vite 代理将 `/api` 请求转发至 `http://localhost:8000`：

```typescript
// frontend/vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

生产模式：前端 `npm run build` 后，FastAPI 自动挂载 `frontend/dist/` 为静态文件。

---

## 会话管理

每个请求可携带 `session_id`，不传则由服务端生成 UUID：

```json
// 第一轮
{"question": "糖尿病有什么症状？"}

// 第二轮——复用上一轮的 session_id
{"question": "那饮食上要注意什么？", "session_id": "a1b2c3d4-..."}
```

后端通过 `qa_engine/stream.py` 的全局 `MemorySaver` 单例保留多轮对话状态。
