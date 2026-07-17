#!/usr/bin/env python3
# coding: utf-8
"""
非流式结果收集：消费 stream_qa 直至 done，与流式端点数据一致。
"""
from __future__ import annotations

from typing import Any

from .stream import stream_qa
from .session import make_thread_config


async def collect_stream_result(
    question: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    运行 stream_qa 并返回 done 事件载荷。

    返回字段：answer, debug, graph_data, mode, session_id
    """
    config = make_thread_config(session_id)
    sid = config["configurable"]["thread_id"]
    done_payload: dict[str, Any] = {
        "answer": "",
        "debug": {},
        "graph_data": {"nodes": [], "edges": []},
        "mode": "template",
        "session_id": sid,
    }

    async for event in stream_qa(question, config=config):
        if event.get("event") == "done":
            done_payload = {
                "answer": event.get("answer", ""),
                "debug": event.get("debug", {}),
                "graph_data": event.get("graph_data") or {"nodes": [], "edges": []},
                "mode": event.get("mode", "template"),
                "session_id": sid,
            }
            break
        if event.get("event") == "error":
            done_payload["answer"] = event.get("message", "问答失败")
            done_payload["debug"] = {"error": done_payload["answer"]}
            break

    return done_payload
