#!/usr/bin/env python3
# coding: utf-8
"""
knowledge_graph 模块单元测试

测试内容：
1. Schema 不再包含药品相关节点/关系类型
2. DataLoader 处理新数据时不创建 Drug/Producer 节点
3. DataLoader 处理新数据时不创建药品相关关系
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.knowledge_graph.config import NODE_LABELS, REL_TYPES, DISEASE_PROPS
from backend.domain.knowledge_graph.data_loader import DataLoader


# ---------------------------------------------------------------------------
# 测试数据（模拟新 medical.json 格式，药品字段为空）
# ---------------------------------------------------------------------------
SAMPLE_RECORD = {
    "name": "测试疾病",
    "desc": "测试描述",
    "category": ["疾病百科", "内科", "心内科"],
    "prevent": "预防措施",
    "cause": "病因",
    "symptom": ["症状A", "症状B"],
    "acompany": ["并发症X"],
    "cure_department": ["内科", "心内科"],
    "cure_way": ["药物治疗"],
    "cure_lasttime": "1-2个月",
    "cured_prob": "80%",
    "get_prob": "1%",
    "yibao_status": "否",
    "easy_get": "老年人",
    "get_way": "无传染性",
    "cost_money": "5000元",
    "check": ["血常规"],
    "do_eat": ["苹果"],
    "not_eat": ["辣椒"],
    "recommand_eat": ["苹果粥"],
    "recommand_drug": [],
    "drug_detail": [],
}


def _write_temp_jsonl(records):
    """写入临时 JSONL 文件并返回路径。"""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# Task 2.1.1: Schema 清理验证
# ---------------------------------------------------------------------------

class TestSchemaCleanup:
    """验证 Schema 已移除药品相关定义。"""

    def test_drug_not_in_node_labels(self):
        """NODE_LABELS 不包含 Drug。"""
        assert "Drug" not in NODE_LABELS

    def test_producer_not_in_node_labels(self):
        """NODE_LABELS 不包含 Producer。"""
        assert "Producer" not in NODE_LABELS

    def test_node_labels_count(self):
        """NODE_LABELS 应为 5 项（Disease/Symptom/Food/Check/Department）。"""
        assert len(NODE_LABELS) == 5

    def test_common_drug_not_in_rel_types(self):
        """REL_TYPES 不包含 common_drug。"""
        assert "common_drug" not in REL_TYPES

    def test_recommand_drug_not_in_rel_types(self):
        """REL_TYPES 不包含 recommand_drug。"""
        assert "recommand_drug" not in REL_TYPES

    def test_drugs_of_not_in_rel_types(self):
        """REL_TYPES 不包含 drugs_of。"""
        assert "drugs_of" not in REL_TYPES

    def test_rel_types_count(self):
        """REL_TYPES 应为 8 项。"""
        assert len(REL_TYPES) == 8


# ---------------------------------------------------------------------------
# Task 2.1.2: DataLoader 不产生药品节点/关系
# ---------------------------------------------------------------------------

class TestDataLoaderNoDrug:
    """验证 DataLoader 处理新数据时不产生 Drug/Producer 节点和药品关系。"""

    def setup_method(self):
        self.data_path = _write_temp_jsonl([SAMPLE_RECORD])
        self.loader = DataLoader(self.data_path)
        self.nodes, self.rels, self.disease_infos = self.loader.load()

    def test_no_drug_nodes(self):
        """nodes 中不包含 Drug 键或为空集合。"""
        drug_nodes = self.nodes.get("Drug", set())
        assert len(drug_nodes) == 0

    def test_no_producer_nodes(self):
        """nodes 中不包含 Producer 键或为空集合。"""
        producer_nodes = self.nodes.get("Producer", set())
        assert len(producer_nodes) == 0

    def test_no_common_drug_rels(self):
        """rels 中 common_drug 为空。"""
        assert len(self.rels.get("common_drug", [])) == 0

    def test_no_recommand_drug_rels(self):
        """rels 中 recommand_drug 为空。"""
        assert len(self.rels.get("recommand_drug", [])) == 0

    def test_no_drugs_of_rels(self):
        """rels 中 drugs_of 为空。"""
        assert len(self.rels.get("drugs_of", [])) == 0

    def test_other_nodes_still_created(self):
        """非药品节点正常创建。"""
        assert "测试疾病" in self.nodes.get("Disease", set())
        assert "症状A" in self.nodes.get("Symptom", set())
        assert "苹果" in self.nodes.get("Food", set())
        assert "血常规" in self.nodes.get("Check", set())
        assert "心内科" in self.nodes.get("Department", set())

    def test_other_rels_still_created(self):
        """非药品关系正常创建。"""
        assert ("测试疾病", "症状A") in self.rels.get("has_symptom", [])
        assert ("测试疾病", "苹果") in self.rels.get("do_eat", [])
        assert ("测试疾病", "血常规") in self.rels.get("need_check", [])

    def test_disease_infos_complete(self):
        """疾病属性完整。"""
        assert len(self.disease_infos) == 1
        info = self.disease_infos[0]
        assert info["name"] == "测试疾病"
        assert info["desc"] == "测试描述"
        assert "common_drug" not in info or info.get("common_drug", "") == ""
