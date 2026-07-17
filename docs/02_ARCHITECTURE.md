# 系统架构 (Architecture)

版本：v1.0.0 | 状态：Current（描述当前代码实际状态）

---

## 1. 分层架构

```
┌─────────────────────────────────────────────────┐
│  表现层 (Presentation)                           │
│  frontend/ React + Vite + Tailwind CSS            │
└───────────────────────┬─────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│  网关层 (Gateway)                                │
│  backend/api/ FastAPI + Uvicorn + SSE              │
│  - REST API 端点                                  │
│  - CORS 中间件                                    │
│  - 静态文件挂载 (frontend/dist)                    │
└───────────────────────┬─────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│  领域层 (Domain)                                 │
│  backend/domain/qa_engine/ LangGraph 工作流引擎    │
│  ├── nodes/analysis.py    三级降级语义分析        │
│  ├── nodes/route.py       条件路由判断            │
│  ├── nodes/normalize.py   实体归一化              │
│  ├── nodes/template_path.py  Cypher 模板路径      │
│  ├── nodes/graphrag_path.py  GraphRAG 子图路径    │
│  └── nodes/error_handler.py  统一错误处理         │
│                                                  │
│  backend/domain/kbqa/  模板问答组件库 (被 qa_engine 复用) │
│  backend/domain/graphrag/  子图检索组件库 (被 qa_engine 复用) │
└───────────────────────┬─────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│  数据层 (Data)                                   │
│  Neo4j 5.x    │    backend/dict/ 实体词典   │   backend/data/ JSON│
└─────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│  基础设施 (Infrastructure)                       │
│  backend/core/config.py  │  .env  │  LangSmith (可选)       │
└─────────────────────────────────────────────────┘
```

---

## 2. 数据全链路

```
backend/domain/data_spider/ 采集（已固化）
  → backend/data/medical.json (45MB, ~8800条)
    → backend/domain/knowledge_graph/main.py 导入
      → Neo4j (~4.4万节点, ~30万关系)
        → backend/domain/qa_engine 查询/子图检索
          → LLM 生成或模板格式化
            → FastAPI SSE
              → React 答案+调试+图谱
```

离线词典 `backend/dict/*.txt`（7类约4.4万词条）供 Level 3 降级与实体模糊匹配使用。

---

## 3. qa_engine LangGraph 工作流

### 3.1 状态 QAState（`backend/domain/qa_engine/state.py`）

| 字段 | 类型 | 用途 |
|------|------|------|
| `question` | str | 用户原始问题 |
| `intent` | list[str] | LLM 识别的意图列表 |
| `entities` | list[dict] | LLM 抽取的实体列表 |
| `normalized_entities` | dict | 归一化后的实体字典 |
| `cypher` | list[dict] | 生成的 Cypher 查询组 |
| `raw_results` | list[dict] | Neo4j 查询原始结果 |
| `answer` | str | 最终格式化答案 |
| `error` | str | 错误信息（为空表示无错误） |
| `no_results` | bool | 查询无结果标记 |
| `analysis_level` | int | 降级等级（1/2/3） |
| `route` | str | 路由标记（6种模式） |
| `rag_entities` | list[dict] | GraphRAG 提取的实体 |
| `subgraph` | dict | 检索到的子图数据 |
| `context` | dict | 构建的文本上下文 |
| `rag_answer` | str | GraphRAG 路径生成的答案 |
| `graph_data` | dict | 前端可视化 `{nodes, edges}` |
| `chat_history` | list[dict] | 多轮对话 `[{role, content}]` |
| `template_no_result` | bool | 模板路径无结果 → 触发 GraphRAG 回退 |

### 3.2 节点一览

| 节点 ID | 模块 | 功能 |
|---------|------|------|
| 1. 分析问题 | `nodes/analysis.py` | 三级降级：LLM全分析 → 部分LLM → 词典NER |
| 2. 路由判断 | `nodes/route.py` | 写入 `route`，供条件边选择 |
| T1 | `nodes/normalize.py` | 实体归一化（失败→template_no_result） |
| T2 | `nodes/template_path.py` | 生成参数化 Cypher 查询 |
| T3 | `nodes/template_path.py` | 执行 Neo4j 查询 |
| T4 | `nodes/template_path.py` | 模板格式化答案 |
| G1 | `nodes/graphrag_path.py` | LLM 实体抽取 |
| G2 | `nodes/graphrag_path.py` | 实体归一化 |
| G3 | `nodes/graphrag_path.py` | 2跳子图检索 |
| G4 | `nodes/graphrag_path.py` | 子图→文本上下文 |
| G5 | `nodes/graphrag_path.py` | LLM 基于上下文生成回答 |
| X | `nodes/error_handler.py` | 三级兜底：硬错误→LLM兜底→静态文本 |

