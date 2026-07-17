#!/usr/bin/env python3
# coding: utf-8
"""
流式输出集成测试（pytest assert 风格）

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


class TestStreamQAImport:
    """验证 stream_qa 可正常导入。"""

    def test_stream_qa_import(self):
        from backend.core.cli import stream_qa
        assert callable(stream_qa)

    def test_create_app_import(self):
        from backend.core.cli import create_app
        app = create_app()
        assert hasattr(app, "invoke")


@skip_no_services
class TestStreamQABasic:
    """流式问答基本流程。"""

    @pytest.mark.asyncio
    async def test_stream_qa_receives_events(self):
        from backend.core.cli import stream_qa

        events = []
        async for event in stream_qa("糖尿病有什么症状"):
            events.append(event)

        assert len(events) > 0, "未收到任何事件"
        event_types = {e.get("event") for e in events}
        assert "done" in event_types, f"未收到 done 事件，收到: {event_types}"

    @pytest.mark.asyncio
    async def test_stream_qa_empty_question_handled(self):
        from backend.core.cli import stream_qa

        error_events = 0
        async for event in stream_qa(""):
            if event.get("event") == "error":
                error_events += 1

        # 空问题不应抛异常
        assert error_events == 0, f"空问题触发 {error_events} 个错误事件"

    @pytest.mark.asyncio
    async def test_stream_qa_complex_question(self):
        from backend.core.cli import stream_qa

        route = None
        async for event in stream_qa("糖尿病和高血压有什么关系"):
            if event.get("event") == "done":
                route = event.get("debug", {}).get("route")

        # 多实体问题应走 graphrag 或 template_to_graphrag
        assert route is not None, "未收到 done 事件"
        assert route in ("graphrag", "template_to_graphrag", "template"), \
            f"非预期路由: {route}"


@skip_no_services
class TestSyncInvoke:
    """同步 invoke 兼容性。"""

    def test_sync_invoke_returns_required_fields(self):
        from backend.core.cli import create_app

        app = create_app()
        config = {"configurable": {"thread_id": "test-sync"}}
        result = app.invoke({"question": "糖尿病有什么症状"}, config=config)

        assert "answer" in result
        assert "route" in result
        assert "analysis_level" in result
        assert len(result["answer"]) > 0, "回答为空"
