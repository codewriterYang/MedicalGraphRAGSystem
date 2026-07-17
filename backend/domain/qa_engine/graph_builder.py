#!/usr/bin/env python3
# coding: utf-8
"""
图构建模块。

包含工作流图构建函数和应用创建函数：
- build_workflow: 构建并返回编译前的 StateGraph
- create_app: 创建带有 MemorySaver 检查点的可运行工作流实例

条件边统一使用 step_outcome / select_route_or_error，标签为 success|error|template|graphrag，
避免 LangGraph 导出 PNG 时出现易误解的 True/False。
"""
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import QAState
from .nodes import (
    analyze_with_fallback,
    route_question,
    select_route_or_error,
    normalize_entities,
    generate_cypher,
    execute_query,
    format_answer,
    extract_rag_entities,
    normalize_rag_entities,
    retrieve_subgraph,
    build_context,
    generate_rag_answer,
    handle_error,
    step_outcome,
)

# 全局日志
log = logging.getLogger("qa_engine")

# 条件边标签（与文档 workflow.png 一致）
_OUTCOME_SUCCESS = "success"
_OUTCOME_ERROR = "error"
_ROUTE_TEMPLATE = "template"
_ROUTE_GRAPHRAG = "graphrag"
_FALLBACK_GRAPHRAG = "template_fallback"  # 模板无结果 → GraphRAG 回退

_NODE_ANALYZE = "1. 分析问题\nAnalyze Question"
_NODE_ROUTE = "2. 路由判断\nRoute Question"
_NODE_ERROR = "X. 错误处理\nError Handler"
_NODE_T1 = "T1. 实体归一化\nNormalize Entities"
_NODE_T2 = "T2. 生成Cypher\nGenerate Cypher"
_NODE_T3 = "T3. 执行查询\nExecute Query"
_NODE_T4 = "T4. 格式化答案\nFormat Answer"
_NODE_G1 = "G1. RAG实体抽取\nRAG Entity Extraction"
_NODE_G2 = "G2. RAG实体归一化\nRAG Entity Normalization"
_NODE_G3 = "G3. 子图检索\nSubgraph Retrieval"
_NODE_G4 = "G4. 上下文构建\nContext Building"
_NODE_G5 = "G5. RAG生成回答\nRAG Answer Generation"


def _after_step(next_node: str) -> dict[str, str]:
    """单步节点后的标准条件：成功 → 下一步，失败 → 错误处理。"""
    return {
        _OUTCOME_SUCCESS: next_node,
        _OUTCOME_ERROR: _NODE_ERROR,
    }


def select_query_outcome(state: QAState) -> str:
    """
    T3（执行查询）之后的条件边出口。
    
    模板查询无结果时自动回退到 GraphRAG 路径，而非直接返回"暂无相关信息"。
    添加日志记录回退事件。
    """
    if state.get("template_no_result"):
        log.info("模板路径无结果，自动回退到 GraphRAG 路径")
        return _FALLBACK_GRAPHRAG
    if state.get("error") or state.get("no_results"):
        return _OUTCOME_ERROR
    return _OUTCOME_SUCCESS


def build_workflow() -> StateGraph:
    """构建并返回编译后的问答工作流（集成 GraphRAG 分支）。"""
    workflow = StateGraph(QAState)

    workflow.add_node(_NODE_ANALYZE, analyze_with_fallback)
    workflow.add_node(_NODE_ROUTE, route_question)
    workflow.add_node(_NODE_ERROR, handle_error)

    workflow.add_node(_NODE_T1, normalize_entities)
    workflow.add_node(_NODE_T2, generate_cypher)
    workflow.add_node(_NODE_T3, execute_query)
    workflow.add_node(_NODE_T4, format_answer)

    workflow.add_node(_NODE_G1, extract_rag_entities)
    workflow.add_node(_NODE_G2, normalize_rag_entities)
    workflow.add_node(_NODE_G3, retrieve_subgraph)
    workflow.add_node(_NODE_G4, build_context)
    workflow.add_node(_NODE_G5, generate_rag_answer)

    workflow.set_entry_point(_NODE_ANALYZE)

    # 分析问题：成功 → 路由；失败 → 错误处理
    workflow.add_conditional_edges(
        _NODE_ANALYZE,
        step_outcome,
        {
            _OUTCOME_SUCCESS: _NODE_ROUTE,
            _OUTCOME_ERROR: _NODE_ERROR,
        },
    )

    # 路由：template / graphrag / 失败 → 错误处理
    workflow.add_conditional_edges(
        _NODE_ROUTE,
        select_route_or_error,
        {
            _ROUTE_TEMPLATE: _NODE_T1,
            _ROUTE_GRAPHRAG: _NODE_G1,
            _OUTCOME_ERROR: _NODE_ERROR,
        },
    )

    workflow.add_conditional_edges(_NODE_T1, step_outcome, _after_step(_NODE_T2))
    workflow.add_conditional_edges(_NODE_T2, step_outcome, _after_step(_NODE_T3))
    # T3：查询无结果时自动回退到 GraphRAG 路径（G1），有结果则正常进入 T4
    workflow.add_conditional_edges(
        _NODE_T3,
        select_query_outcome,
        {
            _OUTCOME_SUCCESS: _NODE_T4,
            _FALLBACK_GRAPHRAG: _NODE_G1,
            _OUTCOME_ERROR: _NODE_ERROR,
        },
    )
    workflow.add_conditional_edges(
        _NODE_T4,
        step_outcome,
        {_OUTCOME_SUCCESS: END, _OUTCOME_ERROR: _NODE_ERROR},
    )

    workflow.add_conditional_edges(_NODE_G1, step_outcome, _after_step(_NODE_G2))
    workflow.add_conditional_edges(_NODE_G2, step_outcome, _after_step(_NODE_G3))
    workflow.add_conditional_edges(_NODE_G3, step_outcome, _after_step(_NODE_G4))
    workflow.add_conditional_edges(_NODE_G4, step_outcome, _after_step(_NODE_G5))
    workflow.add_conditional_edges(
        _NODE_G5,
        step_outcome,
        {_OUTCOME_SUCCESS: END, _OUTCOME_ERROR: _NODE_ERROR},
    )

    workflow.add_edge(_NODE_ERROR, END)

    return workflow


def create_app():
    """创建带有 MemorySaver 检查点的可运行工作流实例。"""
    workflow = build_workflow()
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app


def build_graph():
    """构建图并返回编译后的应用（向后兼容接口）。"""
    return create_app()