### 3.3 条件边

| 条件函数 | 返回标签 | 用途 |
|----------|----------|------|
| `step_outcome` | `success` / `error` | 节点成功→下一步，失败→错误处理 |
| `select_route_or_error` | `template` / `graphrag` / `error` | 路由分支 |
| `select_query_outcome` | `success` / `template_fallback` / `error` | T3后：模板无结果→G1回退 |

### 3.4 6种路由模式

| route 值 | 触发条件 | 前端 Badge |
|----------|----------|-----------|
| `template` | 单实体/短问句/Cypher命中 | 模板检索（绿） |
| `graphrag` | 多实体/关系比较/子图成功 | GraphRAG（蓝） |
| `template_to_graphrag` | 模板无结果→GraphRAG成功 | 模板检索→GraphRAG（蓝） |
| `llm_fallback` | 无医疗实体/直接LLM | AI回答（靛蓝） |
| `graphrag_to_llm` | GraphRAG不足→LLM兜底 | GraphRAG→AI回答（靛蓝） |
| `template_to_graphrag_to_llm` | 模板→GraphRAG→LLM三级 | 模板→GraphRAG→AI回答（靛蓝） |

---

## 4. API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 统一非流式问答 |
| POST | `/api/chat/stream` | SSE 流式问答（推荐） |
| POST | `/api/graphrag/chat` | 兼容路径 |
| POST | `/api/graphrag/chat/stream` | 兼容路径 |
| GET | `/api/graph/neighbors/{name}` | 节点邻居查询 |
| GET | `/api/health` | 健康检查 |

---

## 5. 前端组件树（`frontend/src/`）

```
App.tsx
├── UnifiedChatPanel.tsx      # 统一聊天 + streamChat + 6种路由Badge
│   └── onResponse → debug / graphData / responseMode
└── Tabs（可拖拽侧栏）
    ├── DebugPanel.tsx        # 模板路径调试（降级等级/意图/实体/Cypher）
    ├── GraphRAGDebugPanel.tsx # GraphRAG路径调试（实体/子图统计/上下文）
    └── GraphPanel.tsx        # react-force-graph-2d + 点击扩邻
```

### 前端技术栈

| 依赖 | 版本 | 用途 |
|------|------|------|
| React | ^19.2 | UI 框架 |
| TypeScript | ~5.9 | 类型检查 |
| Vite | ^8.0 | 构建工具 |
| Tailwind CSS | ^4.2 | 原子化 CSS |
| shadcn/ui | ^4.1 | UI 组件库 |
| react-force-graph-2d | ^1.29 | 力导向知识图谱 |
| lucide-react | ^1.7 | 图标库 |

---

## 6. 入口关系

```
backend/core/cli.py  ──re-export──►  backend/domain/qa_engine/
backend/api/app.py ──import──►    backend/core/cli.stream_qa / build_workflow
```

---

## 7. Docker 部署架构

```
docker compose up -d
  ├── medgraph-neo4j   (Neo4j 5.x 图数据库)
  │   └── bolt://neo4j:7687 (容器内) / :7687 (宿主机)
  ├── medgraph-init    (一次性图谱导入，完成后 exit 0)
  ├── medgraph-server  (FastAPI 后端 :8000)
  └── medgraph-web     (Nginx + React 前端 :8000→:80)
```

---

## 8. 模块依赖关系

```
backend/api/app.py
  ├── backend/core/cli.py (统一问答引擎入口)
  │   └── backend/domain/qa_engine/
  │       ├── nodes/analysis.py → backend/domain/kbqa/llm_engine.py
  │       ├── nodes/normalize.py → backend/domain/kbqa/entity_normalizer.py
  │       ├── nodes/template_path.py → backend/domain/kbqa/cypher_generator.py
  │       │                          → backend/domain/kbqa/graph_query.py
  │       │                          → backend/domain/kbqa/answer_formatter.py
  │       ├── nodes/graphrag_path.py → backend/domain/graphrag/entity_extractor.py
  │       │                          → backend/domain/graphrag/subgraph_retriever.py
  │       │                          → backend/domain/graphrag/context_builder.py
  │       │                          → backend/domain/graphrag/generator.py
  │       └── nodes/error_handler.py → backend/core/config.py (create_llm)
  ├── backend/domain/kbqa/chatbot.py (邻居查询 + 健康检查)
  └── backend/api/models.py + qa_response.py

backend/domain/knowledge_graph/main.py
  ├── data_loader.py → backend/data/medical.json
  └── graph_builder.py → Neo4j
```
