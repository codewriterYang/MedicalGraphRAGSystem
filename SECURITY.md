# 安全策略

## 报告漏洞

如发现安全漏洞，请通过以下方式私下报告：

1. **Email**：发送至项目维护者邮箱（参见仓库首页）
2. **不要**在公开 Issue 中报告安全漏洞

我们会在 48 小时内确认收到报告，并在修复后公开披露。

## 安全最佳实践

### API 密钥管理

- **绝对不要**将 `.env` 文件提交到 Git 仓库
- 使用 `.env.example` 作为模板文件
- 定期轮换 API 密钥
- 生产环境使用密钥管理服务（如 HashiCorp Vault、AWS Secrets Manager）

### Neo4j 安全

- 生产环境修改默认密码（`NEO4J_PASSWORD`）
- 限制 Neo4j 网络访问（仅在容器内网暴露 7687 端口）
- 定期备份图谱数据

### CORS 配置

- 生产环境通过 `ALLOWED_ORIGINS` 环境变量限制前端域名
- 示例：`ALLOWED_ORIGINS=https://your-domain.com`

### LLM 安全

- 不在日志中记录用户输入（已通过 `qa_engine/__init__.py` 抑制旧模块日志）
- 不在 `debug` 返回数据中泄露完整 Prompt

## 依赖安全

定期检查依赖漏洞：

```bash
pip-audit
npm audit
```

## 数据隐私

- `data/medical.json` 为公开医疗数据，仅供学习研究
- 用户问答内容不持久化存储（MemorySaver 仅内存级别）
- 请勿在此项目上处理真实患者数据

## 支持的版本

| 版本 | 支持状态 |
|------|----------|
| 1.0.x | 当前支持 |

## 致谢

感谢所有通过私下渠道报告安全问题的贡献者。
