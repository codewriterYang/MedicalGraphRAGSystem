#!/usr/bin/env python3
# coding: utf-8
"""
qa_engine: 统一问答引擎模块。

包含完整的问答工作流实现，支持：
- 三级降级语义分析
- 条件路由（模板问答 / GraphRAG）
- 流式输出支持
- 错误处理和日志统一

导出接口：
- build_workflow: 构建工作流图
- build_graph: 向后兼容接口
- create_app: 创建带检查点的工作流实例
- stream_qa: 异步流式问答函数
- QAState: 工作流状态类型
"""
import logging

# 设置 qa_engine 命名空间的日志级别
log = logging.getLogger("qa_engine")


def _suppress_old_loggers():
    """
    临时提升旧模块的日志级别，避免启动时产生过多 INFO 日志。
    
    旧模块（KBQA、graphrag）有自己的 logger（名为 'qa'、'graphrag'），
    在导入这些模块前提升其日志级别为 WARNING，只保留 qa_engine 和 server 的日志。
    """
    logging.getLogger("qa").setLevel(logging.WARNING)
    logging.getLogger("graphrag").setLevel(logging.WARNING)


# 在模块导入时执行一次
_suppress_old_loggers()


# 导出核心接口
from .graph_builder import build_workflow, create_app, build_graph
from .stream import stream_qa, get_or_create_app
from .state import QAState

__all__ = [
    "build_workflow",
    "build_graph",
    "create_app",
    "stream_qa",
    "QAState",
]
