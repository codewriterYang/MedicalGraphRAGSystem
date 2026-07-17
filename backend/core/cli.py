#!/usr/bin/env python3
# coding: utf-8
"""
CLI 入口模块：提供命令行问答接口和流式输出功能。

将所有问答功能委托给 qa_engine 统一问答引擎。
支持 CLI 交互式问答、流式 token 输出、工作流图导出等。
"""
from backend.domain.qa_engine import build_graph, build_workflow, create_app, stream_qa, QAState
from backend.domain.qa_engine.collect import collect_stream_result
from backend.domain.qa_engine.cli import (
    main,
    setup_langsmith,
    LANGSMITH_AVAILABLE,
    generate_workflow_html,
    render_graph_diagram,
)
from backend.domain.qa_engine.nodes.route import route_question
from backend.domain.qa_engine.nodes.error_handler import handle_error, should_handle_error
from backend.domain.qa_engine.nodes.normalize import normalize_entities
from backend.domain.qa_engine.nodes.template_path import generate_cypher, execute_query, format_answer
from backend.domain.qa_engine.nodes.graphrag_path import (
    extract_rag_entities,
    normalize_rag_entities,
    retrieve_subgraph,
    build_context,
    generate_rag_answer,
)
from backend.core.config import DEFAULT_ANSWER


def log_trace_info(session_id: str, question: str, result: dict) -> None:
    """记录追踪信息到日志（LangSmith 不可用时的本地替代）。

    Args:
        session_id: 会话 ID
        question: 用户问题
        result: 工作流执行结果
    """
    import logging
    _log = logging.getLogger("qa_engine")
    _log.info(
        "Trace | session=%s | route=%s | level=%s | answer_len=%d",
        session_id,
        result.get("route", "unknown"),
        result.get("analysis_level", 0),
        len(result.get("answer", "")),
    )


def record_trace_to_langsmith(result: dict, question: str) -> bool:
    """尝试将追踪记录到 LangSmith（如果可用）。

    Args:
        result: 工作流执行结果
        question: 用户问题

    Returns:
        是否成功记录
    """
    if not LANGSMITH_AVAILABLE:
        return False
    try:
        from langsmith import Client
        client = Client()
        metadata = create_trace_metadata(result, question)
        client.create_run(
            name="qa_workflow",
            inputs={"question": question},
            outputs={"answer": result.get("answer", "")},
            extra={"metadata": metadata},
        )
        return True
    except Exception:
        return False


def create_trace_metadata(result: dict, question: str) -> dict:
    """创建用于 LangSmith 追踪的元数据。
    
    Args:
        result: 工作流执行结果
        question: 用户问题
        
    Returns:
        元数据字典，包含路由信息、子图统计等
    """
    metadata = {
        "question": question,
        "route": result.get("route", "unknown"),
        "analysis_level": result.get("analysis_level"),
    }
    
    # 添加 GraphRAG 特有字段
    subgraph = result.get("subgraph", {})
    if isinstance(subgraph, dict):
        stats = subgraph.get("stats", {})
        if isinstance(stats, dict):
            metadata["subgraph_nodes"] = stats.get("total_nodes")
            metadata["subgraph_edges"] = stats.get("total_edges")
    
    context = result.get("context", {})
    if isinstance(context, dict):
        metadata["context_chars"] = context.get("char_count", context.get("length", 0))
    
    return metadata


# 保持向后兼容的导出
__all__ = [
    "build_graph",
    "build_workflow",
    "create_app",
    "stream_qa",
    "QAState",
    "DEFAULT_ANSWER",
    "setup_langsmith",
    "LANGSMITH_AVAILABLE",
    "route_question",
    "handle_error",
    "should_handle_error",
    "normalize_entities",
    "generate_cypher",
    "execute_query",
    "format_answer",
    "extract_rag_entities",
    "normalize_rag_entities",
    "retrieve_subgraph",
    "build_context",
    "generate_rag_answer",
    "create_trace_metadata",
    "log_trace_info",
    "record_trace_to_langsmith",
    "generate_workflow_html",
    "render_graph_diagram",
    "collect_stream_result",
]

if __name__ == "__main__":
    main()
