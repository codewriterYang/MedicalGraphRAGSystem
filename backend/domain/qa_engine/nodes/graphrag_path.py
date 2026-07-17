#!/usr/bin/env python3
# coding: utf-8
"""
GraphRAG 路径节点模块。

包含 GraphRAG 路径的五个节点函数：
- extract_rag_entities: 使用 GraphRAG 实体抽取器提取实体
- normalize_rag_entities: 将 GraphRAG 提取的实体归一化
- retrieve_subgraph: 检索围绕实体的多跳子图
- build_context: 将子图转换为 LLM 可读的文本上下文
- generate_rag_answer: 基于问题和上下文生成最终回答
"""
import logging

from ..state import QAState
from ..graph_utils import build_graph_data_from_subgraph
from ..session import append_chat_turn

# 全局日志
log = logging.getLogger("qa_engine")

# 模块级单例（延迟初始化）
_rag_extractor = None
_rag_retriever = None
_rag_context_builder = None
_rag_generator = None
_normalizer = None


def _init_dependencies():
    """延迟初始化依赖模块。"""
    global _rag_extractor, _rag_retriever, _rag_context_builder, _rag_generator, _normalizer
    
    if _rag_extractor is not None:
        return
    
    try:
        from backend.core.config import create_llm
        from backend.domain.kbqa.entity_normalizer import EntityNormalizer
        from backend.domain.graphrag.entity_extractor import EntityExtractor
        from backend.domain.graphrag.subgraph_retriever import SubgraphRetriever
        from backend.domain.graphrag.context_builder import ContextBuilder
        from backend.domain.graphrag.generator import GraphRAGGenerator
        
        llm = create_llm()
        _rag_extractor = EntityExtractor(llm=llm)
        _rag_retriever = SubgraphRetriever()
        _rag_context_builder = ContextBuilder()
        _rag_generator = GraphRAGGenerator(llm=llm)
        _normalizer = EntityNormalizer()
        log.info("GraphRAG 组件初始化完成")
    except Exception as e:
        log.warning(f"GraphRAG 组件初始化失败: {e}")


def extract_rag_entities(state: QAState) -> dict:
    """节点G1（GraphRAG路径）：使用 GraphRAG 实体抽取器提取实体。"""
    _init_dependencies()
    
    question = state["question"]
    
    if not _rag_extractor:
        return {
            "rag_entities": [],
            "error": "GraphRAG 实体抽取器不可用",
            "no_results": True,
        }
    
    try:
        entities = _rag_extractor.extract(question)
        if not entities:
            return {
                "rag_entities": [],
                "error": "GraphRAG 未提取到实体",
                "no_results": True,
            }
        
        log.info(f"GraphRAG 提取实体: {entities}")
        return {
            "rag_entities": entities,
            "error": "",
            "no_results": False,
        }
    except Exception as e:
        log.error(f"GraphRAG 实体抽取失败: {e}")
        return {
            "rag_entities": [],
            "error": f"实体抽取失败: {str(e)}",
            "no_results": True,
        }


def normalize_rag_entities(state: QAState) -> dict:
    """节点G2（GraphRAG路径）：将 GraphRAG 提取的实体归一化。"""
    _init_dependencies()
    
    rag_entities = state.get("rag_entities", [])
    
    if not rag_entities:
        return {
            "normalized_entities": {"entity_dict": {}, "entities": {}},
            "error": "GraphRAG 无实体可归一化",
            "no_results": True,
        }
    
    try:
        normalized = _normalizer.normalize(rag_entities, has_negation=False)
        entity_dict = normalized.get("entity_dict", {})
        
        if not entity_dict:
            return {
                "normalized_entities": normalized,
                "error": "GraphRAG 实体归一化后无匹配",
                "no_results": True,
            }
        
        log.info(f"GraphRAG 归一化实体: {entity_dict}")
        return {
            "normalized_entities": normalized,
            "error": "",
            "no_results": False,
        }
    except Exception as e:
        log.error(f"GraphRAG 实体归一化失败: {e}")
        return {
            "normalized_entities": {},
            "error": f"实体归一化失败: {str(e)}",
            "no_results": True,
        }


