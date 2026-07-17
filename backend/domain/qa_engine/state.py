#!/usr/bin/env python3
# coding: utf-8
"""
工作流状态定义模块。

定义 QAState TypedDict，用于在 LangGraph 工作流中传递状态数据。
"""
from typing import TypedDict, Optional


class QAState(TypedDict, total=False):
    """工作流的状态数据结构。"""
    question: str                   # 用户原始问题
    intent: list[str]               # LLM 识别的意图列表
    entities: list[dict]            # LLM 抽取的实体列表
    normalized_entities: dict       # 归一化后的实体字典
    cypher: list[dict]              # 生成的 Cypher 查询组
    params: dict                    # 附加参数（保留扩展）
    raw_results: list[dict]         # Neo4j 查询原始结果
    answer: str                     # 最终格式化答案
    error: str                      # 错误信息（为空表示无错误）
    no_results: bool                # 查询无结果标记
    analysis_level: Optional[int]   # 降级等级（1/2/3）
    
    # GraphRAG 分支字段
    rag_entities: list[dict]        # GraphRAG 提取的实体
    subgraph: dict                  # 检索到的子图数据（节点+边+统计）
    context: dict                   # 构建的文本上下文
    rag_answer: str                 # GraphRAG 路径生成的答案
    route: str                      # 路由标记："template" / "graphrag" / "llm_fallback"
    graph_data: dict                # 前端可视化：{nodes, edges}
    chat_history: list[dict]        # 多轮对话：[{role, content}, ...]
    template_no_result: Optional[bool]  # 模板路径查询无结果时触发 GraphRAG 回退
