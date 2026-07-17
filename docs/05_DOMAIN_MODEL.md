# 领域模型 (Domain Model)

版本：v1.0.0 | 状态：Current（描述当前代码实际状态）

---

## 1. 核心实体类型

| 类型 | Neo4j 标签 | 说明 | 词典规模 |
|------|-----------|------|----------|
| Disease | `Disease` | 疾病（中心实体，带13个属性） | ~8,807 |
| Symptom | `Symptom` | 症状表现 | ~5,998 |
| Drug | `Drug` | 药品名称 | ~3,828 |
| Food | `Food` | 食物名称 | ~4,870 |
| Check | `Check` | 检查项目 | ~3,353 |
| Department | `Department` | 医疗科室 | ~54 |
| Producer | `Producer` | 药品生产商 | ~17,201 |

---

## 2. 关系类型

| 关系 | 方向 | 中文名 | 数量 |
|------|------|--------|------|
| `has_symptom` | Disease → Symptom | 症状 | ~5,998 |
| `acompany_with` | Disease → Disease | 并发症 | ~12,029 |
| `common_drug` | Disease → Drug | 常用药品 | ~14,649 |
| `recommand_drug` | Disease → Drug | 推荐药品 | ~59,467 |
| `do_eat` | Disease → Food | 宜吃 | ~22,238 |
| `no_eat` | Disease → Food | 忌吃 | ~22,247 |
| `recommand_eat` | Disease → Food | 推荐食谱 | ~40,221 |
| `need_check` | Disease → Check | 检查项目 | ~39,422 |
| `belongs_to` | Disease → Department | 所属科室 | ~8,844 |
| `drugs_of` | Producer → Drug | 生产药品 | ~17,315 |
| `dept_belongs_to` | Department → Department | 上级科室 | 少量 |

---

## 3. 18种问答意图

### 疾病类（以 Disease 为核心）

| 意图 ID | 方向 | 所需实体类型 | 示例 |
|---------|------|-------------|------|
| `disease_symptom` | 疾病 → 症状 | disease | 糖尿病有什么症状？ |
| `symptom_disease` | 症状 → 疾病 | symptom | 头痛是什么病？ |
| `disease_cause` | 疾病 → 病因 | disease | 高血压是怎么得的？ |
| `disease_acompany` | 疾病 → 并发症 | disease | 糖尿病有什么并发症？ |
| `disease_do_food` | 疾病 → 宜吃 | disease | 糖尿病可以吃什么？ |
| `disease_not_food` | 疾病 → 忌口 | disease | 糖尿病不能吃什么？ |
| `disease_drug` | 疾病 → 药品 | disease | 糖尿病用什么药？ |
| `disease_check` | 疾病 → 检查 | disease | 糖尿病做什么检查？ |
| `disease_prevent` | 疾病 → 预防 | disease | 怎么预防糖尿病？ |
| `disease_lasttime` | 疾病 → 周期 | disease | 糖尿病要治疗多久？ |
| `disease_cureway` | 疾病 → 治疗 | disease | 糖尿病怎么治？ |
| `disease_cureprob` | 疾病 → 治愈率 | disease | 糖尿病能治好吗？ |
| `disease_easyget` | 疾病 → 易感 | disease | 哪些人容易得糖尿病？ |
| `disease_desc` | 疾病 → 描述 | disease | 糖尿病是什么？ |

### 跨实体类

| 意图 ID | 方向 | 所需实体类型 | 示例 |
|---------|------|-------------|------|
| `check_disease` | 检查 → 疾病 | check | 血糖检测能查出什么病？ |
| `drug_disease` | 药品 → 疾病 | drug | 二甲双胍治什么病？ |
| `food_do_disease` | 食物 → 有益 | food | 苦瓜对什么病有益？ |
| `food_not_disease` | 食物 → 有害 | food | 糖对什么病有害？ |

---

## 4. QAState 状态机

### 4.1 状态字段

```
QAState (TypedDict, total=False)
├── question: str                    # 用户原始问题
├── intent: list[str]                # LLM 识别的意图
├── entities: list[dict]             # LLM 抽取的实体 [{name, type}]
├── normalized_entities: dict        # 归一化实体 {entity_dict, entities}
├── cypher: list[dict]               # Cypher 查询组 [{question_type, queries}]
├── params: dict                     # 附加参数 {has_negation}
├── raw_results: list[dict]          # Neo4j 查询结果 [{question_type, answers}]
├── answer: str                      # 最终答案
├── error: str                       # 错误信息
├── no_results: bool                 # 查询无结果标记
├── analysis_level: int              # 降级等级 1/2/3
├── route: str                       # 路由标记 (6种模式)
├── rag_entities: list[dict]         # GraphRAG 实体
├── subgraph: dict                   # 子图 {nodes, edges, stats}
├── context: dict                    # 上下文 {context_text, char_count}
├── rag_answer: str                  # GraphRAG 答案
├── graph_data: dict                 # 前端图谱 {nodes, edges}
├── chat_history: list[dict]         # 多轮对话 [{role, content}]
├── template_no_result: bool         # 模板无结果→回退标记
└── llm_model: str                   # LLM 模型名（兜底时写入）
```

### 4.2 状态流转

```
__start__
  │
  ▼
[1. 分析问题]
  │ analysis_level=1/2/3
  │ intent, entities 写入
  ▼
[2. 路由判断]
  │ route=template|graphrag
  ├── template ──────────────────────┐
  │   T1: normalized_entities 写入    │
  │   T2: cypher 写入                │
  │   T3: raw_results 写入            │
  │   │  template_no_result=True? ──► G1 (回退)
  │   T4: answer 写入                │
  │                                  │
  └── graphrag ──────────────────────┤
      G1: rag_entities 写入           │
      G2: normalized_entities 写入    │
      G3: subgraph 写入              │
      G4: context 写入               │
      G5: answer 写入, route 写入     │
                                     │
  [X. 错误处理] ◄────────────────────┘
    │ answer 写入 (LLM兜底/静态文本)
    │ route 写入 (llm_fallback等)
    ▼
  __end__
```

---

## 5. 三级降级策略

| 级别 | 策略 | 触发条件 | 依赖 |
|------|------|----------|------|
| Level 1 | 全 LLM 分析（意图 + 实体） | LLM 正常、返回完整 | LLM |
| Level 2 | LLM 实体 + 关键词意图 | LLM 返回实体但无意图 | LLM |
| Level 3 | 词典 NER + 关键词意图 | LLM 完全不可用 | 离线词典 |

---

## 6. 实体归一化匹配策略

| 级别 | 方法 | 说明 |
|------|------|------|
| 1 | 精确匹配 | O(1) set lookup，优先在 expected_type 词典中查 |
| 2 | 子串包含匹配 | 实体名包含词典词条 或 词典词条包含实体名 |
| 3 | 模糊匹配 | rapidfuzz ratio ≥ 80%（可配置），降级用 difflib |

---

## 7. 路由判断规则

| 条件 | 路由 | 说明 |
|------|------|------|
| 无医疗实体 | 直接 LLM 兜底 | 跳过模板/GraphRAG |
| 含比较词（和/与/区别/关系等） | graphrag | 复杂关系问题 |
| 实体数 ≥ 2 | graphrag | 多实体问题 |
| 问题长度 ≥ 20 字 | graphrag | 长问题更复杂 |
| 以上都不满足 | template | 简单单实体查询 |
