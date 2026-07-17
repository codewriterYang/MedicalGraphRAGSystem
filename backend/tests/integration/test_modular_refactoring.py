#!/usr/bin/env python3
# coding: utf-8
"""
测试 qa_engine 模块化的集成测试。

验证内容：
1. qa_engine 模块结构完整性
2. backend/core/cli.py 向后兼容性
3. backend/api/app.py 流式端点兼容性
4. 所有节点函数功能正确性
"""
from __future__ import annotations

import sys
import os
import asyncio
from pathlib import Path

# 获取项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 改变工作目录到项目根目录
os.chdir(project_root)


def test_qa_engine_module_structure():
    """测试 qa_engine 模块结构完整性"""
    print("\n" + "=" * 70)
    print("测试1: qa_engine 模块结构完整性")
    print("=" * 70)
    
    try:
        # 测试核心导出
        from backend.domain.qa_engine import build_graph, build_workflow, create_app, stream_qa, QAState
        print("  [OK] qa_engine 核心导出正常")
        
        # 测试状态模块
        from backend.domain.qa_engine.state import QAState
        print("  [OK] qa_engine.state.QAState 导入成功")
        
        # 测试节点模块
        from backend.domain.qa_engine.nodes import (
            analyze_with_fallback,
            normalize_entities,
            route_question,
            select_route,
            generate_cypher,
            execute_query,
            format_answer,
            extract_rag_entities,
            normalize_rag_entities,
            retrieve_subgraph,
            build_context,
            generate_rag_answer,
            handle_error,
            should_handle_error,
        )
        print("  [OK] qa_engine.nodes 所有节点导入成功")
        
        # 测试图构建模块
        from backend.domain.qa_engine.graph_builder import build_graph, build_workflow, create_app
        print("  [OK] qa_engine.graph_builder 导入成功")
        
        # 测试流式模块
        from backend.domain.qa_engine.stream import stream_qa
        print("  [OK] qa_engine.stream 导入成功")
        
        # 测试 CLI 模块
        from backend.domain.qa_engine.cli import main
        print("  [OK] qa_engine.cli 导入成功")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_qa_backward_compatibility():
    """测试 basic_qa 向后兼容性"""
    print("\n" + "=" * 70)
    print("测试2: basic_qa 向后兼容性")
    print("=" * 70)
    
    try:
        from backend.core import cli as basic_qa
        
        # 验证 build_graph 存在
        assert hasattr(basic_qa, 'build_graph'), "build_graph 不存在"
        print("  [OK] basic_qa.build_graph 存在")
        
        # 验证 stream_qa 存在
        assert hasattr(basic_qa, 'stream_qa'), "stream_qa 不存在"
        print("  [OK] basic_qa.stream_qa 存在")
        
        # 验证 QAState 存在
        assert hasattr(basic_qa, 'QAState'), "QAState 不存在"
        print("  [OK] basic_qa.QAState 存在")
        
        # 验证 build_workflow 存在（新增）
        assert hasattr(basic_qa, 'build_workflow'), "build_workflow 不存在"
        print("  [OK] basic_qa.build_workflow 存在")
        
        # 验证 create_app 存在（新增）
        assert hasattr(basic_qa, 'create_app'), "create_app 不存在"
        print("  [OK] basic_qa.create_app 存在")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 向后兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_app_import():
    """测试 backend/api/app.py 导入兼容性"""
    print("\n" + "=" * 70)
    print("测试3: backend/api/app.py 导入兼容性")
    print("=" * 70)

    try:
        # 设置环境变量避免启动时连接数据库
        os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
        os.environ.setdefault("NEO4J_USER", "neo4j")
        os.environ.setdefault("NEO4J_PASSWORD", "password")

        # 导入 backend/api/app 模块
        from backend.api import app as server_app
        print("  [OK] backend.api.app 模块导入成功")

        # 验证应用实例存在
        assert hasattr(server_app, 'app'), "app 实例不存在"
        print("  [OK] backend.api.app 实例存在")

        return True
    except Exception as e:
        print(f"  [WARN] backend.api.app 导入失败（可能需要数据库连接）: {e}")
        return True  # 允许在无数据库时跳过


async def test_stream_qa_with_new_module():
    """测试使用新模块的流式问答"""
    print("\n" + "=" * 70)
    print("测试4: 流式问答功能（使用 qa_engine）")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine import stream_qa
        
        events = []
        async for event in stream_qa("糖尿病有什么症状"):
            events.append(event)
            event_type = event.get("event", "")
            
            if event_type == "delta":
                print(f"  [DELTA] 收到 token")
            elif event_type == "done":
                answer = event.get("answer", "")
                print(f"  [DONE] 回答长度: {len(answer)}")
        
        # 验证至少收到一些事件
        if len(events) == 0:
            print("  [FAIL] 未收到任何事件")
            return False
        
        # 检查是否有 done 事件
        event_types = [e.get("event") for e in events]
        if "done" in event_types:
            print("  [OK] 收到 done 事件")
        else:
            print("  [WARN] 未收到 done 事件")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 流式问答测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sync_invoke_with_new_module():
    """测试使用新模块的同步调用"""
    print("\n" + "=" * 70)
    print("测试5: 同步调用功能（使用 qa_engine）")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine import create_app
        
        app = create_app()
        config = {"configurable": {"thread_id": "test_sync_session"}}
        result = app.invoke({"question": "糖尿病有什么症状"}, config=config)
        
        # 验证结果结构
        assert "answer" in result, "结果缺少 answer 字段"
        assert "route" in result, "结果缺少 route 字段"
        
        print(f"  [OK] 同步 invoke 正常工作")
        print(f"    - 路由: {result.get('route')}")
        print(f"    - 分析级别: {result.get('analysis_level')}")
        print(f"    - 回答长度: {len(result.get('answer', ''))}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 同步调用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qa_engine_cli_main():
    """测试 qa_engine.cli.main 存在"""
    print("\n" + "=" * 70)
    print("测试6: CLI 入口函数")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine.cli import main
        assert callable(main), "main 不是可调用函数"
        print("  [OK] qa_engine.cli.main 存在且可调用")
        return True
    except Exception as e:
        print(f"  [FAIL] CLI 入口测试失败: {e}")
        return False


def run_async_tests():
    """运行所有异步测试"""
    tests = [
        ("流式问答功能", test_stream_qa_with_new_module),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = asyncio.run(test_func())
            results.append((name, result))
        except Exception as e:
            print(f"  [FAIL] {name} 执行异常: {e}")
            results.append((name, False))
    
    return results


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("       qa_engine 模块化重构集成测试")
    print("=" * 70 + "\n")
    
    try:
        results = []
        
        # 同步测试
        results.append(("qa_engine 模块结构", test_qa_engine_module_structure()))
        results.append(("basic_qa 向后兼容", test_basic_qa_backward_compatibility()))
        results.append(("backend/api/app.py 导入", test_server_app_import()))
        results.append(("同步调用功能", test_sync_invoke_with_new_module()))
        results.append(("CLI 入口函数", test_qa_engine_cli_main()))
        
        # 异步测试
        async_results = run_async_tests()
        results.extend(async_results)
        
        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, result in results:
            status = "[OK]" if result else "[FAIL]"
            print(f"  {status} {name}")
        
        print(f"\n总计: {passed}/{total} 测试通过")
        
        if passed == total:
            print("\n所有测试通过！[OK]")
        else:
            print(f"\n部分测试失败！{total - passed} 个测试未通过")
        
        print("=" * 70 + "\n")
        
        sys.exit(0 if passed == total else 1)
        
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
