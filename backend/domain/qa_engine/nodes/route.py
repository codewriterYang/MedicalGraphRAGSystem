#!/usr/bin/env python3
# coding: utf-8
"""
路由判断节点模块。

包含路由判断函数和条件路由选择函数：
- route_question: 根据问题特征决定走模板问答路径还是 GraphRAG 路径
- select_route: 根据 route 字段选择下一个节点
"""
import logging

from ..state import QAState

# 全局日志
log = logging.getLogger("qa_engine")


def route_question(state: QAState) -> dict:
    """节点2：路由判断节点。
    
    根据问题特征决定走模板问答路径还是 GraphRAG 路径：
    
    模板路径条件（满足任一）：
    - 意图明确（包含已知意图关键词）
    - 实体单一（只有一个实体）
    - 问题较短（< 20 字）
    
    GraphRAG 路径条件（满足任一）：
    - 问题包含多个实体
    - 问题涉及关系比较（如"和"、"与"、"区别"、"关系"等）
    - 意图不明确或问题开放
    - 问题较长（>= 20 字）
    """
    question = state["question"]
    intents = state.get("intent", [])
    entities = state.get("entities", [])
    analysis_level = state.get("analysis_level", 0)
    
    # 统计实体数量
    entity_count = len(entities)
    
    # 快速判断：无任何实体 → 无法查询知识库，跳过模板/GraphRAG，直接 LLM 兜底
    if entity_count == 0:
        log.info("路由判断: 无医疗实体（Level %d），直接 LLM 兜底", analysis_level)
        return {
            "route": "",
            "error": "未识别到医疗实体",
            "no_results": True,
        }
    
    # 判断是否为复杂问题的关键词
    complex_keywords = {"和", "与", "区别", "关系", "比较", "对比", "关联", "联系", "影响"}
    has_complex_indicator = any(kw in question for kw in complex_keywords)
    
    # 判断条件
    if has_complex_indicator or entity_count >= 2 or len(question) >= 20:
        # 复杂问题：走 GraphRAG 路径
        log.info(f"路由选择: GraphRAG（实体数: {entity_count}, 问题长度: {len(question)}, 含比较词: {has_complex_indicator}）")
        return {
            "route": "graphrag",
            "error": "",
            "no_results": False,
        }
    else:
        # 简单问题：走模板路径
        log.info(f"路由选择: 模板问答（实体数: {entity_count}, 意图: {intents}）")
        return {
            "route": "template",
            "error": "",
            "no_results": False,
        }


def select_route(state: QAState) -> str:
    """根据 route 字段选择下一个节点（兼容旧调用）。"""
    return select_route_or_error(state)


def select_route_or_error(state: QAState) -> str:
    """
    路由条件边：template / graphrag / error。

    当 state 含 error、no_results，或 route 非法时走 error → 错误处理节点。
    """
    from .error_handler import should_handle_error

    if should_handle_error(state):
        return "error"
    route = state.get("route", "")
    if route == "graphrag":
        return "graphrag"
    if route == "template":
        return "template"
    log.warning("路由失败，未知 route=%s", route)
    return "error"
