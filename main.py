from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

from backend.api.v1 import card, ocr
from backend.core.config import *
from backend.core.middleware import ErrorHandlingMiddleware, LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時
    print_settings_summary()
    
    # 檢查環境配置
    issues = check_environment()
    if issues:
        logging.warning(f"發現配置問題: {', '.join(issues)}")
    
    # 初始化數據庫
    from backend.models.db import Base, engine
    Base.metadata.create_all(bind=engine)
    
    # 創建必要的目錄
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    logging.info("✅ 後端服務啟動完成")
    yield
    
    # 關閉時
    logging.info("🔄 後端服務正在關閉...")

# 創建 FastAPI 應用
app = FastAPI(
    title=APP_NAME,
    description="Business Card Scanning and Management Backend",
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan
)

# 添加統一錯誤處理中間件
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# 註冊路由
app.include_router(
    card.router,
    prefix=f"{API_V1_PREFIX}/cards",
    tags=["Business Card Management"]
)
app.include_router(
    ocr.router,
    prefix=f"{API_V1_PREFIX}/ocr",
    tags=["OCR"]
)

# 掛載靜態文件目錄
# 掛載 card_data 目錄（舊圖片）
if os.path.exists("card_data"):
    app.mount("/static/card_data", StaticFiles(directory="card_data"), name="card_data")

# 掛載 output/card_images 目錄（新上傳圖片）
if os.path.exists("output/card_images"):
    app.mount("/static/uploads", StaticFiles(directory="output/card_images"), name="uploads")

# 健康檢查端點
@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
        "environment": ENV
    }

# 配置資訊端點 (僅開發環境)
@app.get("/config")
async def get_config():
    """獲取配置資訊 (僅開發環境)"""
    if not is_development():
        return {"error": "此端點僅在開發環境可用"}
    
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "environment": ENV,
        "debug": DEBUG,
        "api_prefix": API_V1_PREFIX,
        "upload_dir": UPLOAD_DIR,
        "log_level": LOG_LEVEL
    }

if __name__ == "__main__":
    import uvicorn
    
    # 配置日誌
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 啟動服務器
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        workers=WORKERS,
        reload=is_development(),
        log_level=LOG_LEVEL.lower()
    ) 