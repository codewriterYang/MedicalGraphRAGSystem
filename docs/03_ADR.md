# 架构决策记录 (ADR)

版本：v1.0.0 | 状态：Current

---

## ADR-001: 使用 LangGraph StateGraph 作为问答引擎

**日期**：2025-06  
**状态**：已采纳

### 背景

早期架构中 KBQA ChatBot 与 GraphRAG Bot 各自独立运行，前端需手动选择模式。需要一种方式将模板 Cypher 检索与 GraphRAG 子图检索统一编排。

### 决策

使用 LangGraph StateGraph 构建统一问答工作流，通过条件边实现自动路由。

### 理由

- 条件边与「三级降级 + 双路径」天然匹配
- MemorySaver 检查点支持多轮对话
- `astream_events` 可统一产出前端所需的 `delta`/`done` 事件
- 节点单一职责，便于测试与 LangSmith 节点级追踪

### 后果

- 新增 `backend/domain/qa_engine/` 模块，包含 StateGraph 构建和 10 个节点函数
- 旧 `ChatBot.chat_stream()` 不再用于问答主路径
- 前端需适配新引擎的 SSE 事件协议（无 `retrieval` 事件）

---

## ADR-002: 保留 kbqa/ 和 graphrag/ 旧模块

**日期**：2025-06  
**状态**：已采纳（注：v1.1.0 目录重构后路径为 `backend/domain/kbqa/` 和 `backend/domain/graphrag/`）

### 背景

`backend/domain/kbqa/` 和 `backend/domain/graphrag/` 包含成熟的组件（LLM 引擎、实体归一化器、Cypher 生成器、子图检索器等），直接删除风险高。

### 决策

保留旧模块作为"组件库"，由 `backend/domain/qa_engine/nodes/` 复用其核心类。

### 理由

- 邻居查询、健康检查仍依赖 `backend/domain/kbqa/chatbot.ChatBot`
- GraphRAG 子模块已被 `backend/domain/qa_engine/nodes/graphrag_path.py` 复用
- 最小风险迁移，不破坏现有导入路径

### 后果

- `backend/domain/kbqa/chatbot.py` 仅用于 `/api/graph/neighbors` 和健康检查
- `backend/domain/graphrag/graphrag_bot.py` 不再直接用于问答端点
- 存在部分逻辑重复（如 `analysis.py` 与 `chatbot.py` 的降级逻辑），后续需去重

---

## ADR-003: 使用 SSE 流式协议而非 WebSocket

**日期**：2025-06  
**状态**：已采纳

### 背景

问答引擎需要支持 token 级流式输出到前端。

### 决策

使用 Server-Sent Events (SSE) 协议，通过 FastAPI `StreamingResponse` 实现。

### 理由

- SSE 比 WebSocket 更简单，单向推送足够
- FastAPI 原生支持 `StreamingResponse`
- 前端 `EventSource` API 或手动 `fetch` + `ReadableStream` 均可消费
- 无需额外的 WebSocket 握手和连接管理

### 后果

- 定义了 4 种 SSE 事件类型：`status`、`delta`、`done`、`error`
- 前端 `client.ts` 手动解析 SSE 帧（`\n\n` 分割）
- Nginx 配置需 `proxy_buffering off` 支持流式传输

---

## ADR-004: 模板路径无结果时自动回退 GraphRAG

**日期**：2025-06  
**状态**：已采纳

### 背景

模板 Cypher 路径在实体归一化失败、Cypher 生成失败或查询无结果时，早期直接返回静态错误文本。

### 决策

设置 `template_no_result = True`（非 `error`），让工作流自动流转到 GraphRAG 路径。

### 理由

- 用户不应因模板路径失败而收到冰冷的技术错误
- GraphRAG 子图检索可能覆盖模板无法匹配的场景
- 与 `error` 区分，避免进入错误处理节点

### 后果

- T1（归一化）、T2（Cypher生成）、T3（查询执行）失败均设 `template_no_result=True`
- `select_query_outcome` 条件边增加 `template_fallback` 标签
- 形成完整的三级回退链：模板 → GraphRAG → LLM 兜底 → 静态文本

---

## ADR-005: 使用 MemorySaver + session_id 实现多轮对话

**日期**：2025-06  
**状态**：已采纳

### 背景

需要支持多轮对话，第二轮提问能关联第一轮的上下文。

### 决策

使用 LangGraph `MemorySaver` 检查点 + 固定 `thread_id`（session_id）实现。

### 理由

- LangGraph 原生支持，无需额外存储
- 同一 `thread_id` 自动恢复上一轮的 `chat_history`
- `session.py` 提供指代词检测 + 历史实体拼接，辅助 LLM 理解上下文

### 后果

- `stream.py` 使用全局单例 `get_or_create_app()` 复用 MemorySaver
- 前端/CLI/API 各自维护固定的 session_id
- chat_history 仅内存级别，服务重启后丢失

---

## ADR-006: 前端使用 UnifiedChatPanel 单入口

**日期**：2025-06  
**状态**：已采纳

### 背景

早期前端有 ChatPanel（模板）和 GraphRAGChatPanel 两个独立面板，用户需手动切换。

### 决策

合并为 `UnifiedChatPanel`，后端自动路由，前端根据 `mode` 切换调试面板和 Badge。

### 理由