def retrieve_subgraph(state: QAState) -> dict:
    """节点G3（GraphRAG路径）：检索围绕实体的多跳子图。"""
    _init_dependencies()
    
    normalized = state.get("normalized_entities", {})
    entity_dict = normalized.get("entity_dict", {})
    
    if not entity_dict:
        return {
            "subgraph": {},
            "error": "无归一化实体用于子图检索",
            "no_results": True,
        }
    
    if not _rag_retriever:
        return {
            "subgraph": {},
            "error": "GraphRAG 子图检索器不可用",
            "no_results": True,
        }
    
    try:
        subgraph = _rag_retriever.retrieve(entity_dict)
        stats = subgraph.get("stats", {})
        
        if stats.get("total_nodes", 0) == 0:
            return {
                "subgraph": subgraph,
                "error": "子图检索无结果",
                "no_results": True,
            }
        
        log.info(f"GraphRAG 子图检索完成: {stats['total_nodes']} 节点, {stats['total_edges']} 边")
        return {
            "subgraph": subgraph,
            "error": "",
            "no_results": False,
        }
    except Exception as e:
        log.error(f"GraphRAG 子图检索失败: {e}")
        return {
            "subgraph": {},
            "error": f"子图检索失败: {str(e)}",
            "no_results": True,
        }


def build_context(state: QAState) -> dict:
    """节点G4（GraphRAG路径）：将子图转换为 LLM 可读的文本上下文。"""
    _init_dependencies()
    
    subgraph = state.get("subgraph", {})
    
    if not subgraph:
        return {
            "context": {},
            "error": "无子图数据用于上下文构建",
            "no_results": True,
        }
    
    if not _rag_context_builder:
        return {
            "context": {},
            "error": "GraphRAG 上下文构建器不可用",
            "no_results": True,
        }
    
    try:
        context_result = _rag_context_builder.build(subgraph)
        
        if not context_result.get("context_text"):
            return {
                "context": context_result,
                "error": "上下文构建结果为空",
                "no_results": True,
            }
        
        log.info(f"GraphRAG 上下文构建完成: {context_result['char_count']} 字符")
        return {
            "context": context_result,
            "error": "",
            "no_results": False,
        }
    except Exception as e:
        log.error(f"GraphRAG 上下文构建失败: {e}")
        return {
            "context": {},
            "error": f"上下文构建失败: {str(e)}",
            "no_results": True,
        }


def generate_rag_answer(state: QAState) -> dict:
    """节点G5（GraphRAG路径）：基于问题和上下文生成最终回答。"""
    _init_dependencies()
    
    question = state["question"]
    context = state.get("context", {})
    context_text = context.get("context_text", "")
    
    if not context_text:
        return {
            "rag_answer": "",
            "error": "无上下文用于生成回答",
            "no_results": True,
        }
    
    if not _rag_generator:
        return {
            "rag_answer": "",
            "error": "GraphRAG 生成器不可用",
            "no_results": True,
        }
    
    try:
        result = _rag_generator.generate(question, context_text)
        answer = result.get("answer", "")
        
        if not answer:
            return {
                "rag_answer": "",
                "error": "GraphRAG 生成结果为空",
                "no_results": True,
            }
        
        log.info(f"GraphRAG 回答生成完成: {len(answer)} 字符")
        
        # 检测 LLM 返回"暂无相关信息"类无效回答，触发 LLM 兜底
        # 图谱可能不包含所需信息（如药品副作用），此时应让 error_handler
        # 调用 LLM 用自身知识回答，而非直接返回"暂无信息"给用户
        _NO_INFO_PATTERNS = [
            "暂无相关信息",
            "暂无相关",
            "暂无信息",
            "没有相关信息",
            "未找到相关",
            "无法提供",
            "不足以回答",
        ]
        if any(p in answer for p in _NO_INFO_PATTERNS):
            log.warning("GraphRAG 回答判定为无效（图谱无相关数据），将触发 LLM 兜底")
            return {
                "rag_answer": answer,
                "answer": answer,
                "error": "图谱数据不足以回答此问题",
                "no_results": True,
            }
        
        graph_data = build_graph_data_from_subgraph(state.get("subgraph"))
        chat_history = append_chat_turn(
            state.get("chat_history"),
            state.get("question", ""),
            answer,
        )
        # 标记路由：区分直接 GraphRAG 还是模板回退到 GraphRAG
        if state.get("template_no_result"):
            log.info("模板路径无结果 → 回退 GraphRAG 成功")
            route = "template_to_graphrag"
        else:
            route = "graphrag"
        return {
            "answer": answer,
            "rag_answer": answer,
            "graph_data": graph_data,
            "chat_history": chat_history,
            "route": route,
            "error": "",
            "no_results": False,
        }
    except Exception as e:
        log.error(f"GraphRAG 回答生成失败: {e}")
        return {
            "rag_answer": "",
            "error": f"回答生成失败: {str(e)}",
            "no_results": True,
        }
