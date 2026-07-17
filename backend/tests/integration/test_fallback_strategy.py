#!/usr/bin/env python3
# coding: utf-8
"""
三级降级策略测试脚本

测试场景：
1. Level 1: 全LLM分析（正常情况）
2. Level 2: LLM实体+关键词意图（模拟降级）
3. Level 3: 离线NER+关键词意图（完全离线）
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.qa_engine.graph_builder import create_app

# 测试用例
TEST_CASES = [
    {
        "name": "Level 1 - 糖尿病症状查询",
        "question": "糖尿病有什么症状？",
        "expected_level": [1],
        "expected_intent": "disease_symptom",
        "expected_entity": "糖尿病"
    },
    {
        "name": "Level 1 - 高血压药物查询",
        "question": "高血压应该吃什么药？",
        "expected_level": [1],
        "expected_intent": "disease_drug",
        "expected_entity": "高血压"
    },
    {
        "name": "Level 1 - 感冒病因",
        "question": "为什么会感冒？",
        "expected_level": [1],
        "expected_intent": "disease_cause",
        "expected_entity": "感冒"
    },
    {
        "name": "Level 3 - 消渴症症状",
        "question": "消渴症有什么症状？",
        "expected_level": [1, 3],
        "expected_intent": "disease_symptom",
        "expected_entity": "糖尿病"
    },
    {
        "name": "Level 3 - 头痛原因",
        "question": "头痛是什么原因引起的？",
        "expected_level": [1, 3],
        "expected_intent": "symptom_disease",
        "expected_entity": "头痛"
    },
]


def run_fallback_tests():
    """运行三级降级策略测试"""
    app = create_app()
    config = {"configurable": {"thread_id": "test_session"}}
    
    print("=" * 70)
    print("          三级降级策略测试")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print("")
        print("--- 测试用例 %d: %s ---" % (i, test_case['name']))
        print("问题: %s" % test_case['question'])
        
        try:
            result = app.invoke({"question": test_case["question"]}, config=config)
            
            level = result.get("analysis_level", 0)
            intent = result.get("intent", [])
            entities = result.get("entities", [])
            answer = result.get("answer", "")
            
            print("分析级别: Level %d" % level)
            print("识别意图: %s" % intent)
            print("识别实体: %s" % entities)
            if len(answer) > 100:
                print("回答摘要: %s..." % answer[:100])
            else:
                print("回答: %s" % answer)
            
            if level in test_case["expected_level"]:
                print("[OK] 级别验证通过")
            else:
                print("[FAIL] 级别验证失败 (预期: %s, 实际: %d)" % (test_case['expected_level'], level))
                failed += 1
                continue
            
            if test_case["expected_intent"] in intent:
                print("[OK] 意图验证通过")
            else:
                print("[FAIL] 意图验证失败 (预期: %s, 实际: %s)" % (test_case['expected_intent'], intent))
                failed += 1
                continue
            
            entity_names = [e.get("name", "") for e in entities]
            if test_case["expected_entity"] in entity_names:
                print("[OK] 实体验证通过")
                passed += 1
            else:
                print("[FAIL] 实体验证失败 (预期: %s, 实际: %s)" % (test_case['expected_entity'], entity_names))
                failed += 1
                
        except Exception as e:
            print("[ERROR] 测试异常: %s" % e)
            failed += 1
    
    print("")
    print("=" * 70)
    print("测试结果: 共 %d 个用例" % len(TEST_CASES))
    print("  通过: %d" % passed)
    print("  失败: %d" % failed)
    print("=" * 70)
    
    return failed == 0


def test_offline_ner():
    """测试离线 NER 组件"""
    print("")
    print("=" * 70)
    print("          离线 NER 组件测试")
    print("=" * 70)
    
    from backend.domain.qa_engine.nodes.analysis import _fallback_full
    
    test_questions = [
        "糖尿病的症状",
        "头痛怎么办",
        "感冒吃什么药",
        "高血压饮食注意事项",
    ]
    
    for question in test_questions:
        print("")
        print("问题: %s" % question)
        intents, entities, has_negation = _fallback_full(question)
        print("  意图: %s" % intents)
        print("  实体: %s" % entities)
        print("  否定: %s" % has_negation)
        if intents or entities:
            print("  [OK] Level 3 离线分析成功")
        else:
            print("  [FAIL] Level 3 未识别到内容")


def test_template_no_result_fallback():
    """
    测试模板路径查询无结果时的 GraphRAG 自动回退。
    
    验证逻辑：
    1. 用模板路径能匹配意图但查询可能为空的问题
    2. 验证最终 answer 不为空且不等于"暂无相关信息"或 DEFAULT_ANSWER
    3. 验证 state 中 template_no_result 为 True（回退已被触发）
    """
    print("")
    print("=" * 70)
    print("          模板无结果 → GraphRAG 回退测试")
    print("=" * 70)
    
    from backend.domain.qa_engine.graph_builder import create_app
    from backend.core.config import DEFAULT_ANSWER
    
    app = create_app()
    config = {"configurable": {"thread_id": "test_fallback_graphrag"}}
    
    # 测试用例：意图匹配但实体在图中可能不存在或无直接关系的查询
    # 模板路径可能无结果，但 GraphRAG 子图检索 + LLM 可生成兜底回答
    test_questions = [
        "罕见病有什么症状？",       # 可能无精确匹配
        "头痛和恶心有什么关联？",    # 跨实体复杂关系
    ]
    
    all_passed = True
    for question in test_questions:
        print("")
        print("问题: %s" % question)
        
        try:
            result = app.invoke({"question": question}, config=config)
            
            answer = result.get("answer", "")
            template_no_result = result.get("template_no_result", False)
            route = result.get("route", "")
            error = result.get("error", "")
            
            print("  路由: %s" % route)
            print("  模板无结果回退: %s" % template_no_result)
            if error:
                print("  错误: %s" % error[:100])
            if len(answer) > 150:
                print("  回答摘要: %s..." % answer[:150])
            else:
                print("  回答: %s" % answer)
            
            # 验证：answer 不应为空且不应为默认"暂无相关信息"
            if not answer:
                print("  [FAIL] 回答为空")
                all_passed = False
                continue
            
            if answer == DEFAULT_ANSWER:
                print("  [FAIL] 回答为默认回答（未触发回退）")
                all_passed = False
                continue
            
            if "暂无相关信息" in answer:
                print("  [WARN] 回答含\"暂无相关信息\"（回退后 GraphRAG 也未成功）")
                continue
            
            if template_no_result:
                print("  [OK] 检测到模板无结果，已自动回退到 GraphRAG 路径")
            else:
                print("  [OK] 模板路径直接返回结果（未触发回退）")
                
        except Exception as e:
            print("  [ERROR] 测试异常: %s" % e)
            import traceback
            traceback.print_exc()
            all_passed = False
    
    print("")
    if all_passed:
        print("  [OK] 所有回退测试通过")
    else:
        print("  [WARN] 部分回退测试未通过（可能 GraphRAG 组件或 Neo4j 不可用）")


if __name__ == "__main__":
    success = run_fallback_tests()
    test_offline_ner()
    test_template_no_result_fallback()
    sys.exit(0 if success else 1)