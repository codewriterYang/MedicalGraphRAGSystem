#!/usr/bin/env python3
# coding: utf-8
"""
模板问答路径节点模块。

包含模板问答路径的三个节点函数：
- generate_cypher: 根据意图和归一化实体生成参数化 Cypher 查询
- execute_query: 执行参数化 Cypher 查询，获取 Neo4j 数据
- format_answer: 将查询结果格式化为自然语言答案
"""
import logging

from ..state import QAState
from ..graph_utils import build_graph_data_from_raw_results
from ..session import append_chat_turn

# 全局日志
log = logging.getLogger("qa_engine")

# 模块级单例（延迟初始化）
_cypher_gen = None
_formatter = None
_query_executor = None


def _init_dependencies():
    """延迟初始化依赖模块。"""
    global _cypher_gen, _formatter, _query_executor
    if _cypher_gen is None:
        from backend.domain.kbqa.cypher_generator import CypherGenerator
        from backend.domain.kbqa.answer_formatter import AnswerFormatter
        _cypher_gen = CypherGenerator()
        _formatter = AnswerFormatter(mode="template")


def _get_query_executor():
    """延迟获取 Neo4j 查询执行器。"""
    global _query_executor
    if _query_executor is None:
        from backend.domain.kbqa.graph_query import GraphQueryExecutor
        _query_executor = GraphQueryExecutor()
    return _query_executor


def _validate_entity_intent_match(intents: list[str], entity_dict: dict) -> dict:
    """验证实体类型与意图是否匹配。"""
    from backend.domain.kbqa.config import INTENT_TYPES
    
    validated = {}
    
    for intent in intents:
        intent_info = INTENT_TYPES.get(intent, {})
        required_type = intent_info.get("entity_type", "disease")
        
        if required_type in entity_dict:
            if required_type not in validated:
                validated[required_type] = []
            validated[required_type].extend(entity_dict[required_type])
        else:
            log.debug("意图 %s 需要 %s 类型实体，但未找到，尝试其他类型", intent, required_type)
            if "disease" in entity_dict and required_type != "disease":
                if "disease" not in validated:
                    validated["disease"] = []
                validated["disease"].extend(entity_dict["disease"])
    
    for etype in validated:
        validated[etype] = list(dict.fromkeys(validated[etype]))
    
    return validated


def _add_fallback_queries(query_groups: list[dict], entity_dict: dict) -> list[dict]:
    """为查询组添加回退查询（模糊匹配）。"""
    enhanced_groups = []
    
    for group in query_groups:
        question_type = group["question_type"]
        queries = group["queries"].copy()
        
        new_queries = []
        for query in queries:
            cypher = query["cypher"]
            params = query["params"]
            
            new_queries.append(query)
            
            if "$name" in cypher:
                fuzzy_cypher = cypher.replace(
                    "WHERE m.name = $name",
                    "WHERE m.name CONTAINS $name"
                ).replace(
                    "WHERE n.name = $name",
                    "WHERE n.name CONTAINS $name"
                )
                
                if fuzzy_cypher != cypher:
                    new_queries.append({
                        "cypher": fuzzy_cypher,
                        "params": params,
                        "fallback": True
                    })
        
        enhanced_groups.append({
            "question_type": question_type,
            "queries": new_queries
        })
    
    return enhanced_groups


def _add_entity_type_queries(query_groups: list[dict], intents: list[str], entity_dict: dict) -> list[dict]:
    """添加实体类型级别的通用查询。"""
    from backend.domain.kbqa.config import INTENT_TYPES
    
    existing_types = set(g["question_type"] for g in query_groups)
    
    for intent in intents:
        if intent in existing_types:
            continue
        
        intent_info = INTENT_TYPES.get(intent, {})
        entity_type = intent_info.get("entity_type", "disease")
        
        if entity_type in entity_dict:
            generic_queries = _generate_generic_queries(intent, entity_type)
            if generic_queries:
                query_groups.append({
                    "question_type": intent,
                    "queries": generic_queries
                })
    
    return query_groups


def _generate_generic_queries(intent: str, entity_type: str) -> list[dict]:
    """为指定意图和实体类型生成通用查询。"""
    if entity_type == "disease" and intent == "disease_desc":
        return [{
            "cypher": "MATCH (m:Disease) RETURN m.name, m.desc LIMIT 5",
            "params": {},
            "generic": True
        }]
    
    return []


