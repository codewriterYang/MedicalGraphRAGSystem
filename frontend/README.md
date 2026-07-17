# Web 前端

React 19 + TypeScript + Vite 构建的医疗知识图谱智能问答前端。

---

## 技术栈

| 依赖 | 版本 | 用途 |
|---|---|---|
| React | ^19.2 | UI 框架 |
| TypeScript | ~5.9 | 类型检查 |
| Vite | ^8.0 | 构建工具 |
| Tailwind CSS | ^4.2 | 原子化 CSS |
| shadcn/ui | ^4.1 | UI 组件库 |
| react-force-graph-2d | ^1.29 | 力导向知识图谱可视化 |

---

## 快速开始

```bash
cd frontend
npm install
npm run dev
```

开发服务器运行在 `http://localhost:5173`，API 请求自动代理到 `http://localhost:8000`。

---

## 项目结构

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # SSE 流式 + 邻居查询 API 客户端
│   ├── components/
│   │   ├── UnifiedChatPanel.tsx # 统一聊天面板（单入口）
│   │   ├── DebugPanel.tsx       # 模板检索调试面板
│   │   ├── GraphRAGDebugPanel.tsx # GraphRAG 调试面板
│   │   ├── GraphPanel.tsx       # 力导向知识图谱可视化
│   │   └── ui/                  # shadcn/ui 基础组件
│   ├── types/
│   │   └── index.ts             # TypeScript 类型定义
│   ├── utils/
│   │   └── debugNormalize.ts    # 调试信息字段映射
│   └── App.tsx                  # 根组件
├── public/                      # 静态资源
├── package.json
├── tsconfig.json
├── vite.config.ts               # Vite 配置（含 API 代理）
└── nginx.conf                   # 生产部署 Nginx 配置
```

---

## 生产构建

```bash
npm run build
```

产物输出到 `dist/`，由 FastAPI 后端 `backend/api/app.py` 自动挂载。

---

## 开发说明

- **流式协议**：前端监听 SSE `delta` / `done` / `error` 事件
- **调试面板**：`onDone` 中解析 `debug` / `graph_data` / `mode`，按 `mode` 切换 DebugPanel / GraphRAGDebugPanel
- **图谱交互**：点击节点触发 `/api/graph/neighbors/{name}` 加载邻居
- **多轮对话**：通过 `session_id` 维持上下文，由 `make_thread_config()` 管理

详见项目根目录 [README.md](../README.md) 和 [架构文档](../docs/02_ARCHITECTURE.md)。
