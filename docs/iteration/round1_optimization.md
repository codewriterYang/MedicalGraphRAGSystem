# 第一轮：药品残留清理（Round 1 Optimization）

版本：v1.0.0 | 状态：✅ 完成

---

## 概述

爬虫确认网站全站下线药品模块后，第一轮对 8 阶段进行系统性清理，确保所有模块的药品相关代码与图谱 Schema 对齐。

**核心原则：**
- 不影响现有系统正常运行
- TDD 护栏（RED → GREEN → REFACTOR）
- 人类 Review 是合并前的最后关卡
- 小步快跑，每个 Story 独立 commit

---

## 数据链路依赖

```
爬虫 JSON 字段  →  Neo4j 节点/关系  →  KBQA 意图 + Cypher 模板  →  GraphRAG 实体/关系标签  →  qa_engine 降级逻辑  →  API 层  →  前端 UI
```

药品数据下线后，这条链路的每一环都残留了无效引用，需要逐环清理。

---

## 阶段 1：data_spider — 数据采集修复

### 问题

爬虫每页请求 8 个子页面，其中 drug 子页面网站已全站下线，100% 返回空，但仍在发起 HTTP 请求，浪费 ~1 秒/页。

### 清理方案

| 文件 | 改动 |
|------|------|
| `parsers.py` | `parse_drug()` 更新 xpath 适配新结构，无药品时返回空列表 |
| `config.py` | `ATTR_MAP` 移除 `"常用药品": "common_drug"`，`SPLIT_FIELDS` 移除 `"common_drug"` |
| `spider.py` | **跳过 drug 页 HTTP 请求**，直接传 `[], []`（加速优化） |

### 测试结果

- 单元测试：7 passed
- 全量回归：75 passed

---

## 阶段 2：knowledge_graph — 知识图谱构建适配

### 问题

图谱 Schema 仍定义 Drug/Producer 节点和 3 种药品关系，与新数据不一致。

### 清理方案

| 文件 | 改动 |
|------|------|
| `config.py` | NODE_LABELS 移除 Drug/Producer（7→5），REL_TYPES 移除 3 种药品关系（11→8） |
| `data_loader.py` | 移除 common_drug/recommand_drug/drug_detail 三段处理代码 |
| `graph_builder.py` | 注释更新 |
| `main.py` | build_nodes/build_rels 移除 Drug/Producer 引用 |

### 测试结果

- 单元测试：15 passed
- 全量回归：90 passed

---

## 阶段 3：kbqa — 模板引擎适配

### 问题

KBQA 有 18 种意图和 6 种实体类型，其中 disease_drug 和 drug_disease 是死路——图谱中无 Drug 节点，查询永远返回空。

### 清理方案

| 文件 | 改动 |
|------|------|
| `config.py` | INTENT_TYPES 移除 disease_drug/drug_disease（18→16），LLM_SYSTEM_PROMPT 移除药品描述 |
| `cypher_generator.py` | CYPHER_TEMPLATES 移除 disease_drug/drug_disease（18→16） |
| `llm_engine.py` | _VALID_ENTITY_TYPES 移除 drug/producer（7→5） |
| `answer_formatter.py` | 移除 disease_drug/drug_disease 模板分支 |
| `config.py` | 路径修复 parent.parent → parent.parent.parent.parent |

### 测试结果

- 单元测试：17 passed
- 集成测试：22 passed（16 种意图各一条典型问题）
- 全量回归：41 passed

---

## 阶段 4：graphrag — 子图检索适配

### 问题

GraphRAG 的检索是通用的（`MATCH (n)-[r]-(m)`），不会报错，但以下残留定义冗余：
- ENTITY_EXTRACT_PROMPT 含 drug 实体类型说明
- _VALID_ENTITY_TYPES 含 drug/producer
- REL_LABELS 含 3 种药品关系中文标签

### 清理方案

| 文件 | 改动 |
|------|------|
| `config.py` | ENTITY_EXTRACT_PROMPT 移除 drug 实体类型，路径修复 |
| `entity_extractor.py` | _VALID_ENTITY_TYPES 移除 drug/producer（7→5） |
| `context_builder.py` | REL_LABELS 移除 3 种药品关系（11→8） |

### 测试结果

- 单元测试：11 passed
- 集成测试：11 passed（含 test_no_drug_node_in_subgraph XPASS）
- 全量回归：52 passed

---

## 阶段 5：qa_engine — 编排引擎适配

### 问题

qa_engine 的三级降级逻辑（Level 2/3）中残留 drug 关键词匹配，LLLM 不可用时仍会匹配药品意图。

### 清理方案

| 文件 | 改动 |
|------|------|
| `nodes/analysis.py` | `_keyword_classify` 移除 `"drug"` 分支、兜底意图移除 disease_drug、`_build_keyword_lists` 移除 disease_drug/drug_disease 两项 |

### 测试结果

- 单元测试：8 passed
- 全量回归：60 passed

---

## 阶段 6：api — API 层适配

### 问题

API 层本身无药品残留（纯调用 qa_engine），但旧集成测试 `test_server_basic_qa.py` 引用已改名函数 `_run_basic_qa`，无法运行。

### 清理方案

| 文件 | 改动 |
|------|------|
| 删除 `test_server_basic_qa.py` | 已被 `test_api.py` 替代 |
| 新增 `test_api.py` | pytest 风格集成测试 10 个（含端到端 _run_qa） |

### 测试结果

- 集成测试：10 passed

---

## 阶段 7：frontend — 前端 UI 适配

### 问题

前端 5 处残留药品相关颜色/标签/文案。

### 清理方案

| 文件 | 改动 |
|------|------|
| `DebugPanel.tsx` | INTENT_LABELS 移除 disease_drug/drug_disease |
| `GraphPanel.tsx` | LABEL_COLORS 移除 Drug/Producer |
| `GraphRAGDebugPanel.tsx` | TYPE_COLORS/TYPE_LABELS 移除 drug |
| `ChatPanel.tsx` | 文案"18 类问题"→"16 类问题"，移除"药品" |
| `UnifiedChatPanel.tsx` | 文案移除"药品" |

### 测试结果

- TypeScript 编译通过

---

## 阶段 8：docker — 部署适配

### 问题

`docker-init.py` 硬编码旧标签列表含 Drug/Producer。

### 清理方案

| 文件 | 改动 |
|------|------|
| `backend/scripts/docker-init.py` | 标签列表移除 Drug/Producer（6→4） |

---

## 清理总结

### 数据变化

| 指标 | 旧 | 新 |
|------|----|----|
| 爬虫记录 | 8777 条 | 8777 条 |
| Disease 节点 | 8763 | 8763 |
| Drug 节点 | 存在 | 0 ✅ |
| Producer 节点 | 存在 | 0 ✅ |
| 药品关系 | 存在 | 0 ✅ |

### 代码变化

| 模块 | 意图数 | 实体类型 | Cypher 模板 | 关系标签 |
|------|--------|---------|------------|---------|
| KBQA | 18→16 | 6→5 | 18→16 | — |
| GraphRAG | — | 6→5 | — | 11→8 |
| qa_engine | — | — | — | — |
| frontend | — | — | — | — |

### 测试覆盖

| 类型 | 数量 | 结果 |
|------|------|------|
| 单元测试 | 60 | ✅ 全绿 |
| 集成测试 | 43 | ✅ 全绿 |
| **合计** | **103** | **0 失败** |

---

## 后续

第一轮完成后进入第二轮全链路验证（修复旧测试 + 契约测试 + E2E 测试），详见 `round2_verification.md`。
