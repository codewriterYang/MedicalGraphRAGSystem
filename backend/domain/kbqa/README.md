# KBQA — 医疗知识图谱模板问答模块

## 概述

`KBQA` 是项目的经典问答核心，基于 **意图识别 + 模板 Cypher 查询 + 图谱检索** 的流水线架构，覆盖 **18 种医疗问答意图**。

> KBQA 的各个组件（LLM 引擎、实体归一化器、Cypher 生成器等）作为"组件库"被 `qa_engine/` 工作流复用。`ChatBot` 类仅作为兼容层保留。

---

## 支持的问答意图

### 疾病类（以 Disease 为核心）

| 意图 ID | 方向 | 示例 |
|---------|------|------|
| `disease_symptom` | 疾病 → 症状 | 糖尿病有什么症状？ |
| `symptom_disease` | 症状 → 疾病 | 头痛是什么病引起的？ |
| `disease_cause` | 疾病 → 病因 | 高血压是怎么得的？ |
| `disease_acompany` | 疾病 → 并发症 | 糖尿病有什么并发症？ |
| `disease_do_food` | 疾病 → 宜吃 | 糖尿病可以吃什么？ |
| `disease_not_food` | 疾病 → 忌口 | 糖尿病不能吃什么？ |
| `disease_drug` | 疾病 → 药品 | 糖尿病用什么药？ |
| `disease_check` | 疾病 → 检查 | 糖尿病做什么检查？ |
| `disease_prevent` | 疾病 → 预防 | 怎么预防糖尿病？ |
| `disease_lasttime` | 疾病 → 周期 | 糖尿病要治疗多久？ |
| `disease_cureway` | 疾病 → 治疗 | 糖尿病怎么治？ |
| `disease_cureprob` | 疾病 → 治愈率 | 糖尿病能治好吗？ |
| `disease_easyget` | 疾病 → 易感 | 哪些人容易得糖尿病？ |
| `disease_desc` | 疾病 → 描述 | 糖尿病是什么？ |

### 跨实体类

| 意图 ID | 方向 | 示例 |
|---------|------|------|
| `check_disease` | 检查 → 疾病 | 血糖检测能查出什么病？ |
| `drug_disease` | 药品 → 疾病 | 二甲双胍治什么病？ |
| `food_do_disease` | 食物 → 有益 | 苦瓜对什么病有益？ |
| `food_not_disease` | 食物 → 有害 | 糖对什么病有害？ |

---

## 流水线架构

```
用户问题
  │
  ▼
┌───────────────────┐
│ LLM 语义分析       │  单次调用 LLM 同时完成意图 + 实体抽取
│ (llm_engine.py)   │  支持 Ollama / OpenAI / Anthropic
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 实体归一化         │  映射到 Neo4j 规范名称
│ (entity_normalizer)│  精确匹配 → 子串包含 → 模糊匹配
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Cypher 查询生成    │  18 套参数化模板，防止注入
│ (cypher_generator) │  自动添加模糊匹配回退查询
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Neo4j 查询执行     │  py2neo 参数化执行
│ (graph_query.py)  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ 答案格式化         │  模板填充 / LLM 润色两种模式
│ (answer_formatter) │
└───────────────────┘
```

---

## 三级降级策略

当 LLM 分析不可用时，自动降级：

| 级别 | 策略 | 触发条件 |
|------|------|----------|
| Level 1 | 全 LLM 分析（意图 + 实体） | LLM 正常、返回结果完整 |
| Level 2 | LLM 实体 + 关键词意图 | LLM 返回实体但无意图 |
| Level 3 | 词典 NER + 关键词意图 | LLM 完全不可用，使用 AC 自动机 + 词典 |

---

## 目录结构

```
KBQA/
├── __init__.py            # 模块入口
├── config.py              # 意图类型定义 + 共享配置导入
├── chatbot.py             # [保留] 问答编排器（三级降级 + 图谱数据提取）
├── llm_engine.py          # LLM 语义分析引擎（多提供商支持）
├── entity_normalizer.py   # 实体归一化器（精确/子串/模糊三级匹配）
├── cypher_generator.py    # 参数化 Cypher 模板生成器
├── graph_query.py         # Neo4j 查询执行器
├── answer_formatter.py    # 答案格式化器（模板/LLM 双模式）
└── main.py                # [已废弃] 旧 CLI 入口（已由 qa_engine/cli.py 接管）
```

---

## 在 qa_engine 中的复用

重构后，KBQA 各组件不再独立对外暴露，而是通过 `qa_engine` 工作流调用：

| KBQA 组件 | qa_engine 调用位置 |
|-----------|-------------------|
| `LLMEngine` | `qa_engine/nodes/analysis.py` |
| `EntityNormalizer` | `qa_engine/nodes/normalize.py` |
| `CypherGenerator` | `qa_engine/nodes/template_path.py` |
| `GraphQueryExecutor` | `qa_engine/nodes/template_path.py` |
| `AnswerFormatter` | `qa_engine/nodes/template_path.py` |

无需修改 KBQA 代码即可接入 LangGraph 工作流，保持向后兼容。

---

## 配置

意图类型定义在 `KBQA/config.py` 的 `INTENT_TYPES` 字典中，每种意图包含：

```python
"disease_symptom": {
    "entity_type": "disease",    # 要求的主实体类型
    "desc": "查询疾病的症状"       # 描述
}
```

共享配置（Neo4j 连接、LLM 参数）从 `settings.py` 导入。
