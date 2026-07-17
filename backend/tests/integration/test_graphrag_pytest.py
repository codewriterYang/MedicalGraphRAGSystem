#!/usr/bin/env python3
# coding: utf-8
"""
GraphRAG 集成测试（pytest 风格）

需要 Neo4j 连接 + LLM + 已导入的图谱数据。
运行方式: python -m pytest backend/tests/integration/test_graphrag_integration.py -v
跳过条件: Neo4j 或 LLM 不可用时自动跳过。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.domain.graphrag.config import (
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
    ENTITY_EXTRACT_PROMPT, create_llm,
)
from backend.domain.graphrag.entity_extractor import EntityExtractor, _VALID_ENTITY_TYPES
from backend.domain.graphrag.subgraph_retriever import SubgraphRetriever
from backend.domain.graphrag.context_builder import ContextBuilder, REL_LABELS
from backend.domain.graphrag.generator import GraphRAGGenerator

# ---------------------------------------------------------------------------
# Neo4j 可用性检测
# ---------------------------------------------------------------------------
_neo4j_available = False
_neo4j_skip_reason = ""

try:
    from py2neo import Graph
    _test_graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    _test_graph.run("RETURN 1").data()
    _neo4j_available = True
except Exception as e:
    _neo4j_skip_reason = f"Neo4j 不可用: {e}"

skip_no_neo4j = pytest.mark.skipif(
    not _neo4j_available,
    reason=_neo4j_skip_reason or "Neo4j 不可用",
)

# ---------------------------------------------------------------------------
# LLM 可用性检测
# ---------------------------------------------------------------------------
_llm_available = False
_llm_skip_reason = ""

try:
    _test_llm = create_llm()
    if _test_llm:
        _test_llm.invoke("hi")
        _llm_available = True
except Exception as e:
    _llm_skip_reason = f"LLM 不可用: {e}"

skip_no_llm = pytest.mark.skipif(
    not _llm_available,
    reason=_llm_skip_reason or "LLM 不可用",
)


# ---------------------------------------------------------------------------
# Story 4.2.1: 子图检索集成测试
# ---------------------------------------------------------------------------

@skip_no_neo4j
class TestSubgraphRetrieval:
    """验证子图检索能正确查询 Neo4j。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.retriever = SubgraphRetriever()

    def test_retrieve_disease_neighbors(self):
        """检索疾病节点的邻居子图。"""
        result = self.retriever.retrieve({"disease": ["百日咳"]})
        assert result["stats"]["total_nodes"] > 0, "应有至少一个节点"
        assert result["stats"]["total_edges"] > 0, "应有至少一条边"

    def test_retrieve_multi_entity(self):
        """多实体检索。"""
        result = self.retriever.retrieve({
            "disease": ["百日咳"],
            "symptom": ["咳嗽"],
        })
        assert result["stats"]["total_nodes"] > 0

    def test_no_drug_node_in_subgraph(self):
        """子图中不应包含 Drug 节点。"""
        result = self.retriever.retrieve({"disease": ["百日咳"]})
        labels = {n["label"] for n in result["nodes"]}
        assert "Drug" not in labels, "子图不应包含 Drug 节点"


@skip_no_neo4j
class TestContextBuilder:
    """验证上下文组装。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.retriever = SubgraphRetriever()
        self.builder = ContextBuilder()

    def test_build_context_from_subgraph(self):
        """从子图组装上下文文本。"""
        subgraph = self.retriever.retrieve({"disease": ["百日咳"]})
        result = self.builder.build(subgraph)
        assert len(result["context_text"]) > 0
        assert result["char_count"] > 0

    def test_no_drug_rels_in_context(self):
        """上下文文本不包含药品关系标签。"""
        subgraph = self.retriever.retrieve({"disease": ["百日咳"]})
        result = self.builder.build(subgraph)
        assert "常用药" not in result["context_text"]
        assert "推荐药" not in result["context_text"]
        assert "生产药品" not in result["context_text"]


# ---------------------------------------------------------------------------
# Story 4.2.2: 药品实体不再被抽取
# ---------------------------------------------------------------------------

class TestDrugEntityNotExtracted:
    """验证药品实体不再被 LLM 抽取。"""

    def test_drug_not_in_valid_types(self):
        """_VALID_ENTITY_TYPES 不包含 drug。"""
        assert "drug" not in _VALID_ENTITY_TYPES

    def test_drug_not_in_extract_prompt(self):
        """ENTITY_EXTRACT_PROMPT 不包含 drug。"""
        assert "- drug:" not in ENTITY_EXTRACT_PROMPT

    def test_no_drug_in_rel_labels(self):
        """REL_LABELS 不包含药品关系。"""
        assert "common_drug" not in REL_LABELS
        assert "recommand_drug" not in REL_LABELS
        assert "drugs_of" not in REL_LABELS


@skip_no_neo4j
@skip_no_llm
class TestGraphRAGFullChain:
    """端到端验证：实体抽取 → 检索 → 上下文 → 生成。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.llm = create_llm()
        self.extractor = EntityExtractor(llm=self.llm)
        self.retriever = SubgraphRetriever()
        self.builder = ContextBuilder()
        self.generator = GraphRAGGenerator(llm=self.llm)

    def test_extract_disease_entity(self):
        """LLM 应正确抽取疾病实体。"""
        entities = self.extractor.extract("百日咳有什么症状")
        assert entities is not None
        types = {e["type"] for e in entities}
        assert "disease" in types, f"应抽取到 disease 类型实体，实际: {entities}"

    def test_drug_question_not_extract_drug_type(self):
        """药品类问题不应返回 drug 类型实体。"""
        entities = self.extractor.extract("阿莫西林能治什么病")
        if entities:
            types = {e["type"] for e in entities}
            assert "drug" not in types, f"不应抽取 drug 类型，实际: {entities}"

    def test_full_chain_disease_query(self):
        """完整链路：实体抽取 → 检索 → 上下文 → 生成。"""
        entities = self.extractor.extract("百日咳怎么治疗")
        assert entities is not None and len(entities) > 0

        from backend.domain.kbqa.entity_normalizer import EntityNormalizer
        normalizer = EntityNormalizer()
        normalized = normalizer.normalize(entities)
        entity_dict = normalized["entity_dict"]
        assert len(entity_dict) > 0

        subgraph = self.retriever.retrieve(entity_dict)
        assert subgraph["stats"]["total_nodes"] > 0

        context = self.builder.build(subgraph)
        assert len(context["context_text"]) > 0

        gen_result = self.generator.generate("百日咳怎么治疗", context["context_text"])
        assert gen_result["answer"], "应生成非空回答"
