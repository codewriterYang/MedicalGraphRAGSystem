# AI Native Vibe Coding 开发模式

版本：v1.0
状态：Active

---

## 一、模式概述

一种以 AI 为核心开发者的软件工程方法。人类负责需求定义和质量把关，AI 负责分析、编码、测试、文档的全流程执行。

**核心循环：**
```
人类提需求 → AI 生成文档体系 → AI 编码实现 → AI 测试验证
→ 人类 Review → AI 修复 → 人类验收
```

---

## 二、文档驱动开发（Document-Driven）

开发前必须先产出完整文档体系，文档是 AI 的"工作手册"。

### 必需文档

| 文档 | 作用 | 何时产出 |
|------|------|----------|
| PRD | 产品需求，定义"做什么" | 项目启动时 |
| Architecture | 系统架构，定义"怎么组织" | 项目启动时 |
| ADR | 架构决策记录，定义"为什么这样" | 每次重大决策时 |
| Contract | API 契约，定义"接口规范" | 项目启动时 |
| Domain Model | 领域模型，定义"业务概念" | 项目启动时 |
| Database Schema | 数据库设计 | 项目启动时 |
| Epics | 史诗拆解，定义"开发计划" | 项目启动时 |
| Testing Strategy | 测试策略 | 项目启动时 |
| Repository Rules | 仓库规范 | 项目启动时 |
| Definition of Done | 完成标准 | 项目启动时 |

### 文档与代码的关系

- **文档是权威来源**，代码必须与文档一致
- 代码变更时必须同步更新文档
- Contract 变更必须更新 Contract Test

---

## 三、开发工作流

### 3.1 Phase 0：需求分析（人类 + AI）

```
人类：描述需求
  ↓
AI：产出 PRD + Architecture + ADR + Contract + Epics
  ↓
人类：Review 并确认
  ↓
保存到 docs/
```

**关键约束：**
- 不写一行代码，只产出文档
- 文档之间必须一致（Contract ↔ Architecture ↔ Domain Model）
- 每个 Epic 必须拆解到 Task 级别，每个 Task 有明确的 Acceptance Criteria

### 3.2 Phase 1：Epic 分析（AI）

```
AI：阅读 Epic 描述
  ↓
AI：对照 Architecture 确认模块归属
  ↓
AI：对照 Contract 确认 API 契约
  ↓
AI：输出 Implementation Plan
```

**输出格式：**
- Feature → Story → Task 拆解
- 每个 Task：Inputs / Outputs / Acceptance Criteria / Tests Required

### 3.3 Phase 2：Story 实现（AI，TDD 流程）

```
RED：编写失败测试
  ↓
GREEN：编写最小代码使测试通过
  ↓
REFACTOR：优化代码结构
  ↓
验证：运行全部相关测试
  ↓
文档更新：同步更新 Architecture / Contract / Domain
  ↓
COMMIT：Story 级别提交
```

**硬性约束：**
- 不得跳过 RED 阶段
- 不得跳过 REFACTOR 阶段
- 不得实现超出当前 Story 范围的功能
- 每个 Story 完成后必须 Commit

### 3.4 Phase 3：Review（人类 + AI）

```
人类：Review 代码和功能
  ↓
AI：修复 Review 发现的问题
  ↓
AI：运行测试确认修复
  ↓
人类：验收
```

---

## 四、TDD（测试驱动开发）

### 核心流程

```
RED → GREEN → REFACTOR
```

### RED（编写失败测试）

- 根据 Acceptance Criteria 编写测试
- 运行测试，确认失败
- 失败原因必须是"功能缺失"，而非代码错误
- **必须使用 `assert` 断言风格**，禁止 `return True/False` 模式

### 测试编写规范

**✅ 正确（assert 风格）：**

```python
def test_disease_drug_not_in_intents():
    """INTENT_TYPES 不包含 disease_drug。"""
    from backend.domain.kbqa.config import INTENT_TYPES
    assert "disease_drug" not in INTENT_TYPES

def test_neo4j_query_returns_results():
    """Neo4j 查询应返回非空结果。"""
    result = graph.run("MATCH (n:Disease) RETURN n LIMIT 1").data()
    assert len(result) > 0, "Disease 节点不应为空"
```

