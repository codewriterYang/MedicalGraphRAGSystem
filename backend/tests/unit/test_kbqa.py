#!/usr/bin/env python3
# coding: utf-8
"""
KBQA 模块单元测试

测试内容：
1. 意图定义不再包含药品相关意图（disease_drug / drug_disease）
2. LLM 提示词不包含药品相关描述
3. Cypher 模板不包含药品查询
4. LLM 引擎的合法实体类型不包含 drug / producer
5. 答案格式化不包含药品模板分支
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.kbqa.config import INTENT_TYPES, LLM_SYSTEM_PROMPT
from backend.domain.kbqa.cypher_generator import CYPHER_TEMPLATES
from backend.domain.kbqa.llm_engine import _VALID_ENTITY_TYPES


# ---------------------------------------------------------------------------
# Task 3.1.2: config.py 清理验证
# ---------------------------------------------------------------------------

class TestIntentCleanup:
    """验证 INTENT_TYPES 已移除药品相关意图。"""

    def test_disease_drug_not_in_intents(self):
        """INTENT_TYPES 不包含 disease_drug。"""
        assert "disease_drug" not in INTENT_TYPES

    def test_drug_disease_not_in_intents(self):
        """INTENT_TYPES 不包含 drug_disease。"""
        assert "drug_disease" not in INTENT_TYPES

    def test_intent_types_count(self):
        """INTENT_TYPES 应为 16 项。"""
        assert len(INTENT_TYPES) == 16

    def test_remaining_intents_valid(self):
        """保留的 16 种意图都还在。"""
        expected = {
            "disease_symptom", "symptom_disease", "disease_cause",
            "disease_acompany", "disease_do_food", "disease_not_food",
            "disease_check", "disease_prevent", "disease_lasttime",
            "disease_cureway", "disease_cureprob", "disease_easyget",
            "disease_desc", "check_disease", "food_do_disease",
            "food_not_disease",
        }
        assert set(INTENT_TYPES.keys()) == expected


class TestLLMPromptCleanup:
    """验证 LLM_SYSTEM_PROMPT 已移除药品相关描述。"""

    def test_no_drug_intent_in_prompt(self):
        """提示词不包含 disease_drug 意图。"""
        assert "disease_drug" not in LLM_SYSTEM_PROMPT

    def test_no_drug_disease_intent_in_prompt(self):
        """提示词不包含 drug_disease 意图。"""
        assert "drug_disease" not in LLM_SYSTEM_PROMPT

    def test_no_drug_entity_type_in_prompt(self):
        """提示词不包含 drug 实体类型定义。"""
        assert "- drug:" not in LLM_SYSTEM_PROMPT

    def test_other_intents_still_in_prompt(self):
        """保留的意图仍在提示词中。"""
        assert "disease_symptom" in LLM_SYSTEM_PROMPT
        assert "disease_cause" in LLM_SYSTEM_PROMPT
        assert "disease_do_food" in LLM_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Task 3.1.3: cypher_generator.py 清理验证
# ---------------------------------------------------------------------------

class TestCypherTemplateCleanup:
    """验证 CYPHER_TEMPLATES 已移除药品查询模板。"""

    def test_disease_drug_not_in_templates(self):
        """CYPHER_TEMPLATES 不包含 disease_drug。"""
        assert "disease_drug" not in CYPHER_TEMPLATES

    def test_drug_disease_not_in_templates(self):
        """CYPHER_TEMPLATES 不包含 drug_disease。"""
        assert "drug_disease" not in CYPHER_TEMPLATES

    def test_cypher_templates_count(self):
        """CYPHER_TEMPLATES 应为 16 项。"""
        assert len(CYPHER_TEMPLATES) == 16

    def test_no_drug_node_in_any_cypher(self):
        """所有 Cypher 模板中不引用 Drug 节点。"""
        for intent, templates in CYPHER_TEMPLATES.items():
            for tmpl in templates:
                assert ":Drug" not in tmpl, f"{intent} 的 Cypher 仍引用 Drug 节点"
                assert "common_drug" not in tmpl, f"{intent} 的 Cypher 仍引用 common_drug 关系"
                assert "recommand_drug" not in tmpl, f"{intent} 的 Cypher 仍引用 recommand_drug 关系"


# ---------------------------------------------------------------------------
# Task 3.1.4: llm_engine.py 清理验证
# ---------------------------------------------------------------------------

class TestValidEntityTypesCleanup:
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
# Task 3.1.5: answer_formatter.py 清理验证
# ---------------------------------------------------------------------------

class TestAnswerFormatterCleanup:
    """验证答案格式化不再包含药品模板。"""

    def test_no_drug_template_in_source(self):
        """answer_formatter.py 源码不包含 disease_drug 分支。"""
        source_path = Path(__file__).resolve().parent.parent.parent / \
                      "domain" / "kbqa" / "answer_formatter.py"
        source = source_path.read_text(encoding="utf-8")
        assert 'disease_drug' not in source
        assert 'drug_disease' not in source
