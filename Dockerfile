# 后端 Dockerfile — FastAPI 应用
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（MySQL 客户端库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# 暴露端口
EXPOSE 8000

# 启动命令：运行迁移 + uvicorn
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
