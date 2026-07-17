#!/usr/bin/env python3
# coding: utf-8
"""
一键生成 LangGraph 工作流示意图。

用法（项目根目录）:
    python scripts/generate_diagrams.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.domain.qa_engine.cli import render_graph_diagram


def main() -> None:
    out_dir = ROOT / "docs" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "workflow.png"
    print(f"正在生成工作流图: {png_path}")
    render_graph_diagram(str(png_path))
    if png_path.exists():
        print(f"已生成 PNG: {png_path}")
    else:
        html_path = out_dir / "workflow.html"
        print(f"PNG 不可用，已生成 HTML 备选: {html_path}")


if __name__ == "__main__":
    main()
