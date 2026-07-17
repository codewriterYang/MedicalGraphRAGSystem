#!/usr/bin/env python3
# coding: utf-8
"""
多轮对话集成测试（pytest assert 风格）

需要 Neo4j + LLM 连接。
"""
from __future__ import annotations

import re
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


class TestEnrichQuestion:
    """enrich_question_with_history 纯函数测试。"""

    def test_no_history_returns_original(self):
        from backend.domain.qa_engine.session import enrich_question_with_history
        result = enrich_question_with_history("感冒了怎么办？", None)
        assert result == "感冒了怎么办？"

    def test_pronoun_with_history_adds_entity(self):
        from backend.domain.qa_engine.session import enrich_question_with_history
        history = [
            {"role": "user", "content": "感冒了怎么办？"},
            {"role": "assistant", "content": "感冒可以通过多休息来缓解..."},
        ]
        result = enrich_question_with_history("那饮食上要注意什么？", history)
        assert "感冒" in result

    def test_non_pronoun_with_history_adds_context(self):
        from backend.domain.qa_engine.session import enrich_question_with_history
        history = [
            {"role": "user", "content": "感冒了怎么办？"},
            {"role": "assistant", "content": "多休息..."},
        ]
        result = enrich_question_with_history("高血压有什么症状？", history)
        assert "对话历史" in result


@skip_no_services
class TestMultiTurnSync:
    """同步模式多轮对话。"""

    def test_two_turns_same_session(self):
        from backend.domain.qa_engine.graph_builder import create_app
        from backend.domain.qa_engine.session import make_thread_config

        app = create_app()
        config = make_thread_config("test-multi-turn-sync")

        r1 = app.invoke({"question": "感冒有什么症状？"}, config=config)
        assert r1.get("answer"), f"第一轮回答为空: {r1.get('error')}"

        r2 = app.invoke({"question": "那饮食上要注意什么？"}, config=config)
        assert r2.get("answer"), f"第二轮回答为空: {r2.get('error')}"

    def test_chat_history_grows(self):
        from backend.domain.qa_engine.graph_builder import create_app
        from backend.domain.qa_engine.session import make_thread_config

        app = create_app()
        config = make_thread_config("test-chkpt-history")

        app.invoke({"question": "感冒有什么症状？"}, config=config)
        s1 = app.get_state(config)
        h1 = s1.values.get("chat_history", []) if s1.values else []
        assert len(h1) > 0, "第一轮后 chat_history 为空"

        app.invoke({"question": "那有什么并发症？"}, config=config)
        s2 = app.get_state(config)
        h2 = s2.values.get("chat_history", []) if s2.values else []
        assert len(h2) > len(h1), f"chat_history 未增长 ({len(h1)} → {len(h2)})"
