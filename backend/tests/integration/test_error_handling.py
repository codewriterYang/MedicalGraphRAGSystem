#!/usr/bin/env python3
# coding: utf-8
"""
测试统一异常处理机制
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

from backend.domain.qa_engine.nodes.error_handler import (
    handle_error,
    should_handle_error,
)
from backend.domain.qa_engine.nodes.normalize import normalize_entities
from backend.domain.qa_engine.nodes.template_path import generate_cypher, execute_query, format_answer
from backend.domain.qa_engine.state import QAState


def test_should_handle_error():
    """测试错误判断函数"""
    print("=" * 70)
    print("测试1: 错误判断函数 should_handle_error")
    print("=" * 70)
    
    test_cases = [
        {"error": "", "no_results": False, "expected": False, "desc": "无错误无结果"},
        {"error": "测试错误", "no_results": False, "expected": True, "desc": "有错误"},
        {"error": "", "no_results": True, "expected": True, "desc": "无结果"},
        {"error": "错误", "no_results": True, "expected": True, "desc": "错误+无结果"},
    ]
    
    passed = 0
    for case in test_cases:
        state = {"error": case["error"], "no_results": case["no_results"]}
        result = should_handle_error(state)
        status = "[OK]" if result == case["expected"] else "[FAIL]"
        print(f"  {status} {case['desc']}: expected={case['expected']}, got={result}")
        if result == case["expected"]:
            passed += 1
    
    print(f"\n测试结果: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_handle_error_no_results():
    """测试查询无结果的错误处理"""
    print("\n" + "=" * 70)
    print("测试2: 查询无结果的错误处理")
    print("=" * 70)
    
    state = {
        "error": "",
        "no_results": True
    }
    
    result = handle_error(state)
    
    print(f"  输入: no_results={state['no_results']}")
    print(f"  输出: answer='{result['answer']}'")
    print(f"  error: '{result['error']}'")
    
    # 静态兜底（LLM 不可用时）应返回友好的提示文本
    expected_answer = "知识库中暂无相关信息，建议您换一种方式提问，或咨询专业医生。"
    status = "[OK]" if result["answer"] == expected_answer else "[FAIL]"
    print(f"  {status} 错误提示正确")
    
    return result["answer"] == expected_answer and result["error"] == ""


def test_handle_error_llm_failure():
    """测试 LLM 调用失败的错误处理"""
    print("\n" + "=" * 70)
    print("测试3: LLM 调用失败的错误处理")
    print("=" * 70)
    
    test_cases = [
        {"error": "LLM timeout error", "expected": "AI 服务暂时不可用，请稍后重试。"},
        {"error": "analyze failed", "expected": "AI 服务暂时不可用，请稍后重试。"},
        {"error": "timeout occurred", "expected": "AI 服务暂时不可用，请稍后重试。"},
    ]
    
    passed = 0
    for case in test_cases:
        state = {"error": case["error"], "no_results": False}
        result = handle_error(state)
        
        print(f"  输入: error='{case['error']}'")
        print(f"  输出: answer='{result['answer']}'")
        
        status = "[OK]" if result["answer"] == case["expected"] else "[FAIL]"
        print(f"  {status} 错误提示正确\n")
        
        if result["answer"] == case["expected"]:
            passed += 1
    
    print(f"测试结果: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_handle_error_cypher_failure():
    """测试 Cypher 执行失败的错误处理"""
    print("\n" + "=" * 70)
    print("测试4: Cypher 执行失败的错误处理")
    print("=" * 70)
    
    test_cases = [
        {"error": "Cypher syntax error", "expected": "内部查询错误，已记录日志，请稍后重试。"},
        {"error": "cypher query failed", "expected": "内部查询错误，已记录日志，请稍后重试。"},
        {"error": "invalid query", "expected": "内部查询错误，已记录日志，请稍后重试。"},
    ]
    
    passed = 0
    for case in test_cases:
        state = {"error": case["error"], "no_results": False}
        result = handle_error(state)
        
        print(f"  输入: error='{case['error']}'")
        print(f"  输出: answer='{result['answer']}'")
        
        status = "[OK]" if result["answer"] == case["expected"] else "[FAIL]"
        print(f"  {status} 错误提示正确\n")
        
        if result["answer"] == case["expected"]:
            passed += 1
    
    print(f"测试结果: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_handle_error_neo4j_failure():
    """测试 Neo4j 连接失败的错误处理"""
    print("\n" + "=" * 70)
    print("测试5: Neo4j 连接失败的错误处理")
    print("=" * 70)
    
    test_cases = [
        {"error": "Neo4j connection refused", "expected": "数据库服务暂时不可用，请稍后重试。"},
        {"error": "graph database error", "expected": "数据库服务暂时不可用，请稍后重试。"},
    ]
    
    passed = 0
    for case in test_cases:
        state = {"error": case["error"], "no_results": False}
        result = handle_error(state)
        
        print(f"  输入: error='{case['error']}'")
        print(f"  输出: answer='{result['answer']}'")
        
        status = "[OK]" if result["answer"] == case["expected"] else "[FAIL]"
        print(f"  {status} 错误提示正确\n")
        
        if result["answer"] == case["expected"]:
            passed += 1
    
    print(f"测试结果: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_handle_error_unknown():
    """测试未知错误的错误处理（非系统级错误→可恢复→LLM兜底）"""
    print("\n" + "=" * 70)
    print("测试6: 未知错误的错误处理")
    print("=" * 70)
    
    state = {"error": "Some unknown error", "no_results": False}
    result = handle_error(state)
    
    print(f"  输入: error='{state['error']}'")
    print(f"  输出: answer='{result['answer'][:60]}...'")
    
    # 新行为：非系统级未知错误被视为可恢复，尝试 LLM 兜底
    # 无 question 时回退到静态文本
    expected_answer = "知识库中暂无相关信息，建议您换一种方式提问，或咨询专业医生。"
    status = "[OK]" if result["answer"] == expected_answer else "[FAIL]"
    print(f"  {status} 可恢复错误→静态兜底")
    
    return result["answer"] == expected_answer


def test_normalize_entities_no_entities():
    """测试 normalize_entities 节点无实体情况（应设 template_no_result 回退而非 error）"""
    print("\n" + "=" * 70)
    print("测试7: normalize_entities 节点无实体情况")
    print("=" * 70)
    
    state = {"entities": [], "params": {}}
    result = normalize_entities(state)
    
    print(f"  输入: entities={state['entities']}")
    print(f"  输出: template_no_result={result.get('template_no_result')}")
    print(f"  输出: no_results={result.get('no_results')}")
    print(f"  输出: error='{result.get('error', '')}'")
    
    # 新行为：不设 error/no_results，改为 template_no_result，自动回退 GraphRAG
    t_ok = result.get("template_no_result") == True and result.get("no_results") == False and result.get("error", "") == ""
    status = "[OK]" if t_ok else "[FAIL]"
    print(f"  {status} 正确设置 template_no_result=True，不设 error（走回退链路）")
    
    return t_ok


def test_generate_cypher_no_intents():
    """测试 generate_cypher 节点无意图情况（应触发回退而非错误）"""
    print("\n" + "=" * 70)
    print("测试8: generate_cypher 节点无意图情况")
    print("=" * 70)
    
    state = {
        "intent": [],
        "normalized_entities": {"entity_dict": {}, "entities": {}}
    }
    result = generate_cypher(state)
    
    print(f"  输入: intent={state['intent']}")
    print(f"  输出: template_no_result={result.get('template_no_result')}")
    print(f"  输出: no_results={result['no_results']}")
    print(f"  输出: error='{result.get('error', '')}'")
    
    # 关键变更：不再设置 error/no_results，改为 template_no_result
    # 让工作流自动回退到 GraphRAG/LLM 兜底
    template_no_result_ok = result.get("template_no_result") == True
    no_error = result.get("error", "") == ""
    status = "[OK]" if template_no_result_ok and no_error else "[FAIL]"
    print(f"  {status} 正确设置 template_no_result=True，不设 error（走回退链路）")
    
    return template_no_result_ok and no_error


def test_format_answer_no_results():
    """测试 format_answer 节点无结果情况"""
    print("\n" + "=" * 70)
    print("测试9: format_answer 节点无结果情况")
    print("=" * 70)
    
    state = {
        "raw_results": [],
        "no_results": True
    }
    result = format_answer(state)
    
    print(f"  输入: raw_results={state['raw_results']}, no_results={state['no_results']}")
    print(f"  输出: answer='{result['answer']}'")
    
    # format_answer 在 no_results=True 时返回空答案，让 handle_error 处理
    # 不再设置 no_results 标记，避免重复设置
    status = "[OK]" if result["answer"] == "" and "error" in result else "[FAIL]"
    print(f"  {status} 正确设置空答案（由 handle_error 统一处理）")
    
    return result["answer"] == "" and "error" in result


def test_workflow_error_propagation():
    """测试工作流错误传播"""
    print("\n" + "=" * 70)
    print("测试10: 工作流错误传播机制")
    print("=" * 70)
    
    # 模拟完整的工作流错误传播
    print("  场景: 用户输入无法识别的实体")
    
    # 步骤1: normalize_entities 返回无实体
    state1 = {"entities": [], "params": {}}
    result1 = normalize_entities(state1)
    print(f"  步骤1: normalize_entities -> no_results={result1['no_results']}")
    
    # 步骤2: 检查是否应该跳转到错误处理
    should_error = should_handle_error(result1)
    print(f"  步骤2: should_handle_error -> {should_error}")
    
    # 步骤3: handle_error 处理
    if should_error:
        final_result = handle_error(result1)
        print(f"  步骤3: handle_error -> answer='{final_result['answer'][:50]}...'")
    
    status = "[OK]" if should_error and final_result["answer"] != "" else "[FAIL]"
    print(f"  {status} 错误传播机制正确")
    
    return should_error and final_result["answer"] != ""


def _run_qa(question: str) -> dict:
    """运行完整工作流获取结果（测试辅助）。"""
    from backend.domain.qa_engine.graph_builder import create_app
    app = create_app()
    config = {"configurable": {"thread_id": "test-llm-fallback"}}
    result = app.invoke({"question": question}, config=config)
    return result


def test_llm_fallback_for_unmatched_question():
    """测试口语化问题触发 LLM 兜底（需要 Neo4j + LLM 可用）。
    
    当问题在知识图谱中无法匹配到实体时，系统应触发 LLM 兜底，
    返回带有免责声明的回答，而非静态的"暂无相关信息"。
    
    若 Neo4j 或 LLM 不可用，测试会优雅跳过。
    """
    print("\n" + "=" * 70)
    print("测试11: 口语化问题 LLM 兜底")
    print("=" * 70)

    question = "999感冒药能吃嘛？"

    try:
        result = _run_qa(question)
        answer = result.get("answer", "")
        route = result.get("route", "")

        print(f"  问题: {question}")
        print(f"  路由: {route}")
        print(f"  回答: {answer[:100]}...")

        # 不应该返回旧的静态文本
        old_static = "知识库中暂无相关信息，建议咨询专业医生。"
        status1 = answer != old_static
        print(f"  [{'OK' if status1 else 'FAIL'}] 未返回旧版静态文本")

        # 应该包含免责声明或咨询建议
        has_disclaimer = "仅供参考" in answer or "咨询" in answer or "医生" in answer
        print(f"  [{'OK' if has_disclaimer else 'FAIL'}] 包含免责/咨询声明")

        # route 应该是合法值
        valid_routes = {"template", "graphrag", "llm_fallback", ""}
        status3 = (route or "") in valid_routes
        print(f"  [{'OK' if status3 else 'FAIL'}] route 合法: {route}")

        passed = status1 and has_disclaimer and status3
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} LLM 兜底测试")
        return passed

    except Exception as e:
        msg = str(e)
        if "Neo4j" in msg or "connection" in msg.lower():
            print(f"  [SKIP] Neo4j 不可用，跳过集成测试: {e}")
            return True  # 环境不满足，不算失败
        if "LLM" in msg or "openai" in msg.lower():
            print(f"  [SKIP] LLM 不可用，跳过集成测试: {e}")
            return True
        print(f"  [ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("       统一异常处理机制测试")
    print("=" * 70 + "\n")
    
    try:
        results = []
        results.append(("错误判断函数", test_should_handle_error()))
        results.append(("无结果处理", test_handle_error_no_results()))
        results.append(("LLM失败处理", test_handle_error_llm_failure()))
        results.append(("Cypher失败处理", test_handle_error_cypher_failure()))
        results.append(("Neo4j失败处理", test_handle_error_neo4j_failure()))
        results.append(("未知错误处理", test_handle_error_unknown()))
        results.append(("无实体节点", test_normalize_entities_no_entities()))
        results.append(("无意图节点", test_generate_cypher_no_intents()))
        results.append(("无结果格式化", test_format_answer_no_results()))
        results.append(("错误传播机制", test_workflow_error_propagation()))
        results.append(("LLM兜底(口语化)", test_llm_fallback_for_unmatched_question()))
        
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
            print("\n所有统一异常处理测试通过！[OK]")
        else:
            print(f"\n部分测试失败！{total - passed} 个测试未通过")
        
        print("=" * 70 + "\n")
        
        sys.exit(0 if passed == total else 1)
        
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)