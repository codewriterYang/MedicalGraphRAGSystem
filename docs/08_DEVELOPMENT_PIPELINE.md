# 开发流程 (Development Pipeline)

版本：v1.0.0 | 状态：Current（描述当前代码实际状态）

---

## 概述

MedicalGraphRAGSystem 共经历 **8 个阶段**的开发，从数据采集到 Docker 部署形成完整闭环。

时间线：2026.03 → 06，约 4 个月。

```
阶段 1-2（数据+图谱）→ 阶段 3-4（双引擎）→ 阶段 5（工作流统一）
→ 阶段 6-7（前后端+流式）→ 阶段 8（部署）
```

---

## 阶段 1：数据采集（data_spider）

```
https://www.xywy.com/ 疾病百科页面
  ↓ requests + lxml + xpath
逐页爬取 ~8800 条疾病记录，每条包含 18 个字段
  ↓ 断点续爬 + 随机延迟反爬
backend/data/medical.json（45MB）
```

### 关键模块

| 模块 | 职责 |
|------|------|
| `backend/domain/data_spider/spider.py` | 爬虫主类，支持断点续爬、重试、随机延迟 |
| `backend/domain/data_spider/parsers.py` | 8 个子页面 xpath 解析（症状、药品、食物、检查等） |
| `backend/domain/data_spider/word_splitter.py` | LLM 并发症切分（"高血压、糖尿病、冠心病" → `["高血压","糖尿病","冠心病"]`） |

---

## 阶段 2：知识图谱构建（knowledge_graph）

```
medical.json
  ↓ DataLoader.load()
逐字段遍历 → nodes[label]（set 去重）+ rels[rel_type]（pair 列表）
  ↓ 特殊处理: cure_department → belongs_to 父子科室
  ↓ 特殊处理: drug_detail → Producer 节点 + drugs_of 关系
  ↓ GraphBuilder: UNWIND 批量写入（BATCH_SIZE=500）
Neo4j 图数据库（4.4 万节点 + 30 万关系）
```

### 关键模块

| 模块 | 职责 |
|------|------|
| `backend/domain/knowledge_graph/data_loader.py` | JSON → 节点/关系/属性 抽取 |
| `backend/domain/knowledge_graph/graph_builder.py` | CREATE INDEX + UNWIND MERGE 批量写入 |
| `backend/domain/knowledge_graph/main.py` | CLI 入口（`--clear` 清空重建，`--step` 分步执行） |

---

## 阶段 3：KBQA 模板问答引擎（kbqa）

```
用户问题
  ↓ LLMEngine: LLM 意图+实体联合抽取（JSON 输出）
  ↓ QuestionClassifier: 关键词兜底意图分类
  ↓ EntityNormalizer: 三级匹配归一化（精确→子串→rapidfuzz 模糊）
  ↓ CypherGenerator: 18 套参数化 Cypher 模板查表渲染
  ↓ GraphQuery: py2neo 参数化执行
  ↓ AnswerFormatter: 模板拼接 / LLM 润色
自然语言答案
```

### 关键模块

| 模块 | 职责 |
|------|------|
| `backend/domain/kbqa/config.py` | 18 种意图定义 + 关键词字典 + Cypher 模板 |
| `backend/domain/kbqa/llm_engine.py` | LLM 意图+实体联合抽取 + JSON 解析 |
| `backend/domain/kbqa/entity_normalizer.py` | 三级匹配归一化器 |
| `backend/domain/kbqa/cypher_generator.py` | 参数化 Cypher 模板引擎 |
| `backend/domain/kbqa/answer_formatter.py` | 18 种模板答案 + LLM 润色 |

---

## 阶段 4：GraphRAG 子图检索引擎（graphrag）

```
用户问题
  ↓ EntityExtractor: LLM 抽取医疗实体 [{name, type}]
  ↓ EntityNormalizer: 复用 KBQA 归一化
  ↓ SubgraphRetriever: 双向 2 跳子图检索（Hop1: 1跳邻居, Hop2: ≤15 Disease 扩展）
  ↓ ContextBuilder: 子图 → 结构化中文文本（按 label 分组, 中文标签映射, 截断 6000 字符）
  ↓ AnswerGenerator: LLM 基于上下文生成（防幻觉约束, temperature=0.1）
自然语言答案
```

### 关键模块

