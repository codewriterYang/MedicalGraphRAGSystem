#!/usr/bin/env python3
# coding: utf-8
"""
知识图谱连接与数据统计测试

测试内容：
1. 验证 Neo4j 连接是否成功
2. 统计图谱节点和关系数量
3. 查询示例数据验证图谱内容
"""
from py2neo import Graph
import os

def test_neo4j_connection():
    """测试 Neo4j 连接"""
    print("[TEST] 测试 Neo4j 连接...")
    try:
        # 从环境变量获取连接信息
        uri = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "neo4j")
        
        graph = Graph(uri, auth=(user, password))
        
        # 测试查询
        result = graph.run("MATCH (n) RETURN count(n) AS node_count").data()
        node_count = result[0]["node_count"]
        print(f"[OK] Neo4j 连接成功！节点总数: {node_count:,}")
        return graph
    except Exception as e:
        print(f"[FAIL] Neo4j 连接失败: {e}")
        return None

def test_graph_statistics():
    """统计图谱数据"""
    import pytest
    graph = test_neo4j_connection()
    if graph is None:
        pytest.skip("Neo4j 未连接，跳过统计测试")
    
    # 节点类型统计
    result = graph.run("CALL db.labels() YIELD label RETURN label").data()
    labels = [r["label"] for r in result]
    
    print(f"节点类型 ({len(labels)} 种):")
    total_nodes = 0
    for label in labels:
        count = graph.run(f"MATCH (n:{label}) RETURN count(n) AS c").data()[0]["c"]
        total_nodes += count
        print(f"  • {label}: {count:,} 个")
    
    # 关系类型统计
    result = graph.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType").data()
    rel_types = [r["relationshipType"] for r in result]
    
    print(f"\n关系类型 ({len(rel_types)} 种):")
    total_rels = 0
    for rel_type in rel_types[:5]:
        count = graph.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c").data()[0]["c"]
        total_rels += count
        print(f"  • {rel_type}: {count:,} 条")
    
    print(f"\n图谱总规模: {total_nodes:,} 个节点, {total_rels:,}+ 条关系")

def test_sample_queries():
    """测试示例查询"""
    import pytest
    graph = test_neo4j_connection()
    if graph is None:
        pytest.skip("Neo4j 未连接，跳过示例查询测试")
    
    # 测试糖尿病的症状
    print("\n示例1: 糖尿病的症状")
    result = graph.run("""
        MATCH (d:Disease)-[:has_symptom]->(s:Symptom) 
        WHERE d.name = '糖尿病' 
        RETURN s.name AS symptom LIMIT 5
    """).data()
    for r in result:
        print(f"  • {r['symptom']}")
    
    # 测试高血压的药物
    print("\n示例2: 高血压常用药物")
    result = graph.run("""
        MATCH (d:Disease)-[:common_drug]->(dr:Drug) 
        WHERE d.name = '高血压' 
        RETURN dr.name AS drug LIMIT 5
    """).data()
    for r in result:
        print(f"  • {r['drug']}")

if __name__ == "__main__":
    print("=" * 60)
    print("        Neo4j 图谱连接测试")
    print("=" * 60)
    
    graph = test_neo4j_connection()
    
    if graph:
        test_graph_statistics(graph)
        test_sample_queries(graph)
        
        print("\n" + "=" * 60)
        print("        所有测试完成")
        print("=" * 60)