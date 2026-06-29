from sqlalchemy import create_engine, event
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

# SQLite: 開 WAL 讓讀寫並行、降低 fsync 成本（查名片以讀為主，收益明顯）
if settings.DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 