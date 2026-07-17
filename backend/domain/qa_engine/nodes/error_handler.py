#!/usr/bin/env python3
# coding: utf-8
"""
错误处理节点模块。

包含统一错误处理函数和条件判断函数：
- handle_error: 根据状态中的错误信息返回友好的错误提示或 LLM 兜底回答
- should_handle_error: 判断是否应该跳转到错误处理节点
"""
import logging

from ..state import QAState

# 全局日志
logger = logging.getLogger(__name__)


def _get_llm_model_display() -> str:
    """获取当前 LLM 模型的显示名称（用于前端标签）。"""
    try:
        from backend.core.config import LLM_MODEL
        return str(LLM_MODEL).strip() or "AI"
    except Exception:
        return "AI"


def _generate_llm_fallback_answer(question: str) -> str | None:
    """尝试使用 LLM 直接回答用户问题（最终兜底）。

    当知识图谱和 GraphRAG 路径均无法提供答案时，利用 LLM 自身的
    医学知识生成回答，并附带免责声明。

    Returns:
        LLM 生成的回答，或 None（LLM 不可用时）。
    """
    try:
        from backend.core.config import create_llm, LLM_MODEL
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = create_llm()
        if llm is None:
            logger.warning("LLM 兜底：create_llm() 返回 None，跳过")
            return None

        model_name = str(LLM_MODEL).strip()
        logger.info("LLM 兜底：尝试用 %s 直接回答用户问题", model_name)
        system_prompt = (
            "你是一个医疗健康助手。请基于你的知识回答用户的问题。"
            "如果问题超出你的知识范围或你无法确定答案，请诚实说明。"
            "在回答末尾必须添加：'⚠️ 以上信息仅供参考，不构成医疗建议，请咨询专业医生。'"
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
        response = llm.invoke(messages)
        answer = response.content.strip() if hasattr(response, "content") else str(response).strip()

        if not answer:
            logger.warning("LLM 兜底：%s 返回空回答", model_name)
            return None

        logger.info("LLM 兜底：%s 生成回答成功 (%d 字符)", model_name, len(answer))
        return answer

    except Exception as e:
        logger.warning("LLM 兜底失败 (%s)，回退到静态文本", e)
        return None


def handle_error(state: QAState) -> dict:
    """节点 X：统一错误处理节点。

    策略（优先级从高到低）：
    1. 系统级硬错误（LLM/Neo4j 不可用）→ 返回分类错误提示
    2. 可恢复错误（Cypher生成/实体未识别等）→ 不阻断，尝试 LLM 兜底
    3. 无结果（no_results / template_no_result）→ 尝试用 LLM 直接回答
    4. LLM 不可用 → 返回静态兜底文本

    关键设计：将 Cypher 生成失败、实体未识别等"数据层面"的失败
    视为可恢复，允许 LLM 直接回答，而非返回冰冷的技术错误信息。
    """

    question = state.get("question", "")
    error = state.get("error", "")
    no_results = state.get("no_results", False)
    template_no_result = state.get("template_no_result", False)
    original_route = state.get("route", "")

    # 变量：标记是否为硬错误（直接阻断、不尝试 LLM 兜底）
    is_hard_error = False

    if error:
        logger.error("工作流发生错误: %s", error)

        # 系统级硬错误：直接返回技术错误提示，不兜底
        if "LLM" in error or "analyze" in error or "timeout" in error.lower():
            is_hard_error = True
            return {
                "answer": "AI 服务暂时不可用，请稍后重试。",
                "error": error,
            }
        elif "Neo4j" in error or "graph database" in error.lower():
            is_hard_error = True
            return {
                "answer": "数据库服务暂时不可用，请稍后重试。",
                "error": error,
            }
        elif "Cypher" in error or "cypher" in error or "query" in error.lower():
            is_hard_error = True
            return {
                "answer": "内部查询错误，已记录日志，请稍后重试。",
                "error": error,
            }

        # 其他错误视为可恢复（实体未识别、意图不匹配、生成失败等）
        # → 不清除 error，但允许后续 LLM 兜底
        logger.warning("可恢复错误('%s')，将继续尝试 LLM 兜底", error[:80])

    # 优先级2: 无结果 或 模板无结果 或 可恢复错误 → LLM 兜底
    if no_results or template_no_result or (error and not is_hard_error):
        # 解析本次降级的 route 标签（LLM 成功和失败共用）
        if template_no_result:
            resolved_route = "template_to_graphrag_to_llm"
        elif original_route == "graphrag":
            resolved_route = "graphrag_to_llm"
        elif original_route == "template":
            resolved_route = "template_to_llm"
        else:
            resolved_route = "llm_fallback"

        if question:
            logger.info("进入 LLM 兜底（question=%r, no_results=%s, template_no_result=%s, error=%r）",
                        question[:60], no_results, template_no_result, error[:40] if error else "")
            llm_answer = _generate_llm_fallback_answer(question)
            if llm_answer:
                return {
                    "answer": llm_answer,
                    "error": "",
                    "route": resolved_route,
                    "llm_model": _get_llm_model_display(),
                }

        # 优先级3: LLM 不可用 → 静态兜底（告知用户尝试了哪些路径）
        logger.info("LLM 兜底不可用，返回静态提示文本")
        attempted = []
        if template_no_result:
            attempted.append("知识库检索")
        if original_route == "graphrag" or (template_no_result and no_results):
            attempted.append("知识图谱分析")
        path_hint = f"（已尝试{' → '.join(attempted)}）" if attempted else ""
        return {
            "answer": f"抱歉，暂时无法回答您的问题{path_hint}。建议您换一种方式提问，或咨询专业医生。",
            "error": "",
            "route": resolved_route,
            "llm_model": _get_llm_model_display(),
        }

    # 边界情况: 没有错误也没有结果标记（不应出现）
    logger.warning("进入边界兜底（无error/no_results 标记），question=%r", question[:60])
    return {
        "answer": "抱歉，系统暂时无法处理您的问题，请重试或联系管理员。",
        "error": "",
    }


def should_handle_error(state: QAState) -> bool:
    """判断是否应该跳转到错误处理节点。"""
    return bool(state.get("error")) or bool(state.get("no_results"))


def step_outcome(state: QAState) -> str:
    """
    条件边出口标签（用于图可视化与阅读）。

    - success：本步成功，进入下一业务节点
    - error：进入 X. 错误处理
    """
    return "error" if should_handle_error(state) else "success"
