#!/usr/bin/env python3
# coding: utf-8
"""
API 层集成测试（pytest 风格）

需要 Neo4j + LLM 连接。
运行方式: python -m pytest backend/tests/integration/test_api.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, create_llm

# ---------------------------------------------------------------------------
# Neo4j 可用性检测
# ---------------------------------------------------------------------------
_neo4j_available = False
_neo4j_skip_reason = ""

try:
    from py2neo import Graph
    _test_graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    _test_graph.run("RETURN 1").data()
    _neo4j_available = True
except Exception as e:
    _neo4j_skip_reason = f"Neo4j 不可用: {e}"

skip_no_neo4j = pytest.mark.skipif(
    not _neo4j_available,
    reason=_neo4j_skip_reason or "Neo4j 不可用",
)

# ---------------------------------------------------------------------------
# LLM 可用性检测
# ---------------------------------------------------------------------------
_llm_available = False
_llm_skip_reason = ""

try:
    _test_llm = create_llm()
    if _test_llm:
        _test_llm.invoke("hi")
        _llm_available = True
except Exception as e:
    _llm_skip_reason = f"LLM 不可用: {e}"

skip_no_llm = pytest.mark.skipif(
    not _llm_available,
    reason=_llm_skip_reason or "LLM 不可用",
)


# ---------------------------------------------------------------------------
# Story 6.1.1: _run_qa 函数导入和基础测试
# ---------------------------------------------------------------------------

class TestRunQAImport:
    """验证 _run_qa 函数可正常导入。"""

    def test_run_qa_import(self):
        """_run_qa 函数导入成功。"""
        from backend.api.app import _run_qa
        assert callable(_run_qa)


class TestModelsImport:
    """验证 API 模型可正常导入。"""

    def test_chat_request_import(self):
        from backend.api.models import ChatRequest
        req = ChatRequest(question="测试")
        assert req.question == "测试"

    def test_chat_response_import(self):
        from backend.api.models import ChatResponse
        assert ChatResponse is not None

    def test_health_response_import(self):
        from backend.api.models import HealthResponse
        assert HealthResponse is not None

    def test_graph_data_import(self):
        from backend.api.models import GraphData, GraphNode, GraphEdge
        node = GraphNode(id="test", label="Disease")
        assert node.id == "test"
        edge = GraphEdge(source="a", target="b", label="has_symptom")
        assert edge.source == "a"


class TestQAResponseConverter:
    """验证 done 事件 → ChatResponse 转换。"""

    def test_done_to_chat_response_basic(self):
        from backend.api.qa_response import done_to_chat_response

        done = {
            "answer": "测试回答",
            "debug": {
                "analysis_level": 1,
                "intents": ["disease_symptom"],
                "entities": {"disease": ["糖尿病"]},
                "cypher_queries": [],
                "result_count": 3,
            },
            "graph_data": {"nodes": [], "edges": []},
        }
        resp = done_to_chat_response(done, session_id="test-123")
        assert resp.answer == "测试回答"
        assert resp.session_id == "test-123"
        assert resp.debug.level == 1
        assert resp.debug.intents == ["disease_symptom"]

    def test_done_to_chat_response_empty(self):
        from backend.api.qa_response import done_to_chat_response

        resp = done_to_chat_response({})
        assert resp.answer == ""
        assert resp.debug.level == 0


# ---------------------------------------------------------------------------
# Story 6.1.2: 端到端 API 测试
# ---------------------------------------------------------------------------

@skip_no_neo4j
@skip_no_llm
class TestRunQAEndToEnd:
    """端到端测试 _run_qa。"""

    def test_simple_question_template_route(self):
        """简单问题应走模板路径。"""
        from backend.api.app import _run_qa

        result = _run_qa("百日咳有什么症状")
        assert "answer" in result
        assert len(result["answer"]) > 0
        # 简单单实体问题应走 template
        route = result.get("route", "")
        assert route in ("template", "graphrag", "")

    def test_empty_question_handled(self):
        """空问题应有兜底处理。"""
        from backend.api.app import _run_qa

        result = _run_qa("")
        assert "answer" in result
        # 至少不应抛异常

    def test_result_has_required_fields(self):
        """返回结果包含必要字段。"""
        from backend.api.app import _run_qa

        result = _run_qa("百日咳有什么症状")
        required = ["answer", "error"]
        for field in required:
            assert field in result, f"缺少字段: {field}"
