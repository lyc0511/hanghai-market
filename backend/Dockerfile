# 航海集市后端镜像：Python 3.14 + FastAPI
# 构建：在项目根目录执行 docker compose build backend（一般不单独构建，见 docker-compose.yml）

# 以官方 Python 镜像为底子；slim 是精简版，体积小
FROM python:3.14-slim

# 国内服务器访问 PyPI 官方很慢，用腾讯云的 pip 镜像站（换别家云时改这个参数即可）
ARG PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /app

# 先只复制依赖清单并安装：依赖没变时这一层直接用缓存，只改代码时重新构建很快
COPY requirements.txt .
RUN pip install -r requirements.txt

# 再复制运行需要的代码（测试、虚拟环境、.env 都不进镜像，见 .dockerignore）
COPY app ./app
COPY scripts ./scripts
COPY sql ./sql

# 用普通用户运行，不用 root；uploads 目录由数据卷挂载，这里先建好并交给该用户
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/uploads \
    && chown appuser:appuser /app/uploads
USER appuser

EXPOSE 8000

# --proxy-headers：信任 Nginx 传来的 X-Forwarded-For，限流才能按访客真实 IP 计算
#   （后端不对外开放端口，只有同一 Docker 网络里的 Nginx 能访问它，所以信任它是安全的）
# --workers 1：小航的单人限流计数在进程内存里，多进程会让限额翻倍；内部测试 1 个进程足够
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
