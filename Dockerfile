# 后端 Dockerfile — FastAPI 应用
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（MySQL 客户端库），合并 RUN 减少层数
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 安装 Python 依赖（利用 Docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY run.py .

# 创建非 root 用户运行应用
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令：幂等建表（create_all，不重置数据）+ uvicorn
# 说明：本项目库表由 ORM create_all 管理（与本地开发一致）；种子数据按 README 手动执行 docker-init
CMD sh -c "python -c 'from app.database import Base, sync_engine; Base.metadata.create_all(bind=sync_engine)' && uvicorn app.main:app --host 0.0.0.0 --port 8000"
