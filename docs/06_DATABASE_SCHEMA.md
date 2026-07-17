# 数据库设计 (Database Schema)

版本：v1.0.0 | 状态：Current（描述当前代码实际状态）

---

## 1. 数据库

- **类型**：Neo4j 5.x 图数据库
- **驱动**：py2neo 2021.2
- **连接**：`bolt://127.0.0.1:7687`（本地）/ `bolt://neo4j:7687`（Docker）

---

## 2. 节点标签

| 标签 | 说明 | 数量 | 属性 |
|------|------|------|------|
| `Disease` | 疾病 | ~8,807 | name + 12个属性字段 |
| `Symptom` | 症状 | ~5,998 | name |
| `Drug` | 药品 | ~3,828 | name |
| `Food` | 食物 | ~4,870 | name |
| `Check` | 检查项目 | ~3,353 | name |
| `Department` | 科室 | ~54 | name |
| `Producer` | 药品生产商 | ~17,201 | name |

---

## 3. Disease 节点属性

| 属性 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `name` | string | 疾病名称（唯一标识） | 糖尿病 |
| `desc` | string | 疾病简介 | 糖尿病是一种... |
| `cause` | string | 病因 | 遗传因素... |
| `prevent` | string | 预防措施 | 控制饮食... |
| `cure_way` | string | 治疗方式 | 药物治疗,支持性治疗 |
| `cure_lasttime` | string | 治疗周期 | 6-12个月 |
| `cured_prob` | string | 治愈概率 | 95% |
| `easy_get` | string | 易感人群 | 中老年人 |
| `cost_money` | string | 治疗费用 | 1000-5000元 |
| `get_prob` | string | 患病比例 | 0.1% |
| `get_way` | string | 传染方式 | 无传染性 |
| `yibao_status` | string | 医保状态 | 医保内 |
| `cure_department` | string | 就诊科室 | 内分泌科 |

---

## 4. 关系类型

| 关系类型 | 源标签 | 目标标签 | 中文名 | 数量 |
|----------|--------|---------|--------|------|
| `has_symptom` | Disease | Symptom | 症状 | ~5,998 |
| `acompany_with` | Disease | Disease | 并发症 | ~12,029 |
| `common_drug` | Disease | Drug | 常用药品 | ~14,649 |
| `recommand_drug` | Disease | Drug | 推荐药品 | ~59,467 |
| `do_eat` | Disease | Food | 宜吃 | ~22,238 |
| `no_eat` | Disease | Food | 忌吃 | ~22,247 |
| `recommand_eat` | Disease | Food | 推荐食谱 | ~40,221 |
| `need_check` | Disease | Check | 检查项目 | ~39,422 |
| `belongs_to` | Disease | Department | 所属科室 | ~8,844 |
| `drugs_of` | Producer | Drug | 生产药品 | ~17,315 |
| `dept_belongs_to` | Department | Department | 上级科室 | 少量 |

所有关系都带有 `name` 属性（值为中文名）。

---

## 5. 索引

构建时自动创建以下索引：

```cypher
CREATE INDEX IF NOT EXISTS FOR (n:Disease) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Symptom) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Drug) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Food) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Check) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Department) ON (n.name)
CREATE INDEX IF NOT EXISTS FOR (n:Producer) ON (n.name)
```

---

## 6. 关键查询模式

### 6.1 模板 Cypher（精确查询）

```cypher
-- 疾病症状
MATCH (m:Disease)-[r:has_symptom]->(n:Symptom)
WHERE m.name = $name RETURN m.name, r.name, n.name

-- 疾病药品
MATCH (m:Disease)-[r:common_drug]->(n:Drug)
WHERE m.name = $name RETURN m.name, r.name, n.name

-- 症状查疾病
MATCH (m:Disease)-[r:has_symptom]->(n:Symptom)
WHERE n.name = $name RETURN m.name, r.name, n.name
```

### 6.2 子图检索（双向邻居）

```cypher
-- 通用邻居查询（双向）
MATCH (n)-[r]-(m)
WHERE n.name = $name
RETURN labels(n)[0] AS n_label, n.name AS n_name,
       type(r) AS r_type, labels(m)[0] AS m_label, m.name AS m_name
LIMIT $limit

-- Disease 属性查询
MATCH (n:Disease) WHERE n.name = $name
RETURN n.desc, n.cause, n.prevent, n.cure_way,
       n.cure_lasttime, n.cured_prob, n.easy_get, n.cost_money
```

### 6.3 邻居查询（前端图谱点击展开）

```cypher
MATCH (n)-[r]-(m)
WHERE n.name = $name
RETURN labels(n)[0] AS n_label, n.name AS n_name,
       type(r) AS r_type, labels(m)[0] AS m_label, m.name AS m_name
LIMIT $limit
```

---

## 7. 数据来源

`backend/data/medical.json`（45 MB）包含约 8,800 条疾病记录，由 `backend/domain/data_spider/` 从医药网站采集。数据已固化，通过 `backend/domain/knowledge_graph/main.py` 导入 Neo4j。

---

## 8. 实体词典（`backend/dict/`）

离线词典供 Level 3 降级和实体模糊匹配使用：

| 文件 | 类型 | 说明 |
|------|------|------|
| `disease.txt` | Disease | 疾病名称 |
| `symptom.txt` | Symptom | 症状名称 |
| `drug.txt` | Drug | 药品名称 |
| `check.txt` | Check | 检查项目 |
| `food.txt` | Food | 食物名称 |
| `department.txt` | Department | 科室名称 |
| `producer.txt` | Producer | 生产商名称 |
| `deny.txt` | - | 否定词（不/别/忌/禁止等） |
