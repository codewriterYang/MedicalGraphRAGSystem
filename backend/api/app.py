#!/usr/bin/env python3
# coding: utf-8
"""
FastAPI 后端：提供问答 API、图谱邻居查询和健康检查。

启动: python -m backend.api.app
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# 项目根目录（用于包级导入）
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 导入统一问答引擎
from backend.core import cli as qa_engine_cli
from backend.domain.qa_engine.collect import collect_stream_result
from backend.domain.qa_engine.session import make_thread_config
from backend.api.qa_response import done_to_chat_response

from backend.api.models import (
    ChatRequest, ChatResponse,
    NeighborResponse, GraphData, GraphNode, GraphEdge,
    HealthResponse,
)

log = logging.getLogger("server")

# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
_bot = None


def _get_bot():
    """获取 KBQA ChatBot 单例（用于邻居查询和健康检查）。"""
    global _bot
    if _bot is None:
        raise RuntimeError("ChatBot 尚未初始化，请等待服务完全启动。")
    return _bot


# ---------------------------------------------------------------------------
# 会话 ID 与统一引擎调用
# ---------------------------------------------------------------------------
def _resolve_session_id(session_id: str | None) -> str:
    """未传 session_id 时生成 UUID，供前端后续复用。"""
    if session_id and str(session_id).strip():
        return str(session_id).strip()
    return str(uuid.uuid4())


def _run_qa(question: str, session_id: str | None = None) -> dict:
    """
    使用统一问答引擎执行问答。

    复用全局 MemorySaver 检查点，支持多轮对话。

    Args:
        question: 用户问题
        session_id: 会话ID（用于多轮对话检查点）

    Returns:
        final_state 字典，包含 answer, error, analysis_level, route 等字段
    """
    try:
        # 使用 create_app 创建带 MemorySaver 的 app（复用全局检查点）
        app_graph = qa_engine_cli.create_app()

        # 构建初始状态（仅传 question，其他字段由 checkpoint 恢复）
        initial_state = {"question": question}

        # 使用 make_thread_config 构建 config，保持同一会话内 thread_id 不变
        config = make_thread_config(session_id or "api-session")
        final_state = app_graph.invoke(initial_state, config=config)

        return final_state

    except Exception as e:
        log.error(f"问答引擎执行失败: {e}", exc_info=True)
        return {
            "answer": f"服务内部错误: {str(e)}",
            "error": str(e),
            "no_results": True,
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化必要组件，关闭时释放。"""
    global _bot
    from backend.domain.kbqa.chatbot import ChatBot

    cfg = app.state.bot_config
    
    # ChatBot 用于邻居查询和健康检查（问答功能由 qa_engine 统一处理）
    _bot = ChatBot(
        neo4j_uri=cfg["neo4j_uri"],
        neo4j_user=cfg["neo4j_user"],
        neo4j_password=cfg["neo4j_password"],
        llm_model=cfg["llm_model"],
        llm_base_url=cfg["llm_base_url"],
        answer_mode=cfg["answer_mode"],
        debug=True,
    )
    log.info("ChatBot 初始化完成（邻居查询 + 健康检查）")

    yield
    _bot = None
    log.info("所有组件已释放")


# ---------------------------------------------------------------------------
# FastAPI 实例
# ---------------------------------------------------------------------------
app = FastAPI(title="医药知识图谱问答 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """问答接口：通过 stream_qa 收集 done 事件，与流式端点数据一致（含 graph_data）。"""
    sid = _resolve_session_id(req.session_id)
    done = await collect_stream_result(req.question, session_id=sid)
    return done_to_chat_response(done, session_id=sid)


def _sse_event(event: str, data: dict) -> str:
    """格式化一个 SSE 事件。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _qa_stream_generator(question: str, session_id: str):
    """使用统一问答引擎生成流式事件（SSE格式）。"""
    config = make_thread_config(session_id)
    try:
        async for event in qa_engine_cli.stream_qa(question, config=config):
            event_type = event.get("event", "")
            
            if event_type == "delta":
                # LLM token 流
                yield _sse_event("delta", {"chunk": event.get("chunk", "")})
            elif event_type == "status":
                # 路由阶段状态（前端展示进度标签和提示）
                yield _sse_event("status", {
                    "stage": event.get("stage", ""),
                    "message": event.get("message", ""),
                })
            elif event_type == "done":
                # 工作流完成
                yield _sse_event("done", {
                    "answer": event.get("answer", ""),
                    "debug": event.get("debug", {}),
                    "graph_data": event.get("graph_data", {}),
                    "mode": event.get("mode", "template"),
                    "llm_model": event.get("llm_model", ""),
                    "session_id": event.get("session_id", session_id),
                })
            elif event_type == "error":
                # 错误事件
                yield _sse_event("error", {"message": event.get("message", "")})
            # 忽略 tool_start/tool_end 事件（用于调试）
    except Exception as e:
        log.error(f"问答引擎流式执行失败: {e}", exc_info=True)
        # 返回错误事件
        yield _sse_event("error", {"message": f"流式问答服务异常: {str(e)}"})


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """问答流式接口（SSE），使用统一问答引擎。"""
    sid = _resolve_session_id(req.session_id)
    return StreamingResponse(
        _qa_stream_generator(req.question, sid),
        media_type="text/event-stream"
    )


@app.get("/api/graph/neighbors/{name}", response_model=NeighborResponse)
async def graph_neighbors(name: str, limit: int = 50):
    """查询指定节点的所有邻居（用于前端图谱探索）。"""
    bot = _get_bot()
    cypher = (
        "MATCH (n)-[r]-(m) WHERE n.name = $name "
        "RETURN labels(n)[0] AS n_label, n.name AS n_name, "
        "type(r) AS r_type, labels(m)[0] AS m_label, m.name AS m_name "
        "LIMIT $limit"
    )
    try:
        rows = bot.graph_query.graph.run(cypher, name=name, limit=limit).data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    nodes_set: dict[str, str] = {name: "center"}
    edges: list[dict] = []
    for row in rows:
        n_name = row.get("n_name", "")
        m_name = row.get("m_name", "")
        n_label = row.get("n_label", "")
        m_label = row.get("m_label", "")
        r_type = row.get("r_type", "")
        if n_name:
            nodes_set.setdefault(n_name, n_label)
        if m_name:
            nodes_set.setdefault(m_name, m_label)
        if n_name and m_name:
            edges.append({"source": n_name, "target": m_name, "label": r_type})

    # 更新 center 节点的真实标签
    for row in rows:
        if row.get("n_name") == name:
            nodes_set[name] = row.get("n_label", "center")
            break

    graph_data = GraphData(
        nodes=[GraphNode(id=n, label=l) for n, l in nodes_set.items()],
        edges=[GraphEdge(**e) for e in edges],
    )
    return NeighborResponse(center=name, graph_data=graph_data)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """健康检查：Neo4j 和 Ollama 连通性。"""
    bot = _get_bot()

    neo4j_ok = False
    try:
        bot.graph_query.graph.run("RETURN 1").data()
        neo4j_ok = True
    except Exception:
        pass

    ollama_ok = bot.llm_engine.available
    
    # 检查 qa_engine 是否可用
    qa_engine_ok = False
    try:
        # 尝试导入并构建工作流来验证
        from backend.domain.qa_engine import build_workflow
        app_graph = build_workflow().compile()
        qa_engine_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if (neo4j_ok and ollama_ok) else "degraded",
        neo4j=neo4j_ok,
        ollama=ollama_ok,
        graphrag=qa_engine_ok,
    )


# ---------------------------------------------------------------------------
# 静态文件（生产模式：前端构建产物）
# ---------------------------------------------------------------------------
_web_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _web_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_web_dist), html=True), name="static")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="医药知识图谱问答 API 服务")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--neo4j-uri", default=None)
    parser.add_argument("--neo4j-user", default=None)
    parser.add_argument("--neo4j-password", "--password", default=None)
    parser.add_argument("--llm-provider", default=None, help="LLM 提供商: ollama/openai/anthropic")
    parser.add_argument("--llm-model", default=None, help="LLM 模型名称")
    parser.add_argument("--llm-base-url", default=None, help="LLM API 地址")
    parser.add_argument("--llm-api-key", default=None, help="LLM API Key (商业 API)")
    parser.add_argument("--answer-mode", default="template", choices=["template", "llm"])
    # Ollama 兼容参数
    parser.add_argument("--ollama-model", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--ollama-url", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    # 导入配置模块获取默认值
    from backend.core import config as settings

    # 如果指定了 provider，覆盖环境变量
    if args.llm_provider:
        os.environ["LLM_PROVIDER"] = args.llm_provider
    if args.llm_api_key:
        os.environ["OPENAI_API_KEY"] = args.llm_api_key
        os.environ["ANTHROPIC_API_KEY"] = args.llm_api_key

    # 参数优先级：CLI 参数 > Ollama 兼容参数 > 配置文件默认值
    llm_model = args.llm_model or args.ollama_model or settings.LLM_MODEL
    llm_base_url = args.llm_base_url or args.ollama_url or settings.LLM_BASE_URL

    app.state.bot_config = {
        "neo4j_uri": args.neo4j_uri or settings.NEO4J_URI,
        "neo4j_user": args.neo4j_user or settings.NEO4J_USER,
        "neo4j_password": args.neo4j_password or settings.NEO4J_PASSWORD,
        "llm_model": llm_model,
        "llm_base_url": llm_base_url,
        "answer_mode": args.answer_mode,
    }

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
