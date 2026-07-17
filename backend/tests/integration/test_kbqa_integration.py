#!/usr/bin/env python3
# coding: utf-8
"""
KBQA 集成测试

需要 Neo4j 连接 + 已导入的图谱数据。
运行方式: python -m pytest backend/tests/integration/test_kbqa_integration.py -v
跳过条件: Neo4j 不可用时自动跳过所有测试。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.kbqa.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from backend.domain.kbqa.cypher_generator import CypherGenerator, CYPHER_TEMPLATES
from backend.domain.kbqa.graph_query import GraphQueryExecutor

# ---------------------------------------------------------------------------
# Neo4j 可用性检测
# ---------------------------------------------------------------------------
_neo4j_available = False
_neo4j_skip_reason = ""

try:
    from py2neo import Graph
    _test_graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    # 尝试一个简单查询验证连通性
    _test_graph.run("RETURN 1").data()
    _neo4j_available = True
except Exception as e:
    _neo4j_skip_reason = f"Neo4j 不可用: {e}"


skip_no_neo4j = pytest.mark.skipif(
    not _neo4j_available,
    reason=_neo4j_skip_reason or "Neo4j 不可用",
)


# ---------------------------------------------------------------------------
# Story 3.2.1: 16 种意图各一条典型问题
# ---------------------------------------------------------------------------

# 每种意图对应一条典型查询（使用图谱中存在的疾病名称）
TYPICAL_QUERIES = {
    "disease_symptom":   "百日咳",
    "symptom_disease":   "咳嗽",
    "disease_cause":     "百日咳",
    "disease_acompany":  "百日咳",
    "disease_do_food":   "百日咳",
    "disease_not_food":  "百日咳",
    "disease_check":     "百日咳",
    "disease_prevent":   "百日咳",
    "disease_lasttime":  "百日咳",
    "disease_cureway":   "百日咳",
    "disease_cureprob":  "百日咳",
    "disease_easyget":   "百日咳",
    "disease_desc":      "百日咳",
    "check_disease":     "血常规",
    "food_do_disease":   "苹果",
    "food_not_disease":  "白酒",
}


@skip_no_neo4j
class TestKBQAIntegration:
    """集成测试：验证 16 种意图的 Cypher 查询能正确执行并返回结果。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.generator = CypherGenerator()
        self.executor = GraphQueryExecutor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    @pytest.mark.parametrize("intent,entity_name", list(TYPICAL_QUERIES.items()))
    def test_intent_returns_results(self, intent, entity_name):
        """每种意图查询应返回非空结果。"""
        # 构造查询
        entity_dict = {}
        intent_info = {"disease_symptom": "disease", "symptom_disease": "symptom",
                       "disease_cause": "disease", "disease_acompany": "disease",
                       "disease_do_food": "disease", "disease_not_food": "disease",
                       "disease_check": "disease", "disease_prevent": "disease",
                       "disease_lasttime": "disease", "disease_cureway": "disease",
                       "disease_cureprob": "disease", "disease_easyget": "disease",
                       "disease_desc": "disease", "check_disease": "check",
                       "food_do_disease": "food", "food_not_disease": "food"}
        etype = intent_info[intent]
        entity_dict[etype] = [entity_name]

        query_groups = self.generator.generate([intent], entity_dict)
        assert len(query_groups) > 0, f"意图 {intent} 未生成查询"

        # 执行查询
        results = self.executor.execute(query_groups)
        assert len(results) > 0, f"意图 {intent} 无查询结果"

        # 至少有一个结果组有数据
        has_data = any(len(r["answers"]) > 0 for r in results)
        assert has_data, f"意图 {intent} (实体={entity_name}) 查询结果为空"


# ---------------------------------------------------------------------------
# Story 3.2.2: 药品意图已移除验证
# ---------------------------------------------------------------------------

@skip_no_neo4j
class TestDrugIntentRemoved:
    """验证药品相关意图不再产生查询。"""

    def test_disease_drug_not_in_templates(self):
        """CYPHER_TEMPLATES 中无 disease_drug。"""
        assert "disease_drug" not in CYPHER_TEMPLATES

    def test_drug_disease_not_in_templates(self):
        """CYPHER_TEMPLATES 中无 drug_disease。"""
        assert "drug_disease" not in CYPHER_TEMPLATES

    def test_no_drug_node_in_cypher(self):
        """所有 Cypher 模板不引用 Drug 节点。"""
        for intent, templates in CYPHER_TEMPLATES.items():
            for tmpl in templates:
                assert ":Drug" not in tmpl, f"{intent} 仍引用 Drug"
                assert "common_drug" not in tmpl, f"{intent} 仍引用 common_drug"


# ---------------------------------------------------------------------------
# Story 3.2.3: 端到端验证
# ---------------------------------------------------------------------------

@skip_no_neo4j
class TestEndToEnd:
    """端到端验证：CypherGenerator → GraphQueryExecutor 完整链路。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.generator = CypherGenerator()
        self.executor = GraphQueryExecutor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    def test_disease_symptom_full_chain(self):
        """疾病→症状 完整链路：生成 → 执行 → 有结果。"""
        query_groups = self.generator.generate(
            ["disease_symptom"],
            {"disease": ["百日咳"]},
        )
        results = self.executor.execute(query_groups)

        assert len(results) == 1
        assert results[0]["question_type"] == "disease_symptom"
        answers = results[0]["answers"]
        assert len(answers) > 0, "百日咳应有症状数据"
        # 验证返回的字段
        first = answers[0]
        assert "m.name" in first
        assert "n.name" in first

    def test_disease_desc_full_chain(self):
        """疾病→描述 完整链路。"""
        query_groups = self.generator.generate(
            ["disease_desc"],
            {"disease": ["百日咳"]},
        )
        results = self.executor.execute(query_groups)

        assert len(results) == 1
        answers = results[0]["answers"]
        assert len(answers) > 0
        assert "m.desc" in answers[0]

    def test_multi_intent_query(self):
        """多意图查询：同时查症状和病因。"""
        query_groups = self.generator.generate(
            ["disease_symptom", "disease_cause"],
            {"disease": ["百日咳"]},
        )
        results = self.executor.execute(query_groups)

        assert len(results) == 2
        types = [r["question_type"] for r in results]
        assert "disease_symptom" in types
        assert "disease_cause" in types
