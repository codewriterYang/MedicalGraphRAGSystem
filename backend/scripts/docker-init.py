#!/usr/bin/env python3
"""Docker 启动时自动导入图谱数据到 Neo4j。

Neo4j 容器健康检查通过后，docker-compose 自动执行本脚本。
等待 Neo4j 完全就绪 → 清空旧数据 → 导入 medical.json。
"""
import logging
import sys
import time
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("docker-init")

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def wait_for_neo4j(max_retries: int = 20, delay: int = 3) -> bool:
    """等待 Neo4j 完全就绪（可执行写操作）。"""
    from py2neo import Graph
    import os

    uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "neo4j")

    log.info("等待 Neo4j 就绪 (%s)...", uri)
    for i in range(max_retries):
        try:
            graph = Graph(uri, auth=(user, password))
            graph.run("RETURN 1").data()
            log.info("Neo4j 连接成功！")
            return True
        except Exception as e:
            log.info("第 %d/%d 次尝试失败: %s", i + 1, max_retries, str(e)[:80])
            time.sleep(delay)
    return False


def import_data():
    """导入图谱数据。"""
    from backend.domain.knowledge_graph.data_loader import DataLoader
    from backend.domain.knowledge_graph.graph_builder import GraphBuilder
    from backend.domain.knowledge_graph.config import DATA_PATH

    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "neo4j")

    log.info("=" * 50)
    log.info("开始导入图谱数据")
    log.info("数据文件: %s", DATA_PATH)
    log.info("Neo4j: %s (用户: %s)", neo4j_uri, neo4j_user)
    log.info("=" * 50)

    if not Path(DATA_PATH).exists():
        log.error("数据文件不存在: %s", DATA_PATH)
        sys.exit(1)

    # 加载数据
    loader = DataLoader(DATA_PATH)
    nodes, rels, disease_infos = loader.load()

    log.info("数据加载完成: %d 疾病, %d 节点类型, %d 关系类型",
             len(disease_infos), len(nodes), len(rels))

    # 创建图构建器并清空旧数据
    builder = GraphBuilder(neo4j_uri, neo4j_user, neo4j_password)
    builder.clear_all()
    log.info("已清空旧图谱数据")

    # 第一步：创建节点
    log.info("第一步：创建节点...")
    builder.create_disease_nodes(disease_infos)
    for label in ["Food", "Check", "Department", "Symptom"]:
        if nodes.get(label):
            builder.create_simple_nodes(label, nodes[label])
    log.info("节点创建完成")

    # 第二步：创建关系
    log.info("第二步：创建关系...")
    for rel_type, triples in rels.items():
        if triples:
            builder.create_relationships(rel_type, triples)
    log.info("关系创建完成")

    # 统计
    node_count = builder.graph.run("MATCH (n) RETURN count(n) AS c").data()[0]["c"]
    rel_count = builder.graph.run("MATCH ()-[r]->() RETURN count(r) AS c").data()[0]["c"]
    log.info("=" * 50)
    log.info("图谱导入完成！节点: %d, 关系: %d", node_count, rel_count)
    log.info("=" * 50)


def main():
    # 等待 Neo4j（docker-compose healthcheck 已确保服务启动，这里额外保险）
    if not wait_for_neo4j():
        log.error("Neo4j 连接超时，放弃初始化")
        sys.exit(1)

    # 检查是否已导入过（跳过重复导入）
    try:
        from py2neo import Graph
        uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "neo4j")
        graph = Graph(uri, auth=(user, password))
        count = graph.run("MATCH (n) RETURN count(n) AS c").data()[0]["c"]
        if count > 0:
            log.info("图谱已存在 (%d 个节点)，跳过导入", count)
            log.info("如需重新导入，请执行: docker compose down -v && docker compose up -d")
            log.info("=" * 50)
            return
    except Exception:
        pass  # 可能尚未就绪，继续导入

    import_data()


if __name__ == "__main__":
    main()
