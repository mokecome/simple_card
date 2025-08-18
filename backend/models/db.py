from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool, QueuePool
from backend.core.config import settings

# 添加 Base 定義
Base = declarative_base()

# 優化數據庫連接池配置
if settings.DATABASE_URL.startswith('sqlite'):
    # SQLite 使用 StaticPool
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # SQLite 最佳池
    )
else:
    # 生產環境數據庫（PostgreSQL, MySQL）使用 QueuePool
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=20,          # 連接池大小
        max_overflow=40,       # 最大溢出連接數
        pool_pre_ping=True,    # 使用前驗證連接
        pool_recycle=3600,     # 每小時回收連接
        echo_pool=settings.DEBUG  # 調試模式下顯示池活動
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 