# Changelog

所有显著变更记录于此，格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [1.1.0] - 2025-06-20

### Changed
- **目录结构优化**：扁平结构 → `backend/` + `frontend/` 全栈 monorepo
  - 后端统一归入 `backend/`（api / core / domain / data / dict / tests / scripts）
  - 前端 `web/` → `frontend/`
  - 文档 `doc/` → `docs/`，图片统一至 `docs/assets/`
- **依赖管理现代化**：`requirements.txt` → `pyproject.toml`（`dependencies` + `optional-dependencies`）
- **Git 提交规范**：企业级 Conventional Commits 写入 `.claude.md`

### Fixed
- 全量 Python import 路径对齐新目录结构
- `docker-compose.yml`、`Dockerfile`、`.gitignore`、`.claudeignore` 路径同步
- `README.md`、`docs/01_QUICK_START.md` 命令和路径更新

---

## [1.0.0] - 2025-06-02

### Added
- **LangGraph 统一问答引擎**（`backend/domain/qa_engine/`）：StateGraph 工作流，三级降级分析
- **条件路由**：模板 Cypher 路径 + GraphRAG 子图检索自动切换
- **SSE 流式输出**：答案逐字返回，`done` 事件携带 debug 与图谱数据
- **LangSmith 可观测**：可选链路追踪，记录路由、降级等级与子图统计
- **图谱可视化**：React 力导向图 + 节点点击展开邻居
- **统一前端面板**：`UnifiedChatPanel` 单入口，后端自动路由
- **多轮对话**：LangGraph `MemorySaver` + `session_id`
- **全链路智能兜底**：模板失败 → 自动回退 GraphRAG → LLM 直接回答 → 静态提示
- **FastAPI 服务端**（`backend/api/`）：SSE + 邻居查询 API
- **React 前端**（`frontend/`）：TypeScript + Vite + Tailwind CSS + shadcn
- **测试框架**：16 个测试文件，~50 个测试函数
- **工作流图导出**：`backend/scripts/generate_diagrams.py`

### Core
- **医疗知识图谱构建**（`backend/domain/knowledge_graph/`）：~4.4 万实体，~30 万关系
- **数据采集爬虫**（`backend/domain/data_spider/`）：从医药网站采集疾病数据
- **实体词典**（`backend/dict/`）：7 类，约 4.4 万词条
- **模板 Cypher 问答**（`backend/domain/kbqa/`）：基于规则的医疗问答
- **GraphRAG 子图检索**（`backend/domain/graphrag/`）：图增强检索
- **固化数据**: `backend/data/medical.json`（45 MB，~8,800 条疾病记录）
