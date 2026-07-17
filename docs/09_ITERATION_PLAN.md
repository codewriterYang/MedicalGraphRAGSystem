# 迭代优化计划 (Iteration Plan)

版本：v1.0.0 | 状态：Active

---

## 1. 概述

基于 `docs/08_DEVELOPMENT_PIPELINE.md` 定义的 8 阶段开发流水线，对各阶段进行渐进式优化。

**时间线：** 2026.06 起，按阶段顺序逐步推进。

**核心原则：**
- 不影响现有系统正常运行
- 小步快跑，频繁迭代
- TDD 护栏 + 架构守护测试
- 人类 Review 是合并前的最后关卡

---

## 2. 执行节奏

```
大纲定稿（本文档）
  ↓
阶段 N 展开 → 写 Story 级详细计划（docs/iteration/stageN_xxx.md）
  ↓
TDD 实现（RED → GREEN → REFACTOR）
  ↓
人类 Review → 修复 → 验收
  ↓
合并到 main → 更新本文档进度
  ↓
阶段 N+1 展开 ...（循环）
```

---

## 3. 保障机制

### 3.1 分支隔离

每个阶段开独立分支，不直接动 main：

| 阶段 | 分支名 |
|------|--------|
| 1. data_spider | `feature/iter-stage1-spider` |
| 2. knowledge_graph | `feature/iter-stage2-kg` |
| 3. kbqa | `feature/iter-stage3-kbqa` |
| 4. graphrag | `feature/iter-stage4-graphrag` |
| 5. qa_engine | `feature/iter-stage5-qa-engine` |
| 6. api | `feature/iter-stage6-api` |
| 7. frontend | `feature/iter-stage7-frontend` |
| 8. docker | `feature/iter-stage8-docker` |

### 3.2 测试护栏

- **改动前：** 跑现有测试确认 baseline（全绿才能开始改）
- **改动中：** TDD（RED → GREEN → REFACTOR），新测试覆盖新行为
- **改动后：** 全量测试通过 + 无回归

### 3.3 影子模式

改动较大时，新旧实现并存，通过配置/开关切换：
- 新实现先在影子模式下运行
- 人类 Review 确认效果后切换到新实现
- 验证无误后移除旧实现

### 3.4 Review 关卡

每个阶段完成后：
1. 全量测试通过
2. 文档同步更新
3. 人类 Review 代码和功能
4. 确认无回归后合并到 main

---

## 4. 三轮推进策略

### 第一轮：数据修复（前置条件）

> 数据是一切的根基，源头不对，下游全是在错误基础上叠加。

| 阶段 | 范围 | 策略 | 状态 |
|------|------|------|------|
| 1. data_spider | 修复 spider/parsers 适配当前网站 | 小量验证 → 通过后全量覆盖 | ✅ 完成 |
| 2. knowledge_graph | 适配新数据结构，保证导入 Neo4j | 只修到能跑，不做去重/对齐 | ✅ 完成 |
| 3. kbqa | 清理药品意图，对齐图谱 Schema | TDD 清理死代码 + 集成测试 | ✅ 完成 |
| 4. graphrag | 清理药品残留，对齐图谱 Schema | TDD 清理死代码 + 集成测试 | ✅ 完成 |
| 5. qa_engine | 清理降级逻辑药品残留 | TDD 清理死代码 | ✅ 完成 |
| 6. api | 修复集成测试，验证 API 层 | 重写测试 + 端到端验证 | ✅ 完成 |
| 7. frontend | 清理 UI 药品残留 | 移除 Drug/Producer 颜色标签和文案 | ✅ 完成 |
| 8. docker | 清理 docker-init.py 药品残留 | 移除 Drug/Producer 标签 | ✅ 完成 |

**阶段 1 详细计划：** `docs/iteration/stage1_spider.md` ✅ Story 1.1/1.2 完成，Story 1.3 全量爬取进行中
**阶段 2 详细计划：** `docs/iteration/stage2_knowledge_graph.md` ✅ Story 2.1 完成，Story 2.2 等爬取完成
**阶段 3 详细计划：** `docs/iteration/stage3_kbqa.md` ✅ 完成（单元 17 + 集成 22 = 39 测试全绿）

### 第二轮：全链路验证

数据更新后，跑完整链路验证：

```
提问 → 分析 → 路由 → 模板查询/GraphRAG 检索 → 回答
```

确认无断裂。有问题当场修，记录到对应阶段的详细计划中。

| 验证项 | 方法 | 状态 |
|--------|------|------|
| KBQA 模板路径 | 16 种意图各跑一条典型问题 | ⬜ 未开始 |
| GraphRAG 路径 | 多实体/关系类问题 | ⬜ 未开始 |
| 降级路径 | 构造无结果/错误场景 | ⬜ 未开始 |
| SSE 流式 | 前端接收完整性 | ⬜ 未开始 |

### 第三轮：逐阶段优化（按优先级）

| 阶段 | 优化方向 | 侧重 | 状态 |
|------|---------|------|------|
| 3. kbqa | 意图覆盖 + 答案格式 | 用户体验：回答更准、更完整 | ⬜ 未开始 |
| 4. graphrag | 检索策略 + 生成质量 | 用户体验：复杂问题也能答好 | ⬜ 未开始 |
| 5. qa_engine | 路由稳定性 + 降级可靠性 | 工程能力：健壮的工作流 | ⬜ 未开始 |
| 6. api | 鉴权 + 限流 + 日志 | 工程能力：生产级接口 | ⬜ 未开始 |
| 7. frontend | 交互体验 + 展示优化 | 用户体验：用得舒服 | ⬜ 未开始 |
| 8. docker | 构建流程自动化 | 工程能力：一键部署 | ⬜ 未开始 |

> 第三轮各阶段的详细优化点在第二轮验证完成后展开，届时可根据实际跑出的问题调整优先级。

---

## 5. 进度追踪

| 轮次 | 阶段 | 计划文档 | 分支 | 状态 |
|------|------|---------|------|------|
| 第一轮 | 全部阶段 | round1_optimization.md | — | ✅ 完成 |
