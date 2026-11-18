# 后端镜像。默认使用容器内 /app/data 下的 SQLite；
# 接 MySQL 时通过 DATABASE_URL 环境变量注入连接串。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先拷依赖清单再装，改代码时不会重装依赖
COPY requirements.txt .

# 国内网络直连 PyPI 经常超时/断开，默认走清华镜像。
# 需要走官方源时：docker build --build-arg PIP_INDEX_URL=https://pypi.org/simple -t ...
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir -i "$PIP_INDEX_URL" -r requirements.txt

COPY app ./app

EXPOSE 8000

# --host 0.0.0.0 不能少，否则容器外访问不到
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
