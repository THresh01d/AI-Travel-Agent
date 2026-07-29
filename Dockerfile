# ==========================================
# AI Travel Agent — Dockerfile
# ==========================================
# 分两步构建：
#   1. builder 阶段：安装依赖
#   2. 运行阶段：只放代码和依赖，镜像更小
# ==========================================

FROM python:3.12-slim AS builder

# 用国内镜像加速 pip 下载（国外服务器部署时去掉 -i 参数）
ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# 先复制依赖文件单独安装，这样改代码不需要重新装依赖（Docker 缓存优化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX}

# ==========================================
# 运行阶段
# ==========================================
FROM python:3.12-slim

WORKDIR /app

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制项目代码
COPY . .

# 告诉 Docker 这个容器监听 8000 端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
