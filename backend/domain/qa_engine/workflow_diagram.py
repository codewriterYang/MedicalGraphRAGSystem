#!/usr/bin/env python3
# coding: utf-8
"""
工作流示意图（文档用 Mermaid 源码）。

与 graph_builder.py 中条件边语义一致：
- success：无 error 且非 no_results，进入下一步
- error：进入 X. 错误处理
- graphrag / template：路由分支
- template_fallback：模板查询无结果 → 回退到 GraphRAG 路径

勿使用 LangGraph draw_mermaid_png() 直接导出 PNG（会显示 True/False 且与「成功/失败」直觉相反）。
"""
from __future__ import annotations

# 与项目 qa_engine/graph_builder.py 节点 ID 及分支一致
WORKFLOW_MERMAID = r"""
flowchart TD
    start([__start__]) --> analyze["1. 分析问题<br/>Analyze Question"]

    analyze -->|成功 success| route["2. 路由判断<br/>Route Question"]
    analyze -->|失败 error| error["X. 错误处理<br/>Error Handler<br/>(含LLM兜底)"]

    route -->|graphrag| g1["G1. RAG实体抽取<br/>RAG Entity Extraction"]
    route -->|template| t1["T1. 实体归一化<br/>Normalize Entities"]
    route -->|失败 error| error

    g1 -->|成功| g2["G2. RAG实体归一化"]
    g1 -->|失败| error
    g2 -->|成功| g3["G3. 子图检索"]
    g2 -->|失败| error
    g3 -->|成功| g4["G4. 上下文构建"]
    g3 -->|失败| error
    g4 -->|成功| g5["G5. RAG生成回答<br/>(写route)"]
    g4 -->|失败| error
    g5 -->|成功| end_ok([返回答案 __end__])
    g5 -->|失败| error

    t1 -->|成功/回退| t2["T2. 生成Cypher"]
    t1 -->|异常| error
    t2 -->|成功/回退| t3["T3. 执行查询<br/>template_no_result → G1"]
    t2 -->|异常| error
    t3 -->|成功| t4["T4. 格式化答案"]
    t3 -->|异常| error
    t3 -->|模板无结果<br/>回退GraphRAG| g1
    t4 -->|成功| end_ok
    t4 -->|异常| error

    error --> end_err([友好提示或<br/>LLM兜底回答 __end__])

    classDef ok fill:#ecfdf5,stroke:#10b981,color:#065f46
    classDef err fill:#fef2f2,stroke:#ef4444,color:#991b1b
    classDef route fill:#eff6ff,stroke:#3b82f6,color:#1e40af
    class analyze,route,g1,g2,g3,g4,g5,t1,t2,t3,t4 route
    class error err
    class end_ok,end_err ok
"""
