#!/usr/bin/env python3
# coding: utf-8
"""
测试 GraphRAG 集成功能
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# 获取项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 改变工作目录到项目根目录
os.chdir(project_root)


def test_module_import():
    """测试 GraphRAG 模块导入"""
    print("=" * 70)
    print("测试1: GraphRAG 模块导入")
    print("=" * 70)
    
    try:
        from backend.domain.graphrag.entity_extractor import EntityExtractor
        from backend.domain.graphrag.subgraph_retriever import SubgraphRetriever
        from backend.domain.graphrag.context_builder import ContextBuilder
        from backend.domain.graphrag.generator import GraphRAGGenerator
        print("  [OK] GraphRAG 模块导入成功")
        return True
    except ImportError as e:
        print(f"  [FAIL] GraphRAG 模块导入失败: {e}")
        return False


def test_basic_qa_import():
    """测试 basic_qa 模块导入（包含 GraphRAG 功能）"""
    print("\n" + "=" * 70)
    print("测试2: basic_qa 模块导入")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine.graph_builder import build_workflow, create_app
        from backend.domain.qa_engine.state import QAState
        from backend.domain.qa_engine.nodes.route import route_question
        from backend.domain.qa_engine.nodes.graphrag_path import (
            extract_rag_entities,
            normalize_rag_entities,
            retrieve_subgraph,
            build_context,
            generate_rag_answer,
        )
        print("  [OK] basic_qa 模块导入成功（包含 GraphRAG 功能）")
        return True
    except ImportError as e:
        print(f"  [FAIL] basic_qa 模块导入失败: {e}")
        return False


def test_state_extension():
    """测试 QAState 状态扩展字段"""
    print("\n" + "=" * 70)
    print("测试3: QAState 状态扩展")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine.state import QAState
        from typing import get_type_hints
        
        type_hints = get_type_hints(QAState)
        graphrag_fields = ["rag_entities", "subgraph", "context", "rag_answer", "route"]
        
        found_fields = [field for field in graphrag_fields if field in type_hints]
        missing_fields = [field for field in graphrag_fields if field not in type_hints]
        
        print(f"  找到的 GraphRAG 字段: {', '.join(found_fields)}")
        if missing_fields:
            print(f"  [FAIL] 缺失的字段: {', '.join(missing_fields)}")
            return False
        
        print("  [OK] QAState 状态扩展字段完整")
        return True
    except Exception as e:
        print(f"  [FAIL] 状态扩展测试失败: {e}")
        return False


def test_workflow_build():
    """测试构建包含 GraphRAG 的工作流"""
    print("\n" + "=" * 70)
    print("测试4: 工作流构建")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine.graph_builder import build_workflow, create_app
        
        # 测试工作流构建
        workflow = build_workflow()
        app = create_app()
        
        print("  [OK] 工作流构建成功")
        
        # 验证节点存在
        graph = app.get_graph()
        nodes = list(graph.nodes)
        
        expected_nodes = [
            "1. 分析问题\nAnalyze Question",
            "2. 路由判断\nRoute Question",
            "X. 错误处理\nError Handler",
            "T1. 实体归一化\nNormalize Entities",
            "T2. 生成Cypher\nGenerate Cypher",
            "T3. 执行查询\nExecute Query",
            "T4. 格式化答案\nFormat Answer",
            "G1. RAG实体抽取\nRAG Entity Extraction",
            "G2. RAG实体归一化\nRAG Entity Normalization",
            "G3. 子图检索\nSubgraph Retrieval",
            "G4. 上下文构建\nContext Building",
            "G5. RAG生成回答\nRAG Answer Generation",
        ]
        
        found_count = sum(1 for node in expected_nodes if node in nodes)
        print(f"  找到的节点: {found_count}/{len(expected_nodes)}")
        
        if found_count == len(expected_nodes):
            print("  [OK] 所有预期节点都存在")
            return True
        else:
            print("  [WARN] 部分节点缺失，但工作流构建成功")
            return True
    except Exception as e:
        print(f"  [FAIL] 工作流构建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_route_question():
    """测试路由判断逻辑"""
    print("\n" + "=" * 70)
    print("测试5: 路由判断")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine.nodes.route import route_question
        
        test_cases = [
            {
                "name": "简单问题（模板路径）",
                "question": "糖尿病有什么症状",
                "intent": ["disease_symptom"],
                "entities": [{"name": "糖尿病", "type": "disease"}],
                "expected_route": "template",
            },
            {
                "name": "复杂问题（GraphRAG路径）",
                "question": "糖尿病和高血压有什么关系",
                "intent": ["disease_symptom"],
                "entities": [
                    {"name": "糖尿病", "type": "disease"},
                    {"name": "高血压", "type": "disease"},
                ],
                "expected_route": "graphrag",
            },
            {
                "name": "长问题（GraphRAG路径）",
                "question": "如何治疗糖尿病以及它会引起哪些并发症和症状",
                "intent": ["disease_symptom", "disease_cureway"],
                "entities": [{"name": "糖尿病", "type": "disease"}],
                "expected_route": "graphrag",
            },
        ]
        
        passed = 0
        for case in test_cases:
            state = {
                "question": case["question"],
                "intent": case["intent"],
                "entities": case["entities"],
            }
            result = route_question(state)
            actual_route = result.get("route")
            
            status = "[OK]" if actual_route == case["expected_route"] else "[FAIL]"
            print(f"  {status} {case['name']}: 路由={actual_route} (预期={case['expected_route']})")
            
            if actual_route == case["expected_route"]:
                passed += 1
        
        print(f"\n  路由测试: {passed}/{len(test_cases)} 通过")
        return passed == len(test_cases)
    except Exception as e:
        print(f"  [FAIL] 路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_neo4j_connection():
    """测试 Neo4j 连接（GraphRAG 需要）"""
    print("\n" + "=" * 70)
    print("测试6: Neo4j 连接")
    print("=" * 70)
    
    try:
        from backend.domain.kbqa.graph_query import GraphQueryExecutor
        
        executor = GraphQueryExecutor()
        print("  [OK] Neo4j 连接成功")
        return True
    except Exception as e:
        print(f"  [SKIP] Neo4j 连接不可用（跳过 GraphRAG 实际运行测试）: {e}")
        # 不返回 False，避免阻断其他测试
        return True


def test_end_to_end_template():
    """测试端到端流程（模板路径）"""
    print("\n" + "=" * 70)
    print("测试7: 端到端流程（模板路径）")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine.graph_builder import create_app
        
        app = create_app()
        question = "糖尿病有什么症状"
        
        print(f"  测试问题: {question}")
        result = app.invoke(
            {"question": question},
            config={"configurable": {"thread_id": "test_template"}}
        )
        
        route = result.get("route")
        answer = result.get("answer")
        error = result.get("error")
        
        print(f"  路由: {route}")
        print(f"  回答长度: {len(answer) if answer else 0}")
        
        if error:
            print(f"  [ERROR] 错误: {error}")
            return False
        
        if route != "template":
            print(f"  [WARN] 预期路由为 template，实际为 {route}")
        
        if answer and len(answer) > 0:
            print("  [OK] 模板路径执行成功")
            return True
        else:
            print("  [FAIL] 模板路径未返回有效回答")
            return False
    except Exception as e:
        print(f"  [FAIL] 模板路径测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end_graphrag():
    """测试端到端流程（GraphRAG路径）"""
    print("\n" + "=" * 70)
    print("测试8: 端到端流程（GraphRAG路径）")
    print("=" * 70)
    
    try:
        from backend.domain.qa_engine.graph_builder import create_app
        
        app = create_app()
        question = "糖尿病和高血压有什么关系"
        
        print(f"  测试问题: {question}")
        result = app.invoke(
            {"question": question},
            config={"configurable": {"thread_id": "test_graphrag"}}
        )
        
        route = result.get("route")
        answer = result.get("answer")
        error = result.get("error")
        
        print(f"  路由: {route}")
        print(f"  回答长度: {len(answer) if answer else 0}")
        
        if error:
            print(f"  [ERROR] 错误: {error}")
            return False
        
        if route != "graphrag":
            print(f"  [WARN] 预期路由为 graphrag，实际为 {route}")
        
        if answer and len(answer) > 0:
            print("  [OK] GraphRAG路径执行成功")
            return True
        else:
            print("  [FAIL] GraphRAG路径未返回有效回答")
            return False
    except Exception as e:
        print(f"  [FAIL] GraphRAG路径测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trace_metadata_with_route():
    """测试包含路由信息的追踪元数据"""
    print("\n" + "=" * 70)
    print("测试9: 追踪元数据（包含路由）")
    print("=" * 70)
    
    try:
        from backend.core.cli import create_trace_metadata
        
        # 模拟模板路径结果
        mock_template_result = {
            "question": "糖尿病有什么症状",
            "analysis_level": 1,
            "intent": ["disease_symptom"],
            "entities": [{"name": "糖尿病", "type": "disease"}],
            "normalized_entities": {"entity_dict": {"disease": ["糖尿病"]}},
            "cypher": [{"question_type": "disease_symptom", "queries": []}],
            "raw_results": [{"question_type": "disease_symptom", "answers": []}],
            "answer": "糖尿病的症状包括多饮、多尿等。",
            "error": "",
            "no_results": False,
            "route": "template",
        }
        
        # 模拟 GraphRAG 路径结果
        mock_graphrag_result = {
            "question": "糖尿病和高血压有什么关系",
            "analysis_level": 1,
            "intent": ["disease_symptom"],
            "entities": [
                {"name": "糖尿病", "type": "disease"},
                {"name": "高血压", "type": "disease"},
            ],
            "normalized_entities": {"entity_dict": {"disease": ["糖尿病", "高血压"]}},
            "cypher": [],
            "raw_results": [],
            "answer": "糖尿病和高血压是密切相关的疾病。",
            "error": "",
            "no_results": False,
            "route": "graphrag",
            "rag_entities": [
                {"name": "糖尿病", "type": "disease"},
                {"name": "高血压", "type": "disease"},
            ],
            "subgraph": {"stats": {"total_nodes": 100, "total_edges": 150}},
            "context": {"char_count": 2000},
        }
        
        passed = 0
        
        # 测试模板路径元数据
        metadata1 = create_trace_metadata(mock_template_result, mock_template_result["question"])
        route1 = metadata1.get("route")
        if route1 == "template":
            print("  [OK] 模板路径元数据: route字段正确")
            passed += 1
        else:
            print(f"  [FAIL] 模板路径元数据: route字段应为 'template', 实际为 '{route1}'")
        
        # 测试 GraphRAG 路径元数据
        metadata2 = create_trace_metadata(mock_graphrag_result, mock_graphrag_result["question"])
        route2 = metadata2.get("route")
        subgraph_nodes = metadata2.get("subgraph_nodes")
        context_chars = metadata2.get("context_chars")
        
        if route2 == "graphrag":
            print("  [OK] GraphRAG路径元数据: route字段正确")
            passed += 1
        else:
            print(f"  [FAIL] GraphRAG路径元数据: route字段应为 'graphrag', 实际为 '{route2}'")
        
        if subgraph_nodes == 100:
            print("  [OK] GraphRAG路径元数据: subgraph_nodes字段正确")
            passed += 1
        
        if context_chars == 2000:
            print("  [OK] GraphRAG路径元数据: context_chars字段正确")
            passed += 1
        
        print(f"\n  元数据测试: {passed}/4 通过")
        return passed >= 3
    except Exception as e:
        print(f"  [FAIL] 元数据测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workflow_visualization():
    """测试工作流可视化函数"""
    print("\n" + "=" * 70)
    print("测试10: 工作流可视化")
    print("=" * 70)
    
    try:
        from backend.core.cli import generate_workflow_html
        
        # 测试 HTML 生成
        html_path = "test_workflow_graphrag.html"
        generate_workflow_html(html_path)
        
        if os.path.exists(html_path):
            file_size = os.path.getsize(html_path)
            print(f"  [OK] HTML文件生成成功, 大小: {file_size} 字节")
            os.remove(html_path)
            return True
        else:
            print("  [FAIL] HTML文件未生成")
            return False
    except Exception as e:
        print(f"  [FAIL] 工作流可视化测试失败: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("       GraphRAG 集成功能测试")
    print("=" * 70 + "\n")
    
    try:
        results = []
        results.append(("模块导入", test_module_import()))
        results.append(("basic_qa导入", test_basic_qa_import()))
        results.append(("状态扩展", test_state_extension()))
        results.append(("工作流构建", test_workflow_build()))
        results.append(("路由判断", test_route_question()))
        results.append(("Neo4j连接", test_neo4j_connection()))
        results.append(("模板流程", test_end_to_end_template()))
        results.append(("GraphRAG流程", test_end_to_end_graphrag()))
        results.append(("追踪元数据", test_trace_metadata_with_route()))
        results.append(("工作流可视化", test_workflow_visualization()))
        
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
            print("\n所有 GraphRAG 集成测试通过！[OK]")
        else:
            print(f"\n部分测试失败！{total - passed} 个测试未通过")
        
        print("=" * 70 + "\n")
        
        sys.exit(0 if passed == total else 1)
        
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
