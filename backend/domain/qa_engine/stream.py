#!/usr/bin/env python3
# coding: utf-8
"""
流式输出模块。

包含异步流式问答函数：
- stream_qa: 异步生成器，逐步返回问答过程中的事件
"""
import logging
from typing import Optional, Any, Dict

from backend.core.config import DEFAULT_ANSWER
from .graph_builder import create_app
from .graph_utils import resolve_graph_data_from_state
from .session import make_thread_config

# 全局日志
log = logging.getLogger("qa_engine")

# 模块级全局 app 单例（复用 MemorySaver，确保多轮对话检查点不会丢失）
# 关键修复：之前每次 stream_qa 调用都 create_app() 新建 MemorySaver，
# 导致上一轮的 chat_history 检查点无法被下一轮读取。
_global_app = None


def get_or_create_app():
    """获取或创建全局 app 单例（含 MemorySaver 检查点，支持多轮会话）。"""
    global _global_app
    if _global_app is None:
        log.info("首次初始化全局 LangGraph 应用（含 MemorySaver）")
        _global_app = create_app()
    return _global_app


async def stream_qa(question: str, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    流式问答函数 - 异步生成器，逐步返回问答过程中的事件。
    
    参数：
        question: 用户问题
        config: 会话配置（可选，用于 MemorySaver 检查点）
    
    生成的事件类型：
        - {"event": "delta", "chunk": token_content}: LLM 正在生成 token
        - {"event": "tool_start", "node": 节点名称}: 节点开始执行
        - {"event": "tool_end", "node": 节点名称, "duration": 耗时毫秒}: 节点执行结束
        - {"event": "done", "answer": 完整答案, "debug": 调试信息, "graph_data": 图谱数据, "mode": 模式}: 工作流完成
        - {"event": "error", "message": 错误信息}: 发生错误
    
    使用示例：
        async for event in stream_qa("糖尿病有什么症状"):
            if event["event"] == "delta":
                print(event["chunk"], end="", flush=True)
            elif event["event"] == "done":
                print(f"\n\n完整答案: {event['answer']}")
    """
    # 使用全局单例 app（复用 MemorySaver，保留多轮对话 state）
    app = get_or_create_app()
    
    # 默认配置（支持调用方传入 session_id / thread_id）
    if config is None:
        config = make_thread_config("stream_session")
    
    # 初始状态
    initial_state = {"question": question}
    
    # 用于收集调试信息
    debug_info = {
        "nodes": [],
        "analysis_level": None,
        "route": None,
        "error": None,
        "no_results": False,
        "intents": [],
        "entities": {},
        "cypher_queries": [],
        "result_count": 0,
        "entities_raw": [],
        "entities_normalized": {},
        "subgraph_stats": {},
        "context_preview": "",
        "context_char_count": 0,
        "generation_time_ms": 0,
        "model_used": "langgraph_engine",
        "total_time_ms": 0,
    }
    
    # 用于收集图谱数据
    graph_data = {
        "nodes": [],
        "edges": [],
    }
    
    # 用于收集最终答案
    final_answer = ""
    
    # 用于收集 LLM 模型名（由 on_chain_end 中多次累积，最终取最后一个有效值）
    _collected_llm_model = ""
    
    # 跟踪已发送的阶段事件，避免重复发送
    _stages_sent = set()
    # 跟踪是否已回退到 GraphRAG（从模板路径）
    _template_fallback_seen = False
    # 跟踪是否已进入 LLM 兜底
    _llm_fallback_seen = False
    
    # 记录开始时间
    import time
    t0 = time.time()
    
    try:
        # 初始阶段：发送分析状态，由后续 on_chain_end 根据实际路由更新
        yield {"event": "status", "stage": "analyze", "message": "正在分析问题..."}
        
        # 使用 LangGraph 的 astream_events API 获取流式事件
        # version="v2" 是推荐的事件格式版本
        async for event in app.astream_events(initial_state, config=config, version="v2"):
            event_type = event.get("event", "")
            
            # ===== LLM 流式输出事件 =====
            if event_type == "on_chat_model_stream":
                # 获取 token 内容
                raw_data = event.get("data", {})
                chunk = raw_data.get("chunk") if isinstance(raw_data, dict) else None
                if chunk is not None:
                    if hasattr(chunk, "content"):
                        content = chunk.content
                    elif isinstance(chunk, dict):
                        content = chunk.get("content", "")
                    else:
                        content = str(chunk)
                    
                    if content:
                        yield {"event": "delta", "chunk": content}
            
            # ===== 工具/节点开始执行事件 =====
            elif event_type == "on_tool_start":
                node_name = event.get("name", "")
                debug_info["nodes"].append({"name": node_name, "status": "start"})
                yield {"event": "tool_start", "node": node_name}
            
            # ===== 工具/节点执行结束事件 =====
            elif event_type == "on_tool_end":
                node_name = event.get("name", "")
                duration = event.get("duration", 0)
                
                # 更新节点状态
                for node in debug_info["nodes"]:
                    if node["name"] == node_name and node["status"] == "start":
                        node["status"] = "end"
                        node["duration"] = duration
                        break
                
                # 尝试提取状态信息（用于 debug）
                raw_data = event.get("data", {})
                result = raw_data.get("output", {}) if isinstance(raw_data, dict) else {}
                if isinstance(result, dict):
                    if "analysis_level" in result:
                        debug_info["analysis_level"] = result["analysis_level"]
                    if "route" in result:
                        debug_info["route"] = result["route"]
                    if "error" in result:
                        debug_info["error"] = result["error"]
                    if "no_results" in result:
                        debug_info["no_results"] = result["no_results"]
                    if "intent" in result:
                        debug_info["intents"] = result["intent"]
                    if "normalized_entities" in result:
                        normalized = result["normalized_entities"]
                        if isinstance(normalized, dict):
                            debug_info["entities"] = normalized.get("entity_dict", {})
                            debug_info["entities_normalized"] = normalized.get("entity_dict", {})
                    if "cypher" in result:
                        cypher_data = result["cypher"]
                        if isinstance(cypher_data, list):
                            queries = []
                            for group in cypher_data:
                                for q in group.get("queries", []):
                                    queries.append({
                                        "cypher": q.get("cypher", ""),
                                        "params": q.get("params", {})
                                    })
                            debug_info["cypher_queries"] = queries
                    if "raw_results" in result:
                        debug_info["result_count"] = len(result["raw_results"])
                    if "rag_entities" in result:
                        debug_info["entities_raw"] = result["rag_entities"]
                    if "subgraph" in result:
                        subgraph = result["subgraph"]
                        if isinstance(subgraph, dict):
                            debug_info["subgraph_stats"] = subgraph.get("stats", {})
                            # 构建图谱数据
                            nodes = subgraph.get("nodes", [])
                            edges = subgraph.get("edges", [])
                            graph_data["nodes"] = [{"id": n["name"], "label": n["label"]} for n in nodes]
                            graph_data["edges"] = [
                                {"source": e["source"], "target": e["target"], "label": e["relationship"]}
                                for e in edges
                            ]
                    if "context" in result:
                        context = result["context"]
                        if isinstance(context, dict):
                            debug_info["context_preview"] = context.get("context_preview", "")[:200]
                            debug_info["context_char_count"] = context.get("char_count", 0)
                
                yield {"event": "tool_end", "node": node_name, "duration": duration}
            
            # ===== 工作流完成事件 =====
            elif event_type == "on_chain_end":
                # 获取当前子链的最终状态（on_chain_end 会多次触发）
                # 条件边输出为字符串（"success"/"template"等），节点输出为 dict
                raw_data = event.get("data", {})
                final_state = raw_data.get("output", {}) if isinstance(raw_data, dict) else {}
                
                if isinstance(final_state, dict):
                    # ===== 阶段检测：根据 state 变化发送 status 事件 =====
                    route_now = final_state.get("route", "")
                    tfr = final_state.get("template_no_result", False)
                    err_now = final_state.get("error", "")
                    
                    # 模板路径阶段
                    if route_now == "template" and "template" not in _stages_sent:
                        _stages_sent.add("template")
                        yield {"event": "status", "stage": "template",
                               "message": "模板检索中..."}
                    
                    # 模板无匹配 → 切换到 GraphRAG
                    if tfr and not _template_fallback_seen:
                        _template_fallback_seen = True
                        yield {"event": "status", "stage": "template_to_graphrag",
                               "message": "模板无匹配，切换至子图检索..."}
                    
                    # GraphRAG 路径阶段
                    if route_now == "graphrag" and "graphrag" not in _stages_sent:
                        _stages_sent.add("graphrag")
                        yield {"event": "status", "stage": "graphrag",
                               "message": "子图检索中..."}
                    
                    # LLM 兜底阶段（出现可恢复错误或 no_results 且之前已走过图谱）
                    if (err_now or final_state.get("no_results")) and not _llm_fallback_seen and "llm" not in _stages_sent:
                        _llm_fallback_seen = True
                        _stages_sent.add("llm")
                        yield {"event": "status", "stage": "llm",
                               "message": "检索未找到答案，使用 AI 模型生成中..."}
                    
                    # 仅当有效答案出现时才更新 final_answer（跳过空字符串和默认值）
                    ans = final_state.get("answer", "")
                    if ans and ans != DEFAULT_ANSWER:
                        final_answer = ans
                    
                    # 累积 llm_model
                    model = final_state.get("llm_model", "")
                    if model:
                        _collected_llm_model = model
                    
                    # 更新 debug 信息（后出现的覆盖先出现的）
                    if "analysis_level" in final_state:
                        debug_info["analysis_level"] = final_state["analysis_level"]
                    if "route" in final_state:
                        debug_info["route"] = final_state["route"]
                    if "error" in final_state:
                        debug_info["error"] = final_state["error"]
                    if "no_results" in final_state:
                        debug_info["no_results"] = final_state["no_results"]
                    if "intent" in final_state:
                        debug_info["intents"] = final_state["intent"]
                    if "normalized_entities" in final_state:
                        normalized = final_state["normalized_entities"]
                        if isinstance(normalized, dict):
                            debug_info["entities"] = normalized.get("entity_dict", {})
                            debug_info["entities_normalized"] = normalized.get("entity_dict", {})
                    if "cypher" in final_state:
                        cypher_data = final_state["cypher"]
                        if isinstance(cypher_data, list):
                            queries = []
                            for group in cypher_data:
                                for q in group.get("queries", []):
                                    queries.append({
                                        "cypher": q.get("cypher", ""),
                                        "params": q.get("params", {})
                                    })
                            debug_info["cypher_queries"] = queries
                    if "raw_results" in final_state:
                        debug_info["result_count"] = sum(
                            len(g.get("answers", []))
                            for g in (final_state["raw_results"] or [])
                            if isinstance(g, dict)
                        )
                    if "graph_data" in final_state and final_state.get("graph_data"):
                        graph_data = final_state["graph_data"]
                    elif final_state:
                        graph_data = resolve_graph_data_from_state(final_state)
                    if "rag_entities" in final_state:
                        debug_info["entities_raw"] = final_state["rag_entities"]
                    if "subgraph" in final_state:
                        subgraph = final_state["subgraph"]
                        if isinstance(subgraph, dict):
                            debug_info["subgraph_stats"] = subgraph.get("stats", {})
                            nodes = subgraph.get("nodes", [])
                            edges = subgraph.get("edges", [])
                            graph_data["nodes"] = [{"id": n["name"], "label": n["label"]} for n in nodes]
                            graph_data["edges"] = [
                                {"source": e["source"], "target": e["target"], "label": e["relationship"]}
                                for e in edges
                            ]
                    if "context" in final_state:
                        context = final_state["context"]
                        if isinstance(context, dict):
                            debug_info["context_preview"] = context.get("context_preview", "")[:200]
                            debug_info["context_char_count"] = context.get("char_count", 0)
        
        # ==== 循环结束，统一输出唯一 done 事件 ====
        # 兜底：如果没有收到 on_chain_end，用 invoke 获取结果
        if not final_answer:
            result = app.invoke(initial_state, config=config)
            if isinstance(result, dict):
                final_answer = result.get("answer", DEFAULT_ANSWER)
                _collected_llm_model = result.get("llm_model", _collected_llm_model)
                graph_data = resolve_graph_data_from_state(result)
                debug_info["analysis_level"] = result.get("analysis_level")
                debug_info["route"] = result.get("route")
                debug_info["error"] = result.get("error")
                debug_info["no_results"] = result.get("no_results", False)
                debug_info["intents"] = result.get("intent", [])
                normalized = result.get("normalized_entities", {})
                if isinstance(normalized, dict):
                    debug_info["entities"] = normalized.get("entity_dict", {})
                    debug_info["entities_normalized"] = normalized.get("entity_dict", {})
                subgraph = result.get("subgraph", {})
                if isinstance(subgraph, dict):
                    debug_info["subgraph_stats"] = subgraph.get("stats", {})
                    nodes = subgraph.get("nodes", [])
                    edges = subgraph.get("edges", [])
                    graph_data["nodes"] = [{"id": n["name"], "label": n["label"]} for n in nodes]
                    graph_data["edges"] = [
                        {"source": e["source"], "target": e["target"], "label": e["relationship"]}
                        for e in edges
                    ]
        
        # 计算总耗时 + 模式 + yield 唯一 done
        debug_info["total_time_ms"] = round((time.time() - t0) * 1000, 1)
        route = debug_info.get("route", "")
        _KNOWN_MODES = {"template", "graphrag", "template_to_graphrag", "template_to_llm", "llm_fallback", "graphrag_to_llm", "template_to_graphrag_to_llm"}
        mode = route if route in _KNOWN_MODES else "template"
        
        yield {
            "event": "done",
            "answer": final_answer or DEFAULT_ANSWER,
            "debug": debug_info,
            "graph_data": graph_data,
            "mode": mode,
            "llm_model": _collected_llm_model,
            "session_id": config.get("configurable", {}).get("thread_id"),
        }
    
    except Exception as e:
        # 流式过程中发生异常，yield 错误事件
        error_msg = str(e)
        log.error(f"流式问答发生错误: {error_msg}")
        yield {"event": "error", "message": error_msg}
