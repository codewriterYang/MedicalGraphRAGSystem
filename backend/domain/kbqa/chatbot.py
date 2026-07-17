#!/usr/bin/env python3
# coding: utf-8
"""
ChatBot — 仅用于 server 的邻居查询(/api/graph/neighbors)和健康检查。
问答功能已由 qa_engine/ 接管。

降级逻辑（_keyword_classify / _fallback_full 等）已统一到 qa_engine/nodes/analysis.py，
此处不再重复维护。
"""
from __future__ import annotations

import logging

from .config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
    LLM_MODEL, LLM_BASE_URL,
)
from .llm_engine import LLMEngine
from .entity_normalizer import EntityNormalizer
from .cypher_generator import CypherGenerator
from .graph_query import GraphQueryExecutor
from .answer_formatter import AnswerFormatter

log = logging.getLogger("qa")


class ChatBot:
    """轻量封装：提供 Neo4j 连接和 LLM 可用性检查。"""

    def __init__(self, neo4j_uri: str = NEO4J_URI, neo4j_user: str = NEO4J_USER,
                 neo4j_password: str = NEO4J_PASSWORD,
                 llm_model: str = LLM_MODEL, llm_base_url: str = LLM_BASE_URL,
                 answer_mode: str = "template", debug: bool = False,
                 ollama_model: str | None = None, ollama_url: str | None = None):
        self.debug = debug
        if ollama_model:
            llm_model = ollama_model
        if ollama_url:
            llm_base_url = ollama_url

        self.llm_engine = LLMEngine(model=llm_model, base_url=llm_base_url)
        self.normalizer = EntityNormalizer()
        self.cypher_gen = CypherGenerator()
        self.graph_query = GraphQueryExecutor(neo4j_uri, neo4j_user, neo4j_password)
        self.formatter = AnswerFormatter(
            mode=answer_mode,
            llm=self.llm_engine.llm if answer_mode == "llm" else None,
        )
