#!/usr/bin/env python3
# coding: utf-8
"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---- 请求 ----
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="用户问题")
    session_id: Optional[str] = Field(
        None,
        max_length=128,
        description="会话 ID，用于多轮对话；不传则由服务端生成或复用默认线程",
    )


# ---- 响应子模型 ----
class CypherQuery(BaseModel):
    cypher: str
    params: dict


class DebugInfo(BaseModel):
    level: int = Field(0, description="降级等级: 1=全LLM, 2=LLM实体+关键词, 3=词典NER")
    intents: list[str] = []
    entities: dict[str, list[str]] = {}
    cypher_queries: list[CypherQuery] = []
    result_count: int = 0


class GraphNode(BaseModel):
    id: str
    label: str


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class GraphData(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class ChatResponse(BaseModel):
    answer: str
    debug: DebugInfo
    graph_data: GraphData
    session_id: Optional[str] = Field(None, description="本次问答使用的会话 ID，后续请求可复用")


# ---- 邻居查询 ----
class NeighborResponse(BaseModel):
    center: str
    graph_data: GraphData


# ---- 健康检查 ----
class HealthResponse(BaseModel):
    status: str
    neo4j: bool
    ollama: bool
    graphrag: bool = False
