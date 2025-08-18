#!/bin/bash
FRONTEND_PORT=1002
BACKEND_PORT=8006


release_port() {
    local port=$1
    local pid=$(lsof -t -i:$port)
    if [ -n "$pid" ]; then
        echo "[INFO] 正在终止占用端口 $port 的进程，PID: $pid"
        kill -9 $pid
        sleep 1 
    fi
}


release_port $FRONTEND_PORT
release_port $BACKEND_PORT

cd "$(dirname "$0")"


rm -f backend/nohup_backend.log
rm -f frontend/nohup_frontend.log

echo "[INFO] 启动 FastAPI backend..."
nohup python main.py > backend/nohup_backend.log 2>&1 &
BACKEND_PID=$!
echo "[INFO] FastAPI 进程 PID $BACKEND_PID，日志文件: backend/nohup_backend.log"

cd frontend

echo "[INFO] 启动 React frontend..."
nohup npm start > nohup_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "[INFO] React frontend 进程 PID $FRONTEND_PID，日志文件: frontend/nohup_frontend.log"

cd ..
echo "[INFO] 前后端已在后台启动。"
echo "[INFO] 前端：http://<你的IP>:$FRONTEND_PORT"
echo "[INFO] 后端：http://<你的IP>:$BACKEND_PORT"