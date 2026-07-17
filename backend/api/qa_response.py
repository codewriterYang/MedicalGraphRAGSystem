#!/usr/bin/env python3
# coding: utf-8
"""
将 qa_engine stream done 载荷转换为 FastAPI 响应模型。
"""
from __future__ import annotations

from backend.api.models import (
    ChatResponse,
    GraphData,
    GraphNode,
    GraphEdge,
    DebugInfo,
    CypherQuery,
)


def _to_graph_data(data: dict | None) -> GraphData:
    if not data:
        return GraphData()
    nodes = [
        GraphNode(id=str(n.get("id", "")), label=str(n.get("label", "Entity")))
        for n in (data.get("nodes") or [])
        if n.get("id")
    ]
    edges = [
        GraphEdge(
            source=str(e.get("source", "")),
            target=str(e.get("target", "")),
            label=str(e.get("label", "")),
        )
        for e in (data.get("edges") or [])
        if e.get("source") and e.get("target")
    ]
    return GraphData(nodes=nodes, edges=edges)


def done_to_chat_response(done: dict, session_id: str | None = None) -> ChatResponse:
    """done 事件 → ChatResponse（含 graph_data）。"""
    debug_raw = done.get("debug") or {}
    cypher_queries = []
    for q in debug_raw.get("cypher_queries") or []:
        if isinstance(q, dict):
            cypher_queries.append(CypherQuery(
                cypher=q.get("cypher", ""),
                params=q.get("params", {}),
            ))

    level = debug_raw.get("analysis_level", debug_raw.get("level", 0))
    if level is None:
        level = 0

    answer = done.get("answer", "")
    if not answer and debug_raw.get("error"):
        answer = str(debug_raw["error"])

    sid = done.get("session_id") or session_id

    return ChatResponse(
        answer=answer,
        debug=DebugInfo(
            level=int(level) if isinstance(level, (int, float)) else 0,
            intents=list(debug_raw.get("intents") or []),
            entities=dict(debug_raw.get("entities") or {}),
            cypher_queries=cypher_queries,
            result_count=int(debug_raw.get("result_count") or 0),
        ),
        graph_data=_to_graph_data(done.get("graph_data")),
        session_id=sid,
    )
