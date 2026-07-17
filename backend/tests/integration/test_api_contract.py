#!/usr/bin/env python3
# coding: utf-8
"""
API 契约测试

验证 API 请求/响应格式与前端 TypeScript 类型定义一致。
不依赖 Neo4j/LLM，纯格式验证。
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class TestChatRequestContract:
    """POST /api/chat 请求格式。"""

    def test_chat_request_minimal(self):
        from backend.api.models import ChatRequest
        req = ChatRequest(question="测试问题")
        assert req.question == "测试问题"
        assert req.session_id is None

    def test_chat_request_with_session(self):
        from backend.api.models import ChatRequest
        req = ChatRequest(question="测试", session_id="abc-123")
        assert req.session_id == "abc-123"

    def test_chat_request_rejects_empty(self):
        from backend.api.models import ChatRequest
        import pydantic
        try:
            ChatRequest(question="")
            assert False, "应抛出验证错误"
        except pydantic.ValidationError:
            pass

    def test_chat_request_rejects_too_long(self):
        from backend.api.models import ChatRequest
        import pydantic
        try:
            ChatRequest(question="x" * 501)
            assert False, "应抛出验证错误"
        except pydantic.ValidationError:
            pass


class TestChatResponseContract:
    """POST /api/chat 响应格式。"""

    def test_chat_response_structure(self):
        from backend.api.models import ChatResponse, DebugInfo, GraphData
        resp = ChatResponse(
            answer="测试回答",
            debug=DebugInfo(level=1, intents=["disease_symptom"], entities={}, cypher_queries=[], result_count=3),
            graph_data=GraphData(),
            session_id="test-123",
        )
        data = resp.model_dump()
        assert "answer" in data
        assert "debug" in data
        assert "graph_data" in data
        assert "session_id" in data
        assert data["session_id"] == "test-123"

    def test_debug_info_structure(self):
        from backend.api.models import DebugInfo
        d = DebugInfo(level=1, intents=["disease_symptom"], entities={"disease": ["糖尿病"]}, cypher_queries=[], result_count=5)
        data = d.model_dump()
        assert data["level"] == 1
        assert "disease_symptom" in data["intents"]
        assert "disease" in data["entities"]
        assert data["result_count"] == 5

    def test_graph_data_structure(self):
        from backend.api.models import GraphData, GraphNode, GraphEdge
        gd = GraphData(
            nodes=[GraphNode(id="n1", label="Disease")],
            edges=[GraphEdge(source="n1", target="n2", label="has_symptom")],
        )
        data = gd.model_dump()
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 1
        assert data["nodes"][0]["id"] == "n1"
        assert data["edges"][0]["label"] == "has_symptom"


class TestHealthResponseContract:
    """GET /api/health 响应格式。"""

    def test_health_response_structure(self):
        from backend.api.models import HealthResponse
        resp = HealthResponse(status="ok", neo4j=True, ollama=True, graphrag=True)
        data = resp.model_dump()
        assert data["status"] == "ok"
        assert data["neo4j"] is True
        assert data["ollama"] is True
        assert data["graphrag"] is True

    def test_health_response_degraded(self):
        from backend.api.models import HealthResponse
        resp = HealthResponse(status="degraded", neo4j=True, ollama=False, graphrag=False)
        data = resp.model_dump()
        assert data["status"] == "degraded"


class TestNeighborResponseContract:
    """GET /api/graph/neighbors/{name} 响应格式。"""

    def test_neighbor_response_structure(self):
        from backend.api.models import NeighborResponse, GraphData, GraphNode, GraphEdge
        resp = NeighborResponse(
            center="糖尿病",
            graph_data=GraphData(
                nodes=[GraphNode(id="糖尿病", label="Disease")],
                edges=[],
            ),
        )
        data = resp.model_dump()
        assert data["center"] == "糖尿病"
        assert "graph_data" in data


class TestQAResponseConverter:
    """done 事件 → ChatResponse 转换契约。"""

    def test_done_to_chat_response_fields(self):
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
        resp = done_to_chat_response(done, session_id="s1")
        assert resp.answer == "测试回答"
        assert resp.session_id == "s1"
        assert resp.debug.level == 1
        assert resp.debug.intents == ["disease_symptom"]
        assert resp.debug.result_count == 3

    def test_done_to_chat_response_empty(self):
        from backend.api.qa_response import done_to_chat_response
        resp = done_to_chat_response({})
        assert resp.answer == ""
        assert resp.debug.level == 0

    def test_done_to_chat_response_no_drug_intent_labels(self):
        """响应中不应出现药品意图标签。"""
        from backend.api.qa_response import done_to_chat_response

        done = {
            "answer": "测试",
            "debug": {
                "analysis_level": 1,
                "intents": ["disease_symptom", "disease_cause"],
                "entities": {"disease": ["糖尿病"]},
                "cypher_queries": [],
                "result_count": 2,
            },
            "graph_data": {"nodes": [], "edges": []},
        }
        resp = done_to_chat_response(done)
        for intent in resp.debug.intents:
            assert intent not in ("disease_drug", "drug_disease"), \
                f"不应出现药品意图: {intent}"