| 模块 | 职责 |
|------|------|
| `backend/domain/graphrag/entity_extractor.py` | LLM 医疗实体抽取 |
| `backend/domain/graphrag/subgraph_retriever.py` | 多跳子图检索 + 双向去重 |
| `backend/domain/graphrag/context_builder.py` | 子图 → 结构化文本 |
| `backend/domain/graphrag/generator.py` | LLM 基于上下文生成 |

---

## 阶段 5：LangGraph 统一工作流（qa_engine）

将 KBQA + GraphRAG 编排为一张 **StateGraph 12 节点工作流**：

```
1. 分析问题（三级降级: LLM → LLM+关键词 → AC自动机）
2. 路由判断（纯规则: 多实体跨类型→graphrag, 命中模板→template, 其他→llm_fallback）
   ├── template: T1(归一化) → T2(Cypher) → T3(执行) → T4(格式化)
   │                                              ↓ 无结果
   │                                         G1(回退 GraphRAG)
   └── graphrag: G1(实体抽取) → G2(归一化) → G3(子图检索) → G4(上下文) → G5(生成)
   X. 错误处理（三级兜底: 错误分类→LLM直接→静态提示）
```

### 关键模块

| 模块 | 职责 |
|------|------|
| `backend/domain/qa_engine/graph_builder.py` | StateGraph 构建 + 编译（MemorySaver） |
| `backend/domain/qa_engine/stream.py` | 全局单例 + SSE 流式生成器 |
| `backend/domain/qa_engine/session.py` | 多轮对话 + 指代消解 |
| `backend/domain/qa_engine/nodes/` | 12 个节点实现 |

---

## 阶段 6：FastAPI 网关 + SSE 流式（api）

```
POST /api/chat/stream
  ↓ StreamingResponse(text/event-stream)
  ↓ stream_qa() → app.astream_events(version="v2")
  ↓ 6 种 SSE 事件: delta | tool_start | tool_end | status | done | error
前端 fetch reader 按 \n\n 切分解析
```

### 关键模块

| 模块 | 职责 |
|------|------|
| `backend/api/app.py` | 4 个路由 + lifespan + CORS |
| `backend/api/models.py` | Pydantic API 模型 |
| `backend/core/config.py` | 统一配置 + LLM 工厂 |

---

## 阶段 7：React 前端 + 图谱可视化（frontend）

```
React 19 + Vite 8 + TypeScript 5 + Tailwind 4 + shadcn/ui
  ├── UnifiedChatPanel: SSE 流式接收 + 7 种路由标签
  ├── DebugPanel: 意图/实体/Cypher/路由 调试信息
  ├── GraphPanel: react-force-graph-2d 力导向图 + 点击展开邻居
  └── GraphRAGDebugPanel: 子图统计 + 上下文预览
```

### 技术栈

| 依赖 | 版本 | 用途 |
|------|------|------|
| React | ^19.2 | UI 框架 |
| TypeScript | ~5.9 | 类型检查 |
| Vite | ^8.0 | 构建工具 |
| Tailwind CSS | ^4.2 | 原子化 CSS |
| shadcn/ui | ^4.1 | UI 组件库 |
| react-force-graph-2d | ^1.29 | 力导向知识图谱 |

---

## 阶段 8：Docker 容器化部署

```
docker compose up -d
  neo4j (7687) ←── init-kg (一次性导入) ──→ 就绪
  web (Nginx:80) ──> server (FastAPI:8000)
                        ├──> Neo4j
                        └──> LLM Provider
```

### 服务清单

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `medgraph-neo4j` | Neo4j 5.x | 7687 | 图数据库 |
| `medgraph-init` | 自建 | — | 一次性图谱导入（完成后 exit 0） |
| `medgraph-server` | 自建 | 8000 | FastAPI 后端 |
| `medgraph-web` | Nginx | 8000→80 | React 前端静态服务 |

---

## 后续迭代方向

本流水线各阶段已完成基本功能，后续可依次优化：

1. **阶段 1** — 增量爬取 + 数据版本管理
2. **阶段 2** — 实体对齐去重 + 属性索引优化
3. **阶段 3** — 意图扩展 + Cypher 模板覆盖率提升
4. **阶段 4** — 多跳策略优化 + 子图排序
5. **阶段 5** — 工作流节点细化 + 评测体系
6. **阶段 6** — 鉴权 + 限流 + 监控
7. **阶段 7** — 组件拆分 + 移动端适配
8. **阶段 8** — K8s 编排 + CI/CD 自动化
