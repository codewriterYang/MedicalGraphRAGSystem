#!/usr/bin/env python3
# coding: utf-8
"""
实体归一化器单元测试

测试内容：
1. 精确匹配
2. 子串匹配
3. 模糊匹配
4. 否定词识别
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.kbqa.entity_normalizer import EntityNormalizer


def test_entity_normalizer():
    """测试实体归一化器"""
    normalizer = EntityNormalizer()
    print("=" * 60)
    print("      实体归一化器单元测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {"input": {"name": "糖尿病", "type": "disease"}, "expected": "糖尿病"},
        {"input": {"name": "消渴症", "type": "disease"}, "expected": "糖尿病"},  # 中医术语
        {"input": {"name": "糖料病", "type": "disease"}, "expected": "糖尿病"},  # 拼写错误
        {"input": {"name": "高血压", "type": "disease"}, "expected": "高血压"},
        {"input": {"name": "血压高", "type": "disease"}, "expected": "高血压"},  # 口语表达
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print("")
        print("测试用例 %d:" % i)
        print("  输入: %s" % test_case['input'])
        
        try:
            result = normalizer.normalize([test_case['input']], has_negation=False)
            entity_dict = result.get("entity_dict", {})
            
            matched = []
            for etype, names in entity_dict.items():
                matched.extend(names)
            
            if test_case['expected'] in matched:
                print("  [OK] 匹配成功: %s" % matched)
                passed += 1
            else:
                print("  [FAIL] 匹配失败 (预期: %s, 实际: %s)" % (test_case['expected'], matched))
                failed += 1
        except Exception as e:
            print("  [ERROR] 异常: %s" % e)
            failed += 1
    
    # 测试否定词识别
    print("")
    print("否定词识别测试:")
    deny_tests = [
        ("糖尿病不能吃什么", True),
        ("糖尿病可以吃什么", False),
        ("不要吃辛辣食物", True),
        ("适合吃的食物", False),
    ]
    
    for question, expected in deny_tests:
        has_deny = any(w in question for w in normalizer.deny_words)
        status = "[OK]" if has_deny == expected else "[FAIL]"
        print("  %s '%s' → 否定: %s (预期: %s)" % (status, question, has_deny, expected))
    
    print("")
    print("=" * 60)
    print("测试结果: %d 通过, %d 失败" % (passed, failed))
    print("=" * 60)


if __name__ == "__main__":
    test_entity_normalizer()