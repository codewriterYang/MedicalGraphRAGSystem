#!/usr/bin/env python3
# coding: utf-8
"""
命令行交互模块。

包含命令行入口函数和交互式问答循环。
"""
import sys
import os
import argparse
import logging
import asyncio
from pathlib import Path

# 确保项目根目录在 sys.path 中
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.core.config import DEFAULT_ANSWER
from .graph_builder import create_app, build_workflow
from .stream import stream_qa
from .session import make_thread_config, DEFAULT_CLI_SESSION

# 全局日志
log = logging.getLogger("qa_engine")

# LangSmith 相关导入（可选依赖）
try:
    from langsmith import Client
    from langchain_core.tracers import LangChainTracer
    from langchain_core.callbacks import CallbackManager
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False


def setup_langsmith() -> None:
    """初始化 LangSmith 追踪（如果可用）。"""
    if not LANGSMITH_AVAILABLE:
        return
    
    tracing_enabled = os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    if not tracing_enabled:
        log.info("LangSmith 追踪未激活（设置 LANGCHAIN_TRACING_V2=true 启用）")
        return
    
    try:
        tracer = LangChainTracer()
        log.info("LangSmith 追踪已激活")
    except Exception as e:
        log.warning(f"初始化 LangSmith 追踪失败: {e}")


async def run_stream_demo(question: str):
    """运行流式问答演示。"""
    print(f"\n【流式问答演示】问题: {question}")
    print("-" * 60)
    
    async for event in stream_qa(question, config=make_thread_config(DEFAULT_CLI_SESSION)):
        event_type = event.get("event", "")
        
        if event_type == "delta":
            print(event.get("chunk", ""), end="", flush=True)
        elif event_type == "tool_start":
            print(f"\n[开始执行] {event.get('node', '')}", flush=True)
        elif event_type == "tool_end":
            node = event.get("node", "")
            duration = event.get("duration", 0)
            print(f"[执行完成] {node} ({duration:.2f}ms)", flush=True)
        elif event_type == "done":
            answer = event.get("answer", "")
            debug = event.get("debug", {})
            level_desc = {1: "Level 1 (全LLM)", 2: "Level 2 (LLM实体+关键词)", 3: "Level 3 (离线NER)"}.get(debug.get("analysis_level"), "未知")
            route_desc = {"template": "模板问答", "graphrag": "GraphRAG", "template_to_graphrag": "模板→GraphRAG", "llm_fallback": "LLM兜底", "graphrag_to_llm": "GraphRAG→LLM", "template_to_graphrag_to_llm": "模板→GraphRAG→LLM"}.get(debug.get("route"), debug.get("route", "unknown"))
            
            print(f"\n\n{'=' * 60}")
            print(f"分析级别: {level_desc}")
            print(f"路由路径: {route_desc}")
            print(f"完整答案: {answer}")
            if debug.get("error"):
                print(f"错误信息: {debug['error']}")
        elif event_type == "error":
            print(f"\n[错误] {event.get('message', '')}")


def render_graph_diagram(output_path: str = "workflow.png") -> None:
    """
    导出与 graph_builder 语义一致的工作流图（成功/失败 标签，非 True/False）。

    优先：手写 Mermaid → Kroki PNG；并始终生成 .mmd 与 .html 备选。
    """
    from pathlib import Path
    from .workflow_diagram import WORKFLOW_MERMAID

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    mmd_path = out.with_suffix(".mmd")
    mmd_path.write_text(WORKFLOW_MERMAID.strip() + "\n", encoding="utf-8")
    log.info("Mermaid 源码已写入: %s", mmd_path)

    html_path = out.with_suffix(".html")
    generate_workflow_html(str(html_path), mermaid=WORKFLOW_MERMAID.strip())

    png_ok = _try_kroki_png(WORKFLOW_MERMAID.strip(), out)
    if png_ok:
        log.info("工作流 PNG 已导出至: %s", out)
        return

    # 次选：LangGraph 自动图（边标签为 success/error 时已可读）
    try:
        workflow = build_workflow()
        app = workflow.compile()
        png_data = app.get_graph().draw_mermaid_png()
        with open(out, "wb") as f:
            f.write(png_data)
        log.info("工作流 PNG（LangGraph 导出）已写入: %s", out)
    except Exception as e:
        log.warning("PNG 生成失败，请打开 HTML 预览: %s | %s", html_path, e)


def _try_kroki_png(mermaid: str, out_path) -> bool:
    """通过 Kroki 服务将 Mermaid 转为 PNG（需网络）。"""
    import json
    from pathlib import Path
    from urllib import request

    try:
        body = json.dumps(
            {"diagram": mermaid, "diagram_type": "mermaid", "output_format": "png"}
        ).encode("utf-8")
        req = request.Request(
            "https://kroki.io/mermaid/png",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:
            Path(out_path).write_bytes(resp.read())
        return True
    except Exception as e:
        log.debug("Kroki PNG 不可用: %s", e)
        return False


def generate_workflow_html(
    output_path: str = "workflow.html",
    mermaid: str | None = None,
) -> None:
    """生成包含工作流图的 HTML 文件。"""
    from .workflow_diagram import WORKFLOW_MERMAID

    diagram = mermaid or WORKFLOW_MERMAID.strip()
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>医药知识图谱问答系统工作流</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
    </script>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; max-width: 1600px; margin: 0 auto; padding: 24px; background: #f1f5f9; }}
        .container {{ background: white; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.08); padding: 32px; }}
        h1 {{ text-align: center; color: #1e293b; font-size: 24px; }}
        p.note {{ text-align: center; color: #64748b; font-size: 14px; }}
        .mermaid-container {{ overflow-x: auto; padding: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>医药知识图谱智能问答 — LangGraph 工作流</h1>
        <p class="note">边标签：成功 success → 下一步；失败 error → 错误处理（与 qa_engine/graph_builder.py 一致）</p>
        <div class="mermaid-container">
            <pre class="mermaid">
{diagram}
            </pre>
        </div>
    </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    log.info("工作流 HTML 已导出至: %s", output_path)


def main():
    """命令行入口函数。"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="医药知识图谱智能问答系统")
    parser.add_argument("--stream", action="store_true", help="使用流式输出模式")
    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 70)
    print("  医药知识图谱智能问答系统（LangGraph 工作流 + GraphRAG）")
    print("  输入医疗相关问题进行问答，输入 quit 退出")
    print("  支持两条路径：")
    print("    - 模板问答：适用于简单查询（如'糖尿病有什么症状'）")
    print("    - GraphRAG：适用于复杂问题（如'糖尿病和高血压有什么关系'）")
    print("  支持三级降级策略：Level 1(全LLM) → Level 2(LLM实体) → Level 3(离线)")
    print("  当前模式: {'流式输出模式' if args.stream else '同步模式'}")
    print("=" * 70)

    # 初始化 LangSmith 追踪
    setup_langsmith()

    # 取消下行注释可导出 LangGraph 工作流 PNG（输出至 docs/assets/workflow.png）
    # 依赖：langgraph 图可视化；若 Mermaid API 不可用将生成 workflow.html
    # render_graph_diagram("docs/assets/workflow.png")

    if args.stream:
        # 流式模式
        while True:
            try:
                question = input("\n请输入问题: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break

            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                print("再见！")
                break

            # 运行流式问答
            asyncio.run(run_stream_demo(question))
    else:
        # 同步模式
        app = create_app()
        config = make_thread_config(DEFAULT_CLI_SESSION)
        
        while True:
            try:
                question = input("\n请输入问题: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break

            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                print("再见！")
                break

            # 执行工作流
            result = app.invoke({"question": question}, config=config)

            # 输出答案和降级等级
            answer = result.get("answer", DEFAULT_ANSWER)
            level = result.get("analysis_level", 0)
            route = result.get("route", "unknown")
            level_desc = {1: "Level 1 (全LLM)", 2: "Level 2 (LLM实体+关键词)", 3: "Level 3 (离线NER)"}.get(level, "未知")
            route_desc = {"template": "模板问答", "graphrag": "GraphRAG", "template_to_graphrag": "模板→GraphRAG", "llm_fallback": "LLM兜底", "graphrag_to_llm": "GraphRAG→LLM", "template_to_graphrag_to_llm": "模板→GraphRAG→LLM"}.get(route, route)
            
            print(f"\n分析级别: {level_desc}")
            print(f"路由路径: {route_desc}")
            print(f"回答: {answer}")


if __name__ == "__main__":
    main()
