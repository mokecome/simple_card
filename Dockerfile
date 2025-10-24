# 多階段構建 - 第一階段：構建前端
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# 複製前端 package 文件並安裝依賴
COPY frontend/package*.json ./
RUN npm ci

# 複製前端源代碼並構建
COPY frontend/ ./
RUN npm run build

# 第二階段：Python 3.10 運行環境
FROM python:3.10-slim

# 設置環境變量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    # OpenCV 依賴
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    # 圖像處理依賴
    libxcb1 \
    libxdamage1 \
    libxfixes3 \
    # 其他工具
    ffmpeg \
    wget \
    curl \
    nginx \
    supervisor \
    lsof \
    && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /app

# 複製並安裝 Python 依賴
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# 複製後端代碼
COPY backend/ ./backend/
COPY main.py ./
COPY init_db.py ./
COPY .env ./

# 複製前端構建結果到 nginx 目錄
COPY --from=frontend-builder /app/frontend/build /usr/share/nginx/html

# 創建必要的目錄
RUN mkdir -p /app/cards \
    && mkdir -p /app/uploads \
    && mkdir -p /app/logs \
    && mkdir -p /var/log/supervisor \
    && mkdir -p /run/nginx

# 複製配置文件
COPY nginx.conf /etc/nginx/sites-available/default
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 初始化數據庫
RUN python init_db.py

# 設置權限
RUN chmod +x /usr/bin/supervisord

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# 暴露端口
EXPOSE 1002 8006

# 使用 supervisor 啟動所有服務
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]