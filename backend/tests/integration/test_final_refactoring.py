#!/usr/bin/env python3
# coding: utf-8
"""
测试全局收尾重构的集成测试。

验证内容：
1. backend/api/app.py 收尾（问答引擎集成、日志优化）
2. qa_engine 日志统一
3. stream_qa 数据完整性（done 事件包含 answer、debug、graph_data、mode）
4. 前端 UnifiedChatPanel 组件存在性
5. 代码结构完整性
"""
from __future__ import annotations

import sys
import os
import asyncio
import logging
from pathlib import Path

# 获取项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 改变工作目录到项目根目录
os.chdir(project_root)


def test_server_app_cleanup():
    """测试 backend/api/app.py 收尾"""
    print("\n" + "=" * 70)
    print("测试1: backend/api/app.py 收尾")
    print("=" * 70)
    
    try:
        # 读取 app.py 内容
        app_file = project_root / "server" / "app.py"
        content = app_file.read_text(encoding="utf-8")
        
        # 检查是否移除了 _graphrag_bot
        if "_graphrag_bot" not in content:
            print("  [OK] 已移除 _graphrag_bot 全局变量")
        else:
            print("  [FAIL] 仍存在 _graphrag_bot")
            return False
        
        # 检查是否移除了 GraphRAGBot 初始化
        if "GraphRAGBot" not in content or "from graphrag.graphrag_bot import GraphRAGBot" not in content:
            print("  [OK] 已移除 GraphRAGBot 初始化代码")
        else:
            print("  [FAIL] 仍存在 GraphRAGBot 初始化")
            return False
        
        # 检查日志信息是否更新
        if "用于邻居查询和健康检查，问答已由 qa_engine 接管" in content:
            print("  [OK] 日志信息已更新")
        else:
            print("  [FAIL] 日志信息未更新")
            return False
        
        # 检查健康检查是否改为检查 qa_engine
        if "qa_engine_ok" in content and "build_workflow" in content:
            print("  [OK] 健康检查已改为检查 qa_engine")
        else:
            print("  [FAIL] 健康检查未更新")
            return False
        
        # 检查 done 事件是否包含 graph_data 和 mode
        if "graph_data" in content and "mode" in content:
            print("  [OK] 流式事件已包含 graph_data 和 mode")
        else:
            print("  [FAIL] 流式事件缺少 graph_data 或 mode")
            return False
        
        return True
    except Exception as e:
        print(f"  [FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qa_engine_log_unification():
    """测试 qa_engine 日志统一"""
    print("\n" + "=" * 70)
    print("测试2: qa_engine 日志统一")
    print("=" * 70)
    
    try:
        # 重置日志级别
        logging.getLogger("qa").setLevel(logging.INFO)
        logging.getLogger("graphrag").setLevel(logging.INFO)
        
        # 导入 qa_engine，触发日志抑制
        from backend.domain import qa_engine
        
        # 检查日志级别是否被提升
        qa_logger = logging.getLogger("qa")
        graphrag_logger = logging.getLogger("graphrag")
        
        if qa_logger.level >= logging.WARNING:
            print("  [OK] 'qa' logger 级别已提升为 WARNING")
        else:
            print("  [FAIL] 'qa' logger 级别未提升")
            return False
        
        if graphrag_logger.level >= logging.WARNING:
            print("  [OK] 'graphrag' logger 级别已提升为 WARNING")
        else:
            print("  [FAIL] 'graphrag' logger 级别未提升")
            return False
        
        # 验证 qa_engine logger 级别正常
        qa_engine_logger = logging.getLogger("qa_engine")
        if qa_engine_logger.level == logging.NOTSET:
            print("  [OK] 'qa_engine' logger 级别正常（NOTSET）")
        else:
            print(f"  [INFO] 'qa_engine' logger 级别: {qa_engine_logger.level}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stream_qa_data_completeness():
    """测试 stream_qa done 事件数据完整性"""
    print("\n" + "=" * 70)
    print("测试3: stream_qa done 事件数据完整性")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine import stream_qa
        
        done_event = None
        async for event in stream_qa("糖尿病有什么症状"):
            if event.get("event") == "done":
                done_event = event
                break
        
        if done_event is None:
            print("  [FAIL] 未收到 done 事件")
            return False
        
        # 检查必需字段
        required_fields = ["answer", "debug", "graph_data", "mode"]
        missing_fields = []
        
        for field in required_fields:
            if field not in done_event:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"  [FAIL] done 事件缺少字段: {', '.join(missing_fields)}")
            return False
        else:
            print("  [OK] done 事件包含所有必需字段")
        
        # 检查 debug 结构
        debug = done_event.get("debug", {})
        if isinstance(debug, dict):
            print("  [OK] debug 字段为字典类型")
            
            # 检查基础问答字段
            if "analysis_level" in debug or "intents" in debug:
                print("  [OK] debug 包含基础问答字段")
            # 检查 GraphRAG 字段
            if "entities_raw" in debug or "subgraph_stats" in debug:
                print("  [OK] debug 包含 GraphRAG 字段")
        else:
            print("  [FAIL] debug 字段类型不正确")
            return False
        
        # 检查 graph_data 结构
        graph_data = done_event.get("graph_data", {})
        if isinstance(graph_data, dict) and "nodes" in graph_data and "edges" in graph_data:
            print("  [OK] graph_data 结构正确")
        else:
            print("  [FAIL] graph_data 结构不正确")
            return False
        
        # 检查 mode 值
        mode = done_event.get("mode")
        if mode in ["graphrag", "template"]:
            print(f"  [OK] mode 值正确: {mode}")
        else:
            print(f"  [WARN] mode 值不标准: {mode}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_frontend_unified_panel():
    """测试前端 UnifiedChatPanel 组件"""
    print("\n" + "=" * 70)
    print("测试4: 前端 UnifiedChatPanel 组件")
    print("=" * 70)
    
    try:
        web_dir = project_root / "web" / "src" / "components"
        
        # 检查 UnifiedChatPanel.tsx 是否存在
        unified_panel = web_dir / "UnifiedChatPanel.tsx"
        if unified_panel.exists():
            print("  [OK] UnifiedChatPanel.tsx 存在")
        else:
            print("  [FAIL] UnifiedChatPanel.tsx 不存在")
            return False
        
        # 检查内容
        content = unified_panel.read_text(encoding="utf-8")
        
        # 检查是否导入了两种 API
        if "streamChat" in content and "streamGraphRAGChat" in content:
            print("  [OK] 已导入两种流式 API")
        else:
            print("  [FAIL] 未导入两种流式 API")
            return False
        
        # 检查是否有 mode prop
        if "mode: 'basic' | 'graphrag'" in content or 'mode: "basic" | "graphrag"' in content:
            print("  [OK] 包含 mode prop")
        else:
            print("  [FAIL] 缺少 mode prop")
            return False
        
        # 检查 App.tsx 是否使用统一面板
        app_file = project_root / "frontend" / "src" / "App.tsx"
        if app_file.exists():
            app_content = app_file.read_text(encoding="utf-8")
            if "UnifiedChatPanel" in app_content:
                print("  [OK] App.tsx 已使用 UnifiedChatPanel")
            else:
                print("  [FAIL] App.tsx 未使用 UnifiedChatPanel")
                return False
        else:
            print("  [WARN] App.tsx 不存在")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_old_code_markers():
    """测试旧代码标记注释"""
    print("\n" + "=" * 70)
    print("测试5: 旧代码标记注释")
    print("=" * 70)
    
    try:
        markers = []
        
        # KBQA/chatbot.py
        chatbot_file = project_root / "KBQA" / "chatbot.py"
        if chatbot_file.exists():
            content = chatbot_file.read_text(encoding="utf-8")
            if "[保留] ChatBot 用于 server 的邻居查询" in content:
                markers.append(("KBQA/chatbot.py", True))
                print("  [OK] KBQA/chatbot.py 已添加保留标记")
            else:
                markers.append(("KBQA/chatbot.py", False))
                print("  [FAIL] KBQA/chatbot.py 缺少保留标记")
        
        # graphrag/graphrag_bot.py
        graphrag_bot_file = project_root / "graphrag" / "graphrag_bot.py"
        if graphrag_bot_file.exists():
            content = graphrag_bot_file.read_text(encoding="utf-8")
            if "[保留] GraphRAGBot 内部模块仍被 qa_engine 复用" in content:
                markers.append(("graphrag/graphrag_bot.py", True))
                print("  [OK] graphrag/graphrag_bot.py 已添加保留标记")
            else:
                markers.append(("graphrag/graphrag_bot.py", False))
                print("  [FAIL] graphrag/graphrag_bot.py 缺少保留标记")
        
        # backend/core/cli.py
        cli_file = project_root / "backend" / "core" / "cli.py"
        if cli_file.exists():
            content = cli_file.read_text(encoding="utf-8")
            if "CLI 入口模块" in content:
                markers.append(("backend/core/cli.py", True))
                print("  [OK] backend/core/cli.py 入口标记正确")
            else:
                markers.append(("backend/core/cli.py", False))
                print("  [FAIL] backend/core/cli.py 缺少入口标记")

        # backend/api/app.py
        app_file = project_root / "backend" / "api" / "app.py"
        if app_file.exists():
            content = app_file.read_text(encoding="utf-8")
            if "邻居查询" in content:
                markers.append(("backend/api/app.py", True))
                print("  [OK] backend/api/app.py 包含邻居查询功能")
            else:
                markers.append(("backend/api/app.py", False))
                print("  [FAIL] backend/api/app.py 缺少邻居查询功能")
        
        return all(status for _, status in markers)
    except Exception as e:
        print(f"  [FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_state_simplification():
    """测试 App.tsx 状态简化"""
    print("\n" + "=" * 70)
    print("测试6: App.tsx 状态简化")
    print("=" * 70)
    
    try:
        app_file = project_root / "frontend" / "src" / "App.tsx"
        if not app_file.exists():
            print("  [WARN] App.tsx 不存在")
            return True
        
        content = app_file.read_text(encoding="utf-8")
        
        # 检查是否移除了旧的状态变量
        if "basicDebug" not in content and "ragDebug" not in content:
            print("  [OK] 已移除 basicDebug/ragDebug 状态")
        else:
            print("  [FAIL] 仍存在 basicDebug/ragDebug 状态")
            return False
        
        if "basicGraph" not in content and "ragGraph" not in content:
            print("  [OK] 已移除 basicGraph/ragGraph 状态")
        else:
            print("  [FAIL] 仍存在 basicGraph/ragGraph 状态")
            return False
        
        # 检查是否使用统一状态
        if "debug" in content and "graphData" in content:
            print("  [OK] 已使用统一的 debug/graphData 状态")
        else:
            print("  [FAIL] 未使用统一状态")
            return False
        
        # 检查是否移除了旧组件导入
        if "ChatPanel" not in content and "GraphRAGChatPanel" not in content:
            print("  [OK] 已移除旧组件导入")
        else:
            print("  [WARN] 仍存在旧组件导入（可能是未使用的导入）")
        
        return True
    except Exception as e:
        print(f"  [FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_async_tests():
    """运行所有异步测试"""
    tests = [
        ("stream_qa 数据完整性", test_stream_qa_data_completeness),
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
    print("       全局收尾重构集成测试")
    print("=" * 70 + "\n")
    
    try:
        results = []
        
        # 同步测试
        results.append(("backend/api/app.py 收尾", test_server_app_cleanup()))
        results.append(("qa_engine 日志统一", test_qa_engine_log_unification()))
        results.append(("前端 UnifiedChatPanel", test_frontend_unified_panel()))
        results.append(("旧代码标记注释", test_old_code_markers()))
        results.append(("App.tsx 状态简化", test_app_state_simplification()))
        
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
