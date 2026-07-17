#!/usr/bin/env python3
# coding: utf-8
"""
Cypher生成器单元测试

测试内容：
1. 意图到Cypher模板的映射
2. 参数化查询生成
3. 多意图查询生成
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.kbqa.cypher_generator import CypherGenerator


def test_cypher_generator():
    """测试Cypher生成器"""
    generator = CypherGenerator()
    print("=" * 60)
    print("      Cypher生成器单元测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "name": "疾病症状查询",
            "intents": ["disease_symptom"],
            "entity_dict": {"disease": ["糖尿病"]},
            "expected_query_count": 1,
        },
        {
            "name": "疾病药物查询",
            "intents": ["disease_drug"],
            "entity_dict": {"disease": ["高血压"]},
            "expected_query_count": 1,
        },
        {
            "name": "多意图查询",
            "intents": ["disease_symptom", "disease_drug"],
            "entity_dict": {"disease": ["糖尿病"]},
            "expected_query_count": 2,
        },
        {
            "name": "多实体查询",
            "intents": ["disease_symptom"],
            "entity_dict": {"disease": ["糖尿病", "高血压"]},
            "expected_query_count": 2,
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print("")
        print("测试用例 %d: %s" % (i, test_case['name']))
        print("  意图: %s" % test_case['intents'])
        print("  实体: %s" % test_case['entity_dict'])
        
        try:
            query_groups = generator.generate(test_case['intents'], test_case['entity_dict'])
            
            # 统计查询数量
            total_queries = 0
            for group in query_groups:
                total_queries += len(group.get("queries", []))
                for q in group.get("queries", []):
                    print("    Cypher: %s" % q['cypher'][:60])
            
            if total_queries == test_case['expected_query_count']:
                print("  [OK] 查询数量正确: %d" % total_queries)
                passed += 1
            else:
                print("  [FAIL] 查询数量错误 (预期: %d, 实际: %d)" % (test_case['expected_query_count'], total_queries))
                failed += 1
                
        except Exception as e:
            print("  [ERROR] 异常: %s" % e)
            failed += 1
    
    print("")
    print("=" * 60)
    print("测试结果: %d 通过, %d 失败" % (passed, failed))
    print("=" * 60)


if __name__ == "__main__":
    test_cypher_generator()