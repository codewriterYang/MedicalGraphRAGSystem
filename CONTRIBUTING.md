# 贡献指南

感谢你对 MedicalGraphRAGSystem 的关注！

## 开发流程

### 分支策略

| 分支 | 用途 |
|------|------|
| `main` | 生产就绪代码，受保护 |
| `develop` | 集成分支 |
| `feat/*` | 新功能开发 |
| `fix/*` | Bug 修复 |
| `docs/*` | 文档更新 |

### 提交流程

1. 从 `develop` 创建功能分支
2. 遵循 [.claude.md](.claude.md) 中的代码规范
3. 使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式提交
4. 确保通过本地测试：`pytest backend/tests/unit/`
5. 提交 Pull Request 到 `develop` 分支

### Commit 格式

```
<type>(<scope>): <subject>

- type: feat | fix | docs | style | refactor | test | chore
- scope: 模块名（如 qa_engine、api、frontend、docker 等）
```

示例：

```
feat(qa_engine): 支持多模型动态切换
fix(api): 修复 SSE 流式连接泄漏
docs(readme): 更新 Docker 部署文档
```

## 代码规范

详见 [.claude.md](.claude.md)，核心要点：

- Python 3.10+，类型注解，Google 风格 docstring
- TypeScript 严格模式，函数组件 + Hooks
- 禁止 `from langchain import ...`
- 敏感配置通过环境变量注入

## 测试

```bash
# 运行单元测试
pytest backend/tests/unit/ -v

# 运行所有测试
pytest backend/tests/ -v

# 覆盖率报告
pytest backend/tests/ --cov=backend --cov-report=term
```

## Issue 模板

提交 Issue 时请包含：
- 运行环境（Python 版本、Neo4j 版本、LLM 提供商）
- 复现步骤
- 预期行为 vs 实际行为
- 相关日志或截图

## 许可

本项目基于 MIT 许可证，贡献即视为同意代码在该许可证下发布。
