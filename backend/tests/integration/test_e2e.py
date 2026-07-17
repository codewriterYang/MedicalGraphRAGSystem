#!/usr/bin/env python3
# coding: utf-8
"""
E2E 端到端测试

验证完整链路：提问 → 分析 → 路由 → 查询 → 回答。
需要 Neo4j + LLM 连接。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, create_llm

# Neo4j 检测
_neo4j_ok = False
try:
    from py2neo import Graph
    Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)).run("RETURN 1").data()
    _neo4j_ok = True
except Exception:
    pass

# LLM 检测
_llm_ok = False
try:
    llm = create_llm()
    if llm:
        llm.invoke("hi")
        _llm_ok = True
except Exception:
    pass

_services_ok = _neo4j_ok and _llm_ok
skip_no_services = pytest.mark.skipif(not _services_ok, reason="Neo4j 或 LLM 不可用")


@skip_no_services
class TestE2ETemplatePath:
    """E2E：模板路径（KBQA）。"""

    def test_single_entity_symptom_query(self):
        """单实体症状查询：分析→路由→Cypher→回答。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "百日咳有什么症状"},
            config={"configurable": {"thread_id": "e2e-template-1"}},
        )

        assert result.get("route") == "template", f"路由应为 template，实际: {result.get('route')}"
        assert result.get("analysis_level", 0) >= 1
        assert len(result.get("answer", "")) > 0, "回答为空"
        assert "症状" in result.get("answer", ""), "回答应包含症状信息"

    def test_single_entity_cause_query(self):
        """单实体病因查询。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "百日咳是怎么引起的"},
            config={"configurable": {"thread_id": "e2e-template-2"}},
        )

        assert len(result.get("answer", "")) > 0, "回答为空"
        assert result.get("error", "") == "", f"有错误: {result.get('error')}"

    def test_single_entity_food_query(self):
        """单实体饮食查询。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "百日咳不能吃什么"},
            config={"configurable": {"thread_id": "e2e-template-3"}},
        )

        assert len(result.get("answer", "")) > 0, "回答为空"
        assert result.get("error", "") == ""

    def test_no_drug_intent_in_result(self):
        """药品问题不应返回药品意图。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "百日咳吃什么药"},
            config={"configurable": {"thread_id": "e2e-template-4"}},
        )

        intents = result.get("intent", [])
        assert "disease_drug" not in intents, f"不应出现 disease_drug 意图: {intents}"
        assert "drug_disease" not in intents, f"不应出现 drug_disease 意图: {intents}"


@skip_no_services
class TestE2EGraphRAGPath:
    """E2E：GraphRAG 路径。"""

    def test_multi_entity_relation_query(self):
        """多实体关系查询：应走 GraphRAG。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "糖尿病和高血压有什么关系"},
            config={"configurable": {"thread_id": "e2e-graphrag-1"}},
        )

        route = result.get("route", "")
        assert route in ("graphrag", "template_to_graphrag"), \
            f"多实体问题应走 GraphRAG，实际: {route}"
        assert len(result.get("answer", "")) > 0, "回答为空"

    def test_long_question_graphrag(self):
        """长问题应走 GraphRAG。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "如何治疗糖尿病以及它会引起哪些并发症和症状"},
            config={"configurable": {"thread_id": "e2e-graphrag-2"}},
        )

        assert len(result.get("answer", "")) > 0, "回答为空"
        assert result.get("error", "") == ""


@skip_no_services
class TestE2EFallback:
    """E2E：降级和回退。"""

    def test_empty_question_handled(self):
        """空问题不应崩溃。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": ""},
            config={"configurable": {"thread_id": "e2e-fallback-1"}},
        )

        assert "answer" in result

    def test_non_medical_question_handled(self):
        """非医疗问题应有兜底回答。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "今天天气怎么样"},
            config={"configurable": {"thread_id": "e2e-fallback-2"}},
        )

        assert "answer" in result
        assert result.get("error", "") == ""

    def test_result_has_graph_data(self):
        """回答应包含图谱可视化数据。"""
        from backend.domain.qa_engine.graph_builder import create_app

        app = create_app()
        result = app.invoke(
            {"question": "百日咳有什么症状"},
            config={"configurable": {"thread_id": "e2e-fallback-3"}},
        )

        graph_data = result.get("graph_data", {})
        nodes = graph_data.get("nodes", []) if graph_data else []
        # 至少应有中心节点
        assert len(nodes) > 0, "graph_data 应包含节点"