- 用户无需关心内部路由逻辑
- 减少前端代码重复
- 6 种路由模式通过 Badge 颜色和文字清晰展示流转路径

### 后果

- `ChatPanel.tsx` 和 `GraphRAGChatPanel.tsx` 已删除
- `normalizeDebug()` 负责将后端统一 debug 转为前端格式
- `UnifiedChatPanel` 处理 `status`/`delta`/`done`/`error` 四种 SSE 事件

---

## ADR-007: 错误处理采用三级兜底策略

**日期**：2025-06  
**状态**：已采纳

### 背景

早期错误处理简单粗暴：有错误就返回静态文本。

### 决策

在 `error_handler.py` 中实现三级兜底：

| 优先级 | 条件 | 行为 |
|--------|------|------|
| 1 | 系统级硬错误（LLM/Cypher/Neo4j） | 返回分类错误提示 |
| 2 | 可恢复错误 / 无结果 | 调用 LLM 直接回答 |
| 3 | LLM 不可用 | 返回静态兜底文本 |

### 理由

- 区分硬错误和可恢复错误，最大化回答成功率
- LLM 兜底时附带免责声明
- 根据来源写入精确的 route 标签（如 `template_to_graphrag_to_llm`）

### 后果

- `handle_error` 函数逻辑较复杂，需仔细维护
- 前端 Badge 需支持 6 种路由模式

---

## ADR-008: 采用 Pipeline 架构而非 Agent 架构

**日期**：2026-06  
**状态**：已采纳

### 背景

在项目架构演进过程中，面临一个关键选择：是否将系统从当前的 Pipeline（流水线）架构升级为 Agent（智能体）架构。Agent 架构近年来在 AI 工程领域备受关注，其核心特征是 LLM 自主规划、动态工具调用、反馈循环。需要评估 Agent 化对本项目的适用性和必要性。

### 决策

**保持 Pipeline 架构，不进行 Agent 化改造。**

### 理由

**1. 任务本质是"检索+生成"，不是"自主决策"**

本系统的用户意图可穷举（查疾病、查药物、查症状、查科室），每种意图对应确定的查询路径。不存在"不知道该做什么、需要 LLM 自己想办法"的开放性场景。Pipeline 的确定性执行路径与业务需求天然匹配。

**2. 六路由降级系统已覆盖 Agent 的核心能力**

Agent 的核心价值在于"这条路不通换那条"——本项目的降级链（模板 Cypher → GraphRAG 子图检索 → LLM 直接回答 → 静态兜底）已经实现了这一思想。区别在于降级策略由规则 + 置信度阈值驱动，而非 LLM 自主决策。规则驱动比 LLM 驱动更可控、更可预测、更可调试。

**3. 医疗场景的特殊约束**

- **准确性**：同一问题必须返回一致答案。Agent 的随机性（同一问题两次可能走不同路径）在医疗场景中不可接受。
- **可解释性**：需要追溯"为什么查这个实体、为什么走这条路径"。Pipeline 每一步可单独测试和审计，Agent 的黑盒决策难以满足这一要求。
- **安全性**：LLM 自主决定查询策略存在幻觉风险，可能生成不存在的 Cypher 或错误关联医疗实体。

**4. 架构复杂度与收益不匹配**

Agent 化需要引入：规划器、记忆系统、工具注册与发现、评估反馈环、资源调度层、监控层。引入的复杂度远大于实际收益——当前 Pipeline 架构已经足够解决所有业务问题。

**5. 当前架构已有 Agent 雏形，缺的不是模块而是编排方式**

| Agent 要素 | 对应模块 | 实现方式 |
|-----------|---------|---------|
| 感知 | `route.py` | 意图识别 + 实体提取 |
| 规划 | 路由决策 + 降级策略 | 规则 + 置信度阈值 |
| 记忆 | `session.py` | 会话上下文管理 |
| 执行 | `graph_query.py` + `generator.py` | 图谱查询 + LLM 生成 |
| 评估 | 降级触发条件 | 查询结果质量判断 |
| 监控 | `stream.py` | 阶段性进度事件 |

结论：不是缺模块，而是**不需要让 LLM 来动态编排这些模块**。

### 后果

- 系统架构保持 Pipeline 模式，不做 Agent 化改造
- 未来若出现开放式多步推理需求（如鉴别诊断、跨异构数据源自主编排），可在 Pipeline 基础上增加 Agent 编排层，而非替换现有架构
- 面试和技术交流中可明确阐述这一架构决策的业务逻辑

### 面试话术参考

> **问**：你们为什么选择 Pipeline 而不是 Agent 架构？
>
> **答**：这是由业务场景决定的。我们的医疗问答系统面对的是可穷举的用户意图和确定性的查询路径——查疾病、查药物、查症状，每种都有明确的图谱查询模板。Agent 的核心价值在于不确定性环境下的自主规划，但我们的场景不需要"猜下一步做什么"，而是需要"每一步都做对"。再加上医疗场景对准确性和一致性要求极高，Agent 的随机性是不可接受的。所以我们用 Pipeline + 六路由降级，既保证了灵活性，又保证了可控性。实际上我们的降级系统已经实现了 Agent 的核心思想——"这条路不通换那条"，只是用规则而非 LLM 来驱动，更稳定、更可调试。

### 核心结论

> **架构选择没有对错，只有合不合适。Pipeline 不是落后的，Agent 不是先进的——在合适的场景里，Pipeline 就是最优解。**
