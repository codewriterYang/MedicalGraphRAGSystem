#!/usr/bin/env python3
# coding: utf-8
"""
实体归一化节点模块。

包含模板路径的实体归一化函数，将 LLM 抽取的实体归一化为知识图谱中的规范名称。
"""
import logging

from ..state import QAState

# 全局日志
log = logging.getLogger("qa_engine")

# 模块级单例（延迟初始化）
_normalizer = None


def _init_dependencies():
    """延迟初始化依赖模块。"""
    global _normalizer
    if _normalizer is None:
        from backend.domain.kbqa.entity_normalizer import EntityNormalizer
        _normalizer = EntityNormalizer()


def normalize_entities(state: QAState) -> dict:
    """节点3（模板路径）：将 LLM 抽取的实体归一化为知识图谱中的规范名称。

    关键设计：归一化失败时不设 error，改为设 template_no_result=True，
    让工作流自动流转到 T2→T3→G1（GraphRAG 路径），而非直接进入错误处理。
    模板路径的任何失败都应先尝试 GraphRAG，GraphRAG 再失败才到 LLM 兜底。
    """
    # 延迟初始化依赖
    _init_dependencies()
    
    entities = state.get("entities", [])
    
    if not entities:
        # 无实体 → 标记模板无结果，交给后续节点流转到 GraphRAG
        log.warning("无实体可供归一化，将回退到 GraphRAG 路径")
        return {
            "normalized_entities": {"entity_dict": {}, "entities": {}},
            "template_no_result": True,
            "error": "",
            "no_results": False,
        }

    has_negation = state.get("params", {}).get("has_negation", False)
    normalized = _normalizer.normalize(entities, has_negation=has_negation)

    if not normalized.get("entity_dict"):
        # 实体归一化后无匹配 → 标记模板无结果，交给后续节点流转到 GraphRAG
        log.warning("实体归一化后无匹配，将回退到 GraphRAG 路径")
        return {
            "normalized_entities": normalized,
            "template_no_result": True,
            "error": "",
            "no_results": False,
        }

    return {
        "normalized_entities": normalized,
        "error": "",
        "no_results": False,
    }