def generate_cypher(state: QAState) -> dict:
    """节点4（模板路径）：根据意图和归一化实体生成参数化 Cypher 查询（增强版）。

    优化点：
    1. 实体-意图类型匹配验证：确保实体类型与意图要求的类型一致
    2. 回退查询策略：添加模糊匹配查询作为备选方案
    3. 多实体组合：支持同一意图下多个实体的查询组合

    **关键设计**：Cypher 生成失败时视为"查询无结果"而非"致命错误"，
    设置 `template_no_result = True`（不设 error），让工作流自动回退到
    GraphRAG 路径或 LLM 兜底，而非直接返回静态错误文本。
    """
    # 延迟初始化依赖
    _init_dependencies()

    intents = state.get("intent", [])
    normalized = state.get("normalized_entities", {})
    entity_dict = normalized.get("entity_dict", {})

    # 无意图 → 标记为模板无结果，走回退链路
    if not intents:
        log.warning("未识别到有效意图，将回退到 GraphRAG/LLM 兜底")
        return {
            "cypher": [],
            "template_no_result": True,
            "error": "",
            "no_results": False,
        }

    # 优化1: 实体-意图类型匹配验证
    validated_entity_dict = _validate_entity_intent_match(intents, entity_dict)

    if not validated_entity_dict:
        log.warning("实体类型与意图不匹配，将回退到 GraphRAG/LLM 兜底")
        return {
            "cypher": [],
            "template_no_result": True,
            "error": "",
            "no_results": False,
        }

    # 生成主查询（包含异常保护）
    try:
        query_groups = _cypher_gen.generate(intents, validated_entity_dict)
    except Exception as e:
        log.warning("CypherGenerator.generate() 异常 (%s)，将回退到 GraphRAG/LLM 兜底", e)
        return {
            "cypher": [],
            "template_no_result": True,
            "error": "",
            "no_results": False,
        }

    if not query_groups:
        log.warning("CypherGenerator.generate() 返回空，将回退到 GraphRAG/LLM 兜底")
        return {
            "cypher": [],
            "template_no_result": True,
            "error": "",
            "no_results": False,
        }

    # 优化2: 添加回退查询策略（模糊匹配作为备选）
    query_groups = _add_fallback_queries(query_groups, validated_entity_dict)

    # 优化3: 添加实体类型查询（当没有具体实体时的通用查询）
    query_groups = _add_entity_type_queries(query_groups, intents, validated_entity_dict)

    return {
        "cypher": query_groups,
        "error": "",
        "no_results": False,
    }


def execute_query(state: QAState) -> dict:
    """节点5（模板路径）：执行参数化 Cypher 查询，获取 Neo4j 数据。"""
    query_groups = state.get("cypher", [])
    
    if not query_groups:
        log.info("无 Cypher 查询可供执行，将回退到 GraphRAG 路径")
        return {
            "raw_results": [],
            "error": "",
            "no_results": False,
            "template_no_result": True,
        }

    executor = _get_query_executor()
    results = executor.execute(query_groups)
    
    # 检查是否有有效结果
    total_answers = sum(len(r.get("answers", [])) for r in results)
    
    if total_answers == 0:
        # 查询执行成功但无结果 → 触发 GraphRAG 自动回退
        log.info("模板路径查询无结果，将自动回退到 GraphRAG 路径")
        return {
            "raw_results": results,
            "graph_data": build_graph_data_from_raw_results(results, _entity_dict_from_state(state)),
            "error": "",
            "no_results": False,           # 非错误，避免进入错误处理
            "template_no_result": True,    # 触发条件边跳转到 GraphRAG 路径
        }

    entity_dict = _entity_dict_from_state(state)
    return {
        "raw_results": results,
        "graph_data": build_graph_data_from_raw_results(results, entity_dict),
        "error": "",
        "no_results": False,
    }


def _entity_dict_from_state(state: QAState) -> dict:
    """从 state 提取归一化实体字典。"""
    normalized = state.get("normalized_entities") or {}
    if isinstance(normalized, dict):
        return normalized.get("entity_dict", {}) or {}
    return {}


def format_answer(state: QAState) -> dict:
    """节点6（模板路径）：将查询结果格式化为自然语言答案。"""
    # 延迟初始化依赖
    _init_dependencies()
    
    raw_results = state.get("raw_results", [])
    no_results = state.get("no_results", False)
    
    # 模板路径无结果已触发回退时，不生成默认答案，保留空字符串等待 GraphRAG 填充
    if state.get("template_no_result"):
        return {
            "answer": "",
            "error": "",
            "no_results": False,
        }
    
    if no_results:
        # 由 handle_error 统一处理
        return {
            "answer": "",
            "error": "",
        }
    
    if not raw_results:
        return {
            "answer": "",
            "error": "模板路径查询无结果",
            "no_results": True,
        }

    answer = _formatter.format(raw_results)
    
    if not answer:
        return {
            "answer": "",
            "error": "答案格式化失败",
            "no_results": True,
        }

    entity_dict = _entity_dict_from_state(state)
    graph_data = state.get("graph_data") or build_graph_data_from_raw_results(
        raw_results, entity_dict
    )
    chat_history = append_chat_turn(
        state.get("chat_history"),
        state.get("question", ""),
        answer,
    )

    return {
        "answer": answer,
        "graph_data": graph_data,
        "chat_history": chat_history,
        "error": "",
        "no_results": False,
    }
