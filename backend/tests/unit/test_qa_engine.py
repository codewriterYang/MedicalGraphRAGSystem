#!/usr/bin/env python3
# coding: utf-8
"""
qa_engine 模块单元测试

测试内容：
1. 降级逻辑不再包含 drug 相关意图和关键词
2. 路由逻辑正常
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.qa_engine.nodes.analysis import _build_keyword_lists, _keyword_classify


# ---------------------------------------------------------------------------
# Task 5.1: 降级逻辑清理验证
# ---------------------------------------------------------------------------

class TestKeywordListsCleanup:
    """验证 _build_keyword_lists 已移除药品相关关键词。"""

    def test_disease_drug_not_in_keyword_lists(self):
        """关键词列表不包含 disease_drug。"""
        kw = _build_keyword_lists()
        assert "disease_drug" not in kw

    def test_drug_disease_not_in_keyword_lists(self):
        """关键词列表不包含 drug_disease。"""
        kw = _build_keyword_lists()
        assert "drug_disease" not in kw

    def test_keyword_lists_count(self):
        """关键词列表应为 16 项（原 18 项 - 2 药品项）。"""
        kw = _build_keyword_lists()
        assert len(kw) == 16

    def test_remaining_intents_in_keyword_lists(self):
        """保留的意图关键词都还在。"""
        kw = _build_keyword_lists()
        expected = {
            "disease_symptom", "symptom_disease", "disease_cause",
            "disease_acompany", "disease_do_food", "disease_not_food",
            "disease_check", "disease_prevent", "disease_lasttime",
            "disease_cureway", "disease_cureprob", "disease_easyget",
            "disease_desc", "check_disease",
            "food_do_disease", "food_not_disease",
        }
        assert set(kw.keys()) == expected


class TestKeywordClassifyCleanup:
    """验证 _keyword_classify 不再匹配 drug 相关意图。"""

    def test_drug_entity_type_no_longer_matches_drug_intents(self):
        """drug 类型实体不应再匹配 drug_disease 或 disease_drug。"""
        intents = _keyword_classify("阿莫西林治什么病", {"drug"})
        assert "drug_disease" not in intents
        assert "disease_drug" not in intents

    def test_disease_entity_no_longer_falls_back_to_disease_drug(self):
        """disease 类型实体的兜底意图不应包含 disease_drug。"""
        intents = _keyword_classify("这是什么病", {"disease"})
        assert "disease_drug" not in intents

    def test_disease_entity_still_gets_valid_intents(self):
        """disease 类型实体仍能匹配有效意图。"""
        intents = _keyword_classify("糖尿病有什么症状", {"disease"})
        assert "disease_symptom" in intents

    def test_food_entity_still_works(self):
        """food 类型实体仍能正常工作。"""
        intents = _keyword_classify("苹果对什么病有益", {"food"})
        assert len(intents) > 0
        assert "disease_drug" not in intents
        assert "drug_disease" not in intents
