# qa_engine — LangGraph 统一问答引擎

## 概述

`qa_engine` 是本项目的**核心模块**，将 `KBQA/` 和 `graphrag/` 的问答逻辑统一收敛为基于 **LangGraph StateGraph** 的工作流引擎。

### 设计动机

| 旧设计 | 新设计 |
|--------|--------|
| KBQA ChatBot 与 GraphRAGBot **独立运行**，前端需手动切换 | `stream_qa` **统一入口**，后端自动路由 |
| 无多轮对话机制 | LangGraph `MemorySaver` + `session_id` 检查点 |
| 无流式输出 | SSE 事件流逐字返回 |
| 错误时直接返回静态文本 | 三级兜底：模板 → GraphRAG → LLM → 静态提示 |
| 非工作流可观测 | LangSmith 追踪 + 节点级事件 |

---

## 工作流架构

```
用户问题
  │
  ▼
┌──────────────────────────────────────────────────┐
│  1. 分析问题 (Analyze)                            │
│  三级降级：全LLM → LLM实体+关键词 → 离线词典NER      │
└───────────────┬──────────────────────────────────┘
                │ success
                ▼
┌──────────────────────────────────────────────────┐
│  2. 路由判断 (Route)                              │
│  简单问句 → template / 复杂多实体 → graphrag        │
└───────┬───────────────────────┬──────────────────┘
        │ template              │ graphrag
        ▼                       ▼
┌───────────────┐       ┌───────────────┐
│ T1 实体归一化  │       │ G1 RAG实体抽取 │
│ T2 生成Cypher │       │ G2 实体归一化  │
│ T3 执行查询   │       │ G3 子图检索    │
│ T4 格式化答案  │       │ G4 上下文构建  │
└───────┬───────┘       │ G5 RAG生成回答 │
        │               └───────┬───────┘
        │           ┌───────────┤
        │           │ 模板无结果时自动回退
        │           ▼
        │     G1→G2→G3→G4→G5
        │
        ▼
   ┌─────────┐
   │  结束    │
   └─────────┘

全程共享: X. 错误处理（含LLM兜底）
```

### 关键设计决策

1. **条件边标签**：统一使用 `success | error | template | graphrag`，避免 LangGraph 导出 PNG 时出现 `True/False` 标签
2. **模板无结果处理**：设置 `template_no_result = True`（非 `error`），让工作流自动流转到 GraphRAG 路径，而非进入错误处理节点
3. **Global App 单例**：`get_or_create_app()` 复用 `MemorySaver`，确保多轮对话检查点不丢失

---

## 目录结构

```
qa_engine/
├── __init__.py            # 模块入口，导出核心接口
├── state.py               # QAState 类型定义（Pydantic）
├── graph_builder.py       # 工作流图构建（StateGraph + MemorySaver）
├── stream.py              # 异步流式 SSE 事件生成器
├── session.py             # 多轮对话会话管理（thread_id + 历史增强）
├── collect.py             # 流式结果收集（消费 stream_qa 至 done）
├── graph_utils.py         # 图谱数据解析工具
├── workflow_diagram.py    # Mermaid 工作流图源码
├── cli.py                 # CLI 入口 + 工作流图导出
└── nodes/                 # 工作流节点实现
    ├── analysis.py        # 节点 1：三级降级语义分析
    ├── route.py           # 节点 2：条件路由判断
    ├── normalize.py       # 节点 T1：实体归一化
    ├── template_path.py   # 节点 T2-T4：模板 Cypher 路径
    ├── graphrag_path.py   # 节点 G1-G5：GraphRAG 子图检索路径
    └── error_handler.py   # 节点 X：统一错误处理（含 LLM 兜底）
```

---

## 核心接口

| 接口 | 说明 |
|------|------|
| `build_workflow()` | 构建并返回编译前的 `StateGraph` |
| `create_app()` | 创建带有 `MemorySaver` 检查点的可运行实例 |
| `stream_qa(question, config)` | 异步生成器，逐步返回 `delta` / `tool_start` / `tool_end` / `done` / `error` 事件 |
| `QAState` | 工作流状态类型（TypedDict） |
| `get_or_create_app()` | 获取或创建全局 app 单例（复用检查点） |

### 使用示例

```python
from backend.domain.qa_engine import stream_qa, create_app
from backend.domain.qa_engine.session import make_thread_config

config = make_thread_config("my-session")

async for event in stream_qa("感冒有什么症状？", config=config):
    if event["event"] == "delta":
        print(event["chunk"], end="", flush=True)
    elif event["event"] == "done":
        print(f"\n[路由: {event['mode']}] 回答完成")
```

---

## 与旧模块的关系

| 旧模块 | 在 qa_engine 中的角色 |
|--------|----------------------|
| `KBQA/llm_engine.py` | `nodes/analysis.py` 调用 LLM 进行语义分析 |
| `KBQA/entity_normalizer.py` | `nodes/normalize.py` 复用实体归一化 |
| `KBQA/cypher_generator.py` | `nodes/template_path.py` 调用生成 Cypher |
| `KBQA/graph_query.py` | `nodes/template_path.py` 调用执行查询 |
| `KBQA/answer_formatter.py` | `nodes/template_path.py` 调用格式化答案 |
| `graphrag/entity_extractor.py` | `nodes/graphrag_path.py` 复用实体抽取 |
| `graphrag/subgraph_retriever.py` | `nodes/graphrag_path.py` 复用于图检索 |
| `graphrag/context_builder.py` | `nodes/graphrag_path.py` 复用上下文构建 |
| `graphrag/generator.py` | `nodes/graphrag_path.py` 复用答案生成 |

旧模块保留原样，作为"组件库"被 qa_engine 调用，向后兼容。

---

## 流式事件协议

| 事件 | 载荷 | 触发时机 |
|------|------|----------|
| `delta` | `{"chunk": "..."}` | LLM 生成每个 token |
| `tool_start` | `{"node": "节点名"}` | 节点开始执行 |
| `tool_end` | `{"node": "节点名", "duration": 123}` | 节点执行结束 |
| `done` | `{"answer": "...", "debug": {...}, "graph_data": {...}, "mode": "template"}` | 工作流完成 |
| `error` | `{"message": "..."}` | 发生异常 |

---

## 多轮对话

基于 LangGraph `MemorySaver` + `thread_id` 实现：

```python
config = {"configurable": {"thread_id": "user-123"}}

# 第一轮
stream_qa("糖尿病有什么症状？", config=config)

# 第二轮——自动携带上一轮的 chat_history
stream_qa("那饮食上要注意什么？", config=config)
```

`session.py` 提供指代词检测 + 历史实体拼接，辅助 LLM 理解上下文中"那"、"它"等指代。

---

## 版本历史

- **v1.0.0**：统一 `qa_engine` 工作流 + FastAPI + React 前后端分离

详见 [CHANGELOG.md](../CHANGELOG.md)。
