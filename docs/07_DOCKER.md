# Docker 运维手册

## 架构概览

```
docker compose up -d
        │
        ├── medgraph-neo4j   (Neo4j 5.x 图数据库)
        │       └── bolt://neo4j:7687  (容器内)
        │       └── http://localhost:7474 (浏览器)
        │
        ├── medgraph-init    (一次性图谱导入，完成后 exit 0)
        │
        ├── medgraph-server  (FastAPI 后端 :8000)
        │       └── http://localhost:8000/docs (Swagger)
        │
        └── medgraph-web     (Nginx + React 前端 :8000)
                └── http://localhost:8000
```

---

## 快速启动

```bash
# 1. 配置 API Key
cp .env.example .env
# 编辑 .env：填入 SiliconFlow API Key 及 Neo4j 密码

# 2. 启动（首次约 5-10 分钟）
docker compose up -d

# 3. 查看启动进度
docker compose logs -f

# 4. 浏览器打开
# http://localhost:8000
```

> 首次启动 `init-kg` 需导入 45MB 数据（4.4 万节点 / 29 万关系），请耐心等待。
> 看到 `图谱导入完成` 后即可使用。后续重启秒级启动。

---

## 日常运维

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 停止 + 删除数据卷（图谱数据将丢失）
docker compose down -v

# 重启所有服务
docker compose restart

# 重启单个服务
docker compose restart server
docker compose restart web
docker compose restart neo4j
```

---

## 状态查看

```bash
# 查看所有容器状态
docker compose ps

# 正常状态应如下：
#   medgraph-neo4j    Up (healthy)
#   medgraph-init     Exited (0)        ← 一次性任务，正常
#   medgraph-server   Up
#   medgraph-web      Up

# 查看实时日志
docker compose logs -f

# 查看指定服务日志
docker compose logs -f server
docker compose logs -f web
docker compose logs -f neo4j

# 查看最近 N 行日志
docker compose logs --tail=100
```

---

## 重新构建

修改源代码后需重新构建对应镜像：

```bash
# 无缓存完整重建（修改 Dockerfile 时使用）
docker compose build --no-cache

# 只重建指定服务（常用）
docker compose build --no-cache server
docker compose build --no-cache web
docker compose build --no-cache init-kg

# 重建并启动
docker compose up -d --build
```

---

## 数据管理

### 重新导入图谱

```bash
# 方式一：完全重置（推荐）
docker compose down -v
docker compose up -d

# 方式二：仅重新导入（保留 Neo4j 数据卷）
docker compose run --rm init-kg
```

### 访问 Neo4j 浏览器

浏览器打开 `http://localhost:7474`

| 参数 | 值 |
|---|---|
| URL | `bolt://localhost:7687` |
| 用户 | `neo4j` |
| 密码 | `.env` 中 `NEO4J_PASSWORD` |

### 备份图谱（脚本导出）

```bash
docker exec medgraph-neo4j neo4j-admin database dump neo4j --to-path=/backups
docker cp medgraph-neo4j:/backups ./backups
```

---

## 镜像源说明

项目使用国内镜像源，无需配置代理：

| 组件 | 镜像源 |
|---|---|
| Docker 基础镜像 | `docker.m.daocloud.io` |
| apt (Debian) | `mirrors.ustc.edu.cn` |
| pip (Python) | `pypi.tuna.tsinghua.edu.cn` |
| npm (Node.js) | `registry.npmmirror.com` |

---

## 常见问题

### 1. init-kg 一直 Waiting 或 Exit 1

```bash
# 查看错误详情
docker compose logs init-kg
```

常见原因：
- Neo4j 未就绪 → 等待 Healthy 状态后自动重试
- 导入报错 → 检查日志定位，修复后 `docker compose build --no-cache init-kg`

### 2. HTTP 500 或 Neo4j 连接失败

```bash
# 检查 Neo4j 状态
docker compose ps neo4j

# 重启后端
docker compose restart server
```

### 3. 前端无法访问

```bash
# 确认 web 容器状态
docker compose ps web

# 查看 nginx 日志
docker compose logs web
```

---

## 清理

```bash
# 清理停止的容器、未使用的网络和镜像
docker system prune -a

# 只清理停止的容器
docker container prune

# 清理所有 Docker 数据（慎用，影响其他项目）
docker system prune -a --volumes
```
