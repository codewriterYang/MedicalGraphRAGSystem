# ===========================================================================
# React 前端镜像（多阶段构建）
# 国内镜像源：DaoCloud（基础镜像）+ npmmirror（npm）
# ===========================================================================

# ---- 构建阶段 ----
FROM docker.m.daocloud.io/library/node:20-alpine AS builder

# npm 源切换为 npmmirror 淘宝镜像
RUN npm config set registry https://registry.npmmirror.com

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- 运行阶段 ----
FROM docker.m.daocloud.io/library/nginx:alpine

# 复制 static 产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置（反向代理 /api → 后端）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
