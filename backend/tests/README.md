# 测试目录说明

## 目录结构

```
tests/
├── integration/          # 集成测试（多模块协作）
│   ├── test_graph_connection.py       # Neo4j 图谱连接测试
│   ├── test_fallback_strategy.py      # 三级降级策略测试
│   ├── test_cypher_optimization.py    # Cypher 查询优化测试
│   ├── test_error_handling.py         # 错误处理测试
│   ├── test_langsmith_tracing.py      # LangSmith 追踪测试
│   ├── test_graphrag_integration.py   # GraphRAG 集成测试
│   ├── test_multi_turn.py            # 多轮对话测试
│   ├── test_server_basic_qa.py        # 后端问答集成测试
│   ├── test_streaming_output.py       # 流式输出测试
│   ├── test_modular_refactoring.py    # 模块化重构验证
│   └── test_final_refactoring.py      # 最终重构验证
├── unit/                 # 单元测试（单个模块）
│   ├── test_entity_normalizer.py      # 实体归一化器测试
│   └── test_cypher_generator.py       # Cypher 生成器测试
└── README.md             # 本文件
```

## 测试类型说明

### 集成测试 (integration/)
- 测试多个模块协同工作的场景
- 测试完整的业务流程
- 需要外部依赖（如 Neo4j 数据库）

### 单元测试 (unit/)
- 测试单个模块的功能
- 验证核心算法和逻辑
- 通常不需要外部依赖

## 运行测试

```bash
# 运行单元测试
pytest backend/tests/unit/ -v

# 运行集成测试
pytest backend/tests/integration/ -v

# 运行所有测试
pytest backend/tests/ -v

# 带覆盖率报告
pytest backend/tests/ --cov=backend --cov-report=term
```

## 测试文件命名规范

```
test_<模块名>_<功能>.py

示例：
- test_graph_connection.py       # 图谱连接测试
- test_fallback_strategy.py      # 降级策略测试
- test_entity_normalizer.py      # 实体归一化器测试
- test_graphrag_integration.py   # GraphRAG 集成测试
```

## 测试编写规范

1. 每个测试文件对应一个测试主题
2. 使用清晰的测试用例命名
3. 输出明确的测试结果（[OK]/[FAIL]/[ERROR]）
4. 包含测试统计信息
