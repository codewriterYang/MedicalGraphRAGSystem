# ===========================================================================
# FastAPI 后端镜像
# 国内镜像源：DaoCloud（基础镜像）+ 中科大（apt）+ 清华（pip）
# ===========================================================================
FROM docker.m.daocloud.io/library/python:3.11-slim

WORKDIR /app

# apt 源切换为中科大镜像
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（pyahocorasick 需要 gcc）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# pip 源切换为清华镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Python 依赖（利用 Docker 缓存层）
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 复制项目代码
COPY . .

# 暴露端口（uvicorn 内部端口，实际由 docker-compose 网络管理）
EXPOSE 8000

CMD ["python", "-m", "backend.api.app"]