**❌ 错误（return True/False 风格，禁止使用）：**

```python
def test_something():
    try:
        from module import func
        print("  [OK] 导入成功")
        return True          # ← pytest 不认为这是失败
    except ImportError:
        print("  [FAIL] 导入失败")
        return False         # ← 静默失败，pytest 报告通过
```

**为什么禁止 return True/False：** pytest 通过 `AssertionError` 判断测试是否失败。`return False` 不会抛异常，pytest 认为测试通过了，导致 import 失败、查询异常等问题被静默掩盖。

### GREEN（最小实现）

- 编写最少的代码使测试通过
- 不做额外优化
- 不实现超出当前 Story 的功能

### REFACTOR（重构）

- 优化代码结构
- 消除重复
- 提升可读性
- 重构后测试必须全部通过

### 测试层级

| 层级 | 用途 | 优先级 |
|------|------|--------|
| Contract Test | 验证 API 契约 | 最先编写 |
| Unit Test | 验证单个函数/类 | 其次 |
| Integration Test | 验证组件协作 | 再次 |
| E2E Test | 验证完整链路 | 最后 |

---

## 五、Contract First（合约优先）

### 核心原则

- Contract 是 API 的唯一权威来源
- 先定义接口，后实现代码
- 实现必须通过 Contract Test

### 开发顺序

```
Contract 定义
  ↓
Contract Test
  ↓
Implementation
  ↓
Integration Test
```

### 变更规则

- 新增字段：允许
- 删除字段：禁止
- 修改字段类型：禁止
- 修改 Endpoint：禁止
- 需要破坏性修改时：创建新版本（如 `/api/v2`）

---

## 六、Epic 驱动开发

### 拆解层级

```
Epic → Feature → Story → Task
```

### 每个层级的完成标准

**Task Done：**
- Acceptance Criteria 已验证
- RED → GREEN → REFACTOR 完成
- Contract Test 通过

**Story Done：**
- 所有 Task 完成
- 跨 Task 一致性检查
- Story 级别 E2E 验证
- Code Review 通过
- Commit 已提交

**Epic Done：**
- 所有 Story 完成
- Epic 级别 E2E 验证
- Architecture / Contract / Domain 一致性检查
- 文档全部更新

---

## 七、Git 管理

### Commit 规范

```
<type>(<scope>): <description>
```

**Type：** feat / fix / test / refactor / docs / chore / style / perf

**Scope：** 模块名称（如 qa_engine / api / frontend / knowledge_graph / kbqa / graphrag）

**格式：**

```
<type>(<scope>): <中文简述>

<body>（可选，说明 why 而非 what）

<footer>（可选，BREAKING CHANGE / 关联 Issue）
```

**Footer 规范：**

| Footer 类型 | 格式 | 何时使用 |
|-------------|------|----------|
| 破坏性变更 | `BREAKING CHANGE: <描述>` | API/数据结构不兼容变更 |
| 关联 Issue | `Closes #123` | 修复或实现某个 Issue |

**规则：**
- 每个 Story 一个 Commit
- 不同功能分开 Commit
- 不提交临时文件、缓存、IDE 配置
- Commit 前必须通过全部测试

### 回滚策略

- 未 push 的 commit：`git reset --soft` 回退
- 已 push 的 commit：`git revert` 创建反向 commit
- 大规模回滚：`git reset --hard` + `git push --force`（需确认无协作者）

### 分支策略

- `main`：生产分支，随时可部署
- `feature/<功能名>`：功能分支，Story 级别
- `fix/<问题描述>`：紧急修复

---

## 八、AI 工具协作模式

### 模式 A：单 AI 开发（推荐）

```
人类提需求
  ↓
AI（Claude Code）：分析 + 编码 + 测试 + 文档
  ↓
人类：Review + 验收
```

适用于：小型项目、快速原型

### 模式 B：双 AI 协作

```
AI-1（Claude Code）：产出文档体系 → 保存到 docs/
  ↓
  备选：ChatGPT / Claude 网页版产出文档
  ↓
AI-2（Claude Code）：读取文档 → 编码 → 测试
  ↓
人类：Review 代码
  ↓
AI-2（Claude Code）：修复问题
```

适用于：中型项目、需要代码审查

### 模式 C：多 AI 流水线

```
AI-1（Claude Code）：需求分析 + PRD + 架构设计
  ↓
  备选：ChatGPT / Claude 网页版辅助文档编写
  ↓
AI-2（Claude Code）：TDD 开发 + Contract 实现
  ↓
人类：代码审查 + 最终验收
```

适用于：大型项目、团队协作

---

## 九、质量保障

### 测试金字塔

```
        E2E (10%)
         ▲
    Integration (20%)
         ▲
       Unit (70%)
```

### 覆盖率要求

| 类型 | 要求 |
|------|------|
| Unit Test | ≥ 90% |
| Integration Test | ≥ 80% |
| Contract Test | 100% |
| Critical Domain | 100% |

### 代码审查检查清单

- [ ] 代码是否与文档一致
- [ ] Contract 是否被修改（如修改需更新）
- [ ] 测试是否覆盖 Acceptance Criteria
- [ ] 是否有未处理的异常
- [ ] 是否有硬编码值
- [ ] 是否有未使用的导入
- [ ] Commit Message 是否规范

---

## 十、快速启动

### 新项目初始化

1. 用 Claude Code 生成完整文档体系（备选：ChatGPT / Claude 网页版）
2. 保存到 `docs/` 目录
3. 创建 `.claude.md` 定义 AI 行为规范
4. 创建 `.claudeignore` 排除不需要 AI 读取的文件（构建产物、缓存、归档文档等）
5. 创建 `pyproject.toml` / `package.json`
6. 初始化 Git 仓库

### 日常开发循环

```
1. AI 阅读 Epic → 输出 Implementation Plan
2. AI 按 Story 执行 TDD（RED → GREEN → REFACTOR）
3. AI 运行测试 → 确认通过
4. AI 更新文档
5. AI Commit
6. 人类 Review
7. AI 修复（如需要）
8. 重复 1-7
```

### 紧急修复流程

```
1. 人类报告问题
2. AI 编写复现测试（RED）
3. AI 修复问题（GREEN）
4. AI 重构（REFACTOR）
5. AI 运行测试 → 确认通过
6. AI Commit（fix 类型）
```

---

## 十一、AI 工具使用最佳实践

### 文档喂给 AI 的最佳实践

**第一原则：用 Claude Code**，它能直接读取项目文件，无需手动喂文档。

**Claude Code 模式（推荐）：**
- `.claude.md` 自动读取，核心规范无需重复交代
- `.claudeignore` 控制 AI 不读取的文件（构建产物、归档文档等）
- 直接 `@docs/04_CONTRACT.md` 引用具体文档即可
- 备选：ChatGPT / Claude 网页版需手动上传文档

**如果手动喂文档，按阶段分层：**

```
Phase 0：喂 PRD + Architecture + Contract
  → 让 AI 理解"做什么"和"怎么组织"
  → 产出 Implementation Plan

Phase 1：喂 Contract + Domain Model + 当前 Story 的 Task 描述
  → 让 AI 只关注当前要做的事
  → 执行 TDD（RED → GREEN → REFACTOR）

Phase 2：喂 Testing Strategy + Repository Rules
  → 让 AI 知道测试规范和代码规范
  → 验证 + Commit
```

### `.claude.md` 与 `.claudeignore` 配置要点

**`.claude.md`** 是 AI 每次启动自动读取的行为规范文件，应包含：

- 项目技术栈和架构约定
- TDD 强制规则
- Contract First 原则
- Commit 规范
- 当前开发阶段标记
- 参考文档路径

**`.claudeignore`** 控制 AI 不读取的文件，减少上下文膨胀：

- 构建产物（`node_modules/`、`dist/`、`*.egg-info/`）
- 缓存文件（`__pycache__/`、`.pytest_cache/`）
- 归档文档（`docs/archive/`）
- 大文件（数据文件、图片等）

### 关键原则

1. **一次只给一个 Story** — 不要让 AI 同时做多个 Story，上下文会乱
2. **先让它出 Plan，确认后再写代码** — 否则容易跑偏，实现超出范围的功能
3. **Contract 一定要先喂** — AI 会按 Contract 写测试，再写实现，不会乱加字段
4. **`.claude.md` 是最重要的** — 核心规则写进去，每次启动自动读取，不用反复交代
