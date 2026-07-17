# 第二轮：全链路验证

版本：v1.0.0 | 状态：✅ 完成

---

## 1. 目标

第一轮 8 阶段已完成数据修复和药品清理。第二轮验证全链路正确性。

## 2. 当前测试基线

| 类型 | 数量 | 结果 |
|------|------|------|
| 单元测试 | 60 | ✅ 全绿 |
| 集成测试（新） | 43 | ✅ 全绿 |
| 集成测试（旧） | 3 文件 | ⚠️ 静默失败 |

## 3. 旧测试问题

3 个旧测试文件用 `return True/False` 代替 `assert`，import 失败也返回 False，pytest 不报错：

| 文件 | 问题 |
|------|------|
| `test_server_basic_qa.py` | 导入 `_run_basic_qa`（已改名 `_run_qa`），全部静默失败 |
| `test_multi_turn.py` | `return True/False` 模式，无 assert |
| `test_streaming_output.py` | `return True/False` 模式，无 assert |

## 4. 执行计划

### Step 1：修复旧测试（改写为 pytest assert 风格）

- `test_server_basic_qa.py` → 删除（已被 `test_api.py` 替代）
- `test_multi_turn.py` → 改写为 assert 风格，添加 skip 条件
- `test_streaming_output.py` → 改写为 assert 风格，添加 skip 条件

### Step 2：新建 API 契约测试

验证 API 请求/响应格式与前端 TypeScript 类型定义一致。

### Step 3：新建 E2E 测试

端到端验证：提问 → 分析 → 路由 → 查询 → 回答 全链路。

## 5. 验收标准

- 全量测试 0 失败
- 契约测试覆盖所有 API 端点
- E2E 测试覆盖 template + graphrag 两条路径
