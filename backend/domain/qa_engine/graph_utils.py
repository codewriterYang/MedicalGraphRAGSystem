#!/usr/bin/env python3
# coding: utf-8
"""
图谱数据构建工具。

将模板路径 raw_results 或 GraphRAG subgraph 转为前端统一的 graph_data 结构。
"""
from __future__ import annotations

from typing import Any

# 实体类型 → Neo4j 标签（用于可视化配色）
_ENTITY_LABEL_MAP: dict[str, str] = {
    "disease": "Disease",
    "symptom": "Symptom",
    "food": "Food",
    "check": "Check",
    "department": "Department",
}


def build_graph_data_from_raw_results(
    raw_results: list[dict],
    entity_dict: dict[str, list[str]] | None = None,
    max_nodes: int = 80,
) -> dict[str, list[dict]]:
    """
    从模板路径 Neo4j 查询结果构建 graph_data。

    常见行字段：m.name（中心实体）、n.name（关联实体）、r.name（关系类型）。
    """
    nodes: dict[str, str] = {}
    edges: list[dict] = []
    seen_edges: set[tuple[str, str, str]] = set()

    if entity_dict:
        for etype, names in entity_dict.items():
            label = _ENTITY_LABEL_MAP.get(etype, "Entity")
            for name in names:
                if name:
                    nodes[name] = label

    for group in raw_results or []:
        for row in group.get("answers") or []:
            if not isinstance(row, dict):
                continue
            m_name = row.get("m.name") or row.get("m_name")
            n_name = row.get("n.name") or row.get("n_name")
            r_name = row.get("r.name") or row.get("r_type") or "相关"

            if m_name:
                nodes.setdefault(str(m_name), "Disease")
            if n_name:
                nodes.setdefault(str(n_name), _infer_neighbor_label(row, str(m_name)))
            if m_name and n_name:
                key = (str(m_name), str(n_name), str(r_name))
                if key not in seen_edges:
                    edges.append({
                        "source": key[0],
                        "target": key[1],
                        "label": key[2],
                    })
                    seen_edges.add(key)
            elif n_name and not m_name:
                nodes.setdefault(str(n_name), "Symptom")

            if len(nodes) >= max_nodes:
                break
        if len(nodes) >= max_nodes:
            break

    return {
        "nodes": [{"id": nid, "label": lbl} for nid, lbl in nodes.items()],
        "edges": edges[: max_nodes * 2],
    }


def build_graph_data_from_subgraph(subgraph: dict | None) -> dict[str, list[dict]]:
    """从 GraphRAG 子图结构构建 graph_data。"""
    if not subgraph or not isinstance(subgraph, dict):
        return {"nodes": [], "edges": []}
    nodes = subgraph.get("nodes") or []
    edges = subgraph.get("edges") or []
    return {
        "nodes": [
            {"id": n.get("name", n.get("id", "")), "label": n.get("label", "Entity")}
            for n in nodes
            if n.get("name") or n.get("id")
        ],
        "edges": [
            {
                "source": e.get("source", ""),
                "target": e.get("target", ""),
                "label": e.get("relationship", e.get("label", "")),
            }
            for e in edges
            if e.get("source") and e.get("target")
        ],
    }


def resolve_graph_data_from_state(state: dict[str, Any]) -> dict[str, list[dict]]:
    """从工作流最终 state 解析 graph_data（优先显式字段，再子图/查询结果）。"""
    if state.get("graph_data") and state["graph_data"].get("nodes"):
        return state["graph_data"]

    route = state.get("route", "")
    if route == "graphrag":
        gd = build_graph_data_from_subgraph(state.get("subgraph"))
        if gd["nodes"]:
            return gd

    normalized = state.get("normalized_entities") or {}
    entity_dict = normalized.get("entity_dict", {}) if isinstance(normalized, dict) else {}
    return build_graph_data_from_raw_results(state.get("raw_results") or [], entity_dict)


def _infer_neighbor_label(row: dict, center: str | None) -> str:
    """根据返回字段粗略推断邻居节点标签。"""
    for key, label in (
        ("n.label", None),
        ("m.label", None),
    ):
        if row.get(key):
            return str(row[key])
    if row.get("n.desc") or row.get("m.cause"):
        return "Disease"
    return "Entity"
