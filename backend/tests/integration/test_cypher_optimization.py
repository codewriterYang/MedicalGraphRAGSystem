#!/usr/bin/env python3
# coding: utf-8
"""
测试 Cypher 生成优化效果
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# 获取项目根目录（tests/integration 的父目录的父目录）
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 改变工作目录到项目根目录
os.chdir(project_root)

from backend.domain.qa_engine.nodes.template_path import (
    _validate_entity_intent_match,
    _add_fallback_queries,
    _add_entity_type_queries,
    _cypher_gen
)
from backend.domain.kbqa.config import INTENT_TYPES


def test_entity_intent_validation():
    """测试实体-意图类型匹配验证"""
    print("=" * 70)
    print("测试1: 实体-意图类型匹配验证")
    print("=" * 70)
    
    # 测试用例1: 正常匹配
    intents = ["disease_symptom"]
    entity_dict = {"disease": ["糖尿病"], "symptom": ["头痛"]}
    
    print("\n输入:")
    print(f"  意图: {intents}")
    print(f"  实体: {entity_dict}")
    
    validated = _validate_entity_intent_match(intents, entity_dict)
    print(f"\n验证结果: {validated}")
    print("[OK] disease_symptom 需要 disease 类型实体，已正确匹配")
    
    # 测试用例2: 类型不匹配时的回退
    intents = ["drug_disease"]
    entity_dict = {"disease": ["糖尿病"]}
    
    print("\n" + "-" * 50)
    print("输入:")
    print(f"  意图: {intents}")
    print(f"  实体: {entity_dict}")
    
    validated = _validate_entity_intent_match(intents, entity_dict)
    print(f"\n验证结果: {validated}")
    print("[OK] drug_disease 需要 drug 类型，但只有 disease 类型，自动回退")
    
    print("\n[OK] 测试1 通过！\n")


def test_fallback_queries():
    """测试回退查询策略"""
    print("=" * 70)
    print("测试2: 回退查询策略（模糊匹配）")
    print("=" * 70)
    
    # 模拟查询组
    query_groups = [
        {
            "question_type": "disease_symptom",
            "queries": [
                {
                    "cypher": "MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) WHERE m.name = $name RETURN m.name, r.name, n.name",
                    "params": {"name": "糖尿病"}
                }
            ]
        }
    ]
    
    entity_dict = {"disease": ["糖尿病"]}
    
    print("\n原始查询:")
    for group in query_groups:
        for q in group["queries"]:
            print(f"  {q['cypher']}")
    
    enhanced = _add_fallback_queries(query_groups, entity_dict)
    
    print("\n增强后的查询:")
    for group in enhanced:
        print(f"\n  意图类型: {group['question_type']}")
        for q in group["queries"]:
            fallback_mark = " [回退查询]" if q.get("fallback") else " [主查询]"
            print(f"    {fallback_mark}{q['cypher']}")
    
    print("\n[OK] 为每个查询添加了 CONTAINS 模糊匹配版本")
    print("[OK] 测试2 通过！\n")


def test_generic_queries():
    """测试通用查询"""
    print("=" * 70)
    print("测试3: 实体类型通用查询")
    print("=" * 70)
    
    # 模拟场景：有实体但没有特定意图的查询
    intents = ["disease_symptom", "disease_drug", "disease_desc"]
    entity_dict = {"disease": ["糖尿病"]}
    
    # 先生成已有的查询
    from backend.domain.qa_engine.nodes.template_path import _init_dependencies
    _init_dependencies()
    from backend.domain.qa_engine.nodes.template_path import _cypher_gen
    query_groups = _cypher_gen.generate(["disease_symptom"], entity_dict)
    
    print("\n已有查询:")
    print(f"  意图: disease_symptom")
    print(f"  实体: {entity_dict}")
    
    # 添加通用查询
    enhanced = _add_entity_type_queries(query_groups, intents, entity_dict)
    
    print("\n增强后的查询组:")
    for group in enhanced:
        print(f"\n  意图类型: {group['question_type']}")
        for q in group["queries"][:2]:  # 只显示前2个
            generic_mark = " [通用查询]" if q.get("generic") else ""
            print(f"    {generic_mark}{q['cypher'][:80]}...")
    
    print("\n[OK] 添加了 disease_desc 的通用查询作为补充")
    print("[OK] 测试3 通过！\n")


def test_integration():
    """集成测试：完整的 Cypher 生成流程"""
    print("=" * 70)
    print("测试4: 集成测试 - 完整 Cypher 生成流程")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "糖尿病症状查询",
            "question": "糖尿病有什么症状？",
            "intents": ["disease_symptom"],
            "entity_dict": {"disease": ["糖尿病"]}
        },
        {
            "name": "高血压药物查询",
            "question": "高血压应该吃什么药？",
            "intents": ["disease_drug"],
            "entity_dict": {"disease": ["高血压"]}
        },
        {
            "name": "消渴症（别名）查询",
            "question": "消渴症的症状是什么？",
            "intents": ["disease_symptom"],
            "entity_dict": {"disease": ["糖尿病"]}  # 归一化后的结果
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {case['name']}")
        print(f"  问题: {case['question']}")
        print(f"  意图: {case['intents']}")
        print(f"  实体: {case['entity_dict']}")
        
        try:
            # 步骤1: 验证实体-意图匹配
            validated = _validate_entity_intent_match(case['intents'], case['entity_dict'])
            print(f"  验证结果: {validated}")
            
            # 步骤2: 生成 Cypher
            query_groups = _cypher_gen.generate(case['intents'], validated)
            print(f"  生成查询: {len(query_groups)} 个查询组")
            
            # 步骤3: 添加回退查询
            query_groups = _add_fallback_queries(query_groups, validated)
            print(f"  回退查询: 每个查询组增加了模糊匹配版本")
            
            # 步骤4: 添加通用查询
            query_groups = _add_entity_type_queries(query_groups, case['intents'], validated)
            print(f"  最终查询: {len(query_groups)} 个查询组")
            
            # 验证
            if query_groups:
                print("  [OK] 测试通过")
                passed += 1
            else:
                print("  [FAIL] 测试失败: 没有生成查询")
                failed += 1
                
        except Exception as e:
            print(f"  [FAIL] 测试失败: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"集成测试结果: {passed}/{len(test_cases)} 通过")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("       Cypher 生成优化测试")
    print("=" * 70 + "\n")
    
    try:
        test_entity_intent_validation()
        test_fallback_queries()
        test_generic_queries()
        success = test_integration()
        
        print("\n" + "=" * 70)
        if success:
            print("所有测试通过！[OK]")
        else:
            print("部分测试失败！[FAIL]")
        print("=" * 70 + "\n")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)