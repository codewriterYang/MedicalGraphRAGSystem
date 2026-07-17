#!/usr/bin/env python3
# coding: utf-8
"""
GraphRAG 模块单元测试

测试内容：
1. ENTITY_EXTRACT_PROMPT 不包含 drug 实体类型
2. _VALID_ENTITY_TYPES 不包含 drug / producer
3. REL_LABELS 不包含药品相关关系标签
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.graphrag.config import ENTITY_EXTRACT_PROMPT
from backend.domain.graphrag.entity_extractor import _VALID_ENTITY_TYPES
from backend.domain.graphrag.context_builder import REL_LABELS


# ---------------------------------------------------------------------------
# Task 4.1.2: config.py 提示词清理验证
# ---------------------------------------------------------------------------

class TestEntityExtractPromptCleanup:
    """验证 ENTITY_EXTRACT_PROMPT 已移除药品相关描述。"""

    def test_no_drug_entity_type_in_prompt(self):
        """提示词不包含 drug 实体类型定义。"""
        assert "- drug:" not in ENTITY_EXTRACT_PROMPT

    def test_other_entity_types_still_in_prompt(self):
        """保留的实体类型仍在提示词中。"""
        assert "- disease:" in ENTITY_EXTRACT_PROMPT
        assert "- symptom:" in ENTITY_EXTRACT_PROMPT
        assert "- check:" in ENTITY_EXTRACT_PROMPT
        assert "- food:" in ENTITY_EXTRACT_PROMPT
        assert "- department:" in ENTITY_EXTRACT_PROMPT


# ---------------------------------------------------------------------------
# Task 4.1.3: entity_extractor.py 清理验证
# ---------------------------------------------------------------------------

class TestEntityExtractorValidTypes:
    """验证 _VALID_ENTITY_TYPES 已移除 drug / producer。"""

    def test_drug_not_in_valid_types(self):
        """_VALID_ENTITY_TYPES 不包含 drug。"""
        assert "drug" not in _VALID_ENTITY_TYPES

    def test_producer_not_in_valid_types(self):
        """_VALID_ENTITY_TYPES 不包含 producer。"""
        assert "producer" not in _VALID_ENTITY_TYPES

    def test_valid_entity_types_count(self):
        """_VALID_ENTITY_TYPES 应为 5 项。"""
        assert len(_VALID_ENTITY_TYPES) == 5

    def test_remaining_entity_types(self):
        """保留的 5 种实体类型都还在。"""
        expected = {"disease", "symptom", "food", "check", "department"}
        assert _VALID_ENTITY_TYPES == expected


# ---------------------------------------------------------------------------
# Task 4.1.4: context_builder.py 清理验证
# ---------------------------------------------------------------------------

class TestRelLabelsCleanup:
    """验证 REL_LABELS 已移除药品相关关系标签。"""

    def test_common_drug_not_in_rel_labels(self):
        """REL_LABELS 不包含 common_drug。"""
        assert "common_drug" not in REL_LABELS

    def test_recommand_drug_not_in_rel_labels(self):
        """REL_LABELS 不包含 recommand_drug。"""
        assert "recommand_drug" not in REL_LABELS

    def test_drugs_of_not_in_rel_labels(self):
        """REL_LABELS 不包含 drugs_of。"""
        assert "drugs_of" not in REL_LABELS

    def test_rel_labels_count(self):
        """REL_LABELS 应为 8 项。"""
        assert len(REL_LABELS) == 8

    def test_remaining_rel_labels(self):
        """保留的 8 种关系标签都还在。"""
        expected = {
            "has_symptom", "acompany_with", "do_eat", "no_eat",
            "recommand_eat", "need_check", "belongs_to", "dept_belongs_to",
        }
        assert set(REL_LABELS.keys()) == expected
