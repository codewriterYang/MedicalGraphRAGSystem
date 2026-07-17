# 快速启动指南

---

## 1. 环境要求

| 软件 | 说明 |
|------|------|
| Python 3.10+ | 后端运行环境 |
| Neo4j 4.x/5.x | 需已导入医疗图谱（`python -m backend.domain.knowledge_graph.main`） |
| Node.js 18+ | 仅 `frontend/` 前端开发 |
| Ollama 或兼容 API | 默认 Ollama；国内可用 SiliconFlow（OpenAI 兼容） |

<!--
  以下包已包含在 pyproject.toml 的 dependencies 中，pip install backend/ 即可安装，
  无需再手动执行：
  pip install langgraph langsmith langchain-ollama
  若使用 OpenAI 兼容 API：pyproject.toml 已含 langchain-openai
-->

---

## 2. 安装步骤

```bash
# 1. 克隆并进入项目
cd MedicalGraphRAGSystem

# 2. 虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 3. 依赖（已包含 langgraph / langsmith / langchain-ollama 等）
pip install backend/

# 4. 环境变量
copy .env.example .env            # Windows
# cp .env.example .env          # Linux/macOS
# 编辑 .env：NEO4J_PASSWORD、LLM 相关项

# 5. 导入图谱（首次，耗时数小时）
# backend/data/medical.json 已包含爬取好的数据，无需重新爬取
python -m backend.domain.knowledge_graph.main
```

---

## 3. 配置 `.env`

### 3.1 最小可运行（Ollama + 本地 Neo4j）

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=你的密码
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
LLM_BASE_URL=http://localhost:11434
```

启动 Ollama 并拉取模型：

```bash
ollama pull qwen3:8b
```

### 3.2 SiliconFlow（OpenAI 兼容）

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-你的硅基流动密钥
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=deepseek-ai/DeepSeek-V4-Pro
```

### 3.3 LangSmith 追踪（可选）

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-你的密钥
LANGCHAIN_PROJECT=MedicalGraphQA
```

---

## 4. 三种启动入口

### 4.1 CLI — 终端调试

```bash
python -m backend.core.cli              # 同步问答
python -m backend.core.cli --stream     # 流式 token 输出
```

**适用**：开发调试、验证路由与降级、无浏览器环境。

退出：输入 `quit` / `exit` / `q`。

---

### 4.2 前后端分离 — 完整 Web UI

**终端 1 — 后端：**

```bash
python -m backend.api.app
# 可选参数：--port 8000 --neo4j-password xxx --llm-model qwen3:8b
```

**终端 2 — 前端：**

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。Vite 将 `/api` 代理到 `http://localhost:8000`。

**适用**：流式聊天、右侧调试面板、知识图谱点击扩邻。

生产构建：

```bash
cd frontend && npm run build
# FastAPI 会自动挂载 frontend/dist（若目录存在）
```

---

## 5. 验证清单

| 操作 | 预期 |
|------|------|
| `curl http://localhost:8000/api/health` | `neo4j: true`，`graphrag: true`（qa_engine 可用） |
| 问「感冒有什么症状？」 | 流式答案；调试面板显示 Level/意图/Cypher；标签「模板检索」 |
| 问「糖尿病和高血压有什么共同并发症？」 | GraphRAG 调试信息；图谱有节点；标签「GraphRAG」 |
| 连续追问「它有哪些症状？」 | 应能结合上一轮上下文（同一 `session_id`） |
| 点击图谱节点 | 加载邻居并扩展 |

流式请求体示例（含多轮会话）：

```json
{ "question": "感冒有什么症状？", "session_id": "web-session" }
```

---

## 6. 常见问题排查

### Neo4j 连接失败

- 确认 Neo4j 服务已启动，`.env` 中 `NEO4J_PASSWORD` 正确  
- 浏览器访问 `http://localhost:7474` 验证  
- `/api/health` 中 `neo4j: false` 时，问答与邻居查询均不可用  

### LLM 无响应 / 超时

- Ollama：`ollama list` 确认模型存在，`LLM_BASE_URL` 指向正确端口  
- SiliconFlow：检查 `OPENAI_API_KEY` 与 `OPENAI_BASE_URL`，模型名与平台一致  
- 查看终端 `qa_engine` / `backend.api` 日志  

### 右侧调试/图谱空白

- 确认使用 **流式** 接口且前端在 **`onDone`** 处理 debug（新引擎无 `retrieval`）  
- 浏览器 Network 查看 `done` 事件 JSON 是否含 `debug`、`graph_data`  
- 模板路径可能 `graph_data.nodes` 为空，属正常现象  

### 前端无法访问 API

- 开发模式必须用 `npm run dev`（带 proxy），不要直接打开 `dist/index.html`  
- 或先 `npm run build` 后只启 `python -m backend.api.app` 由 FastAPI 托管静态文件  

### LangSmith 无 Trace

- `LANGCHAIN_TRACING_V2=true`（字符串 true，非引号注释）  
- 已安装 `langsmith`，API Key 有效  
- 项目名 `LANGCHAIN_PROJECT` 与控制台一致  

### 导出工作流图失败

```bash
python -c "from backend.domain.qa_engine.cli import render_graph_diagram; render_graph_diagram('docs/assets/workflow.png')"
```

失败时会生成 `docs/assets/workflow.html`，用浏览器打开查看 Mermaid 图。

---

## 相关文档

- [../README.md](../README.md)  
- [02_ARCHITECTURE.md](./02_ARCHITECTURE.md)  
- [03_ADR.md](./03_ADR.md)  
