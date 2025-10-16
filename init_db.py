#!/usr/bin/env python3
"""
數據庫初始化腳本
Initialize cards.db database with proper schema
"""
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.models.db import engine, Base
from backend.models.card import CardORM, CardTagORM
from backend.core.config import settings

def init_database():
    """初始化數據庫，創建所有表"""
    try:
        print(f"🗄️  正在初始化數據庫: {settings.DATABASE_URL}")
        
        # 創建所有表
        Base.metadata.create_all(bind=engine)
        
        print("✅ 數據庫初始化成功！")
        print("📋 已創建的表:")
        print(f"   - cards (名片數據表)")
        print(f"   - card_tags (名片標籤表)")
        print(f"📊 索引:")
        print(f"   - idx_name_company (姓名+公司複合索引)")
        print(f"   - idx_name_phone (姓名+手機複合索引)")
        print(f"   - idx_card_tag (名片+標籤複合索引)")
        print(f"   - idx_tag_type (標籤名稱+類型索引)")
        
        return True
        
    except Exception as e:
        print(f"❌ 數據庫初始化失敗: {str(e)}")
        return False

def check_database_status():
    """檢查數據庫狀態"""
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"🔍 數據庫狀態檢查:")
        print(f"   數據庫文件: {settings.DATABASE_URL}")
        print(f"   已存在的表: {tables}")
        
        if 'cards' in tables:
            # 檢查表結構
            columns = inspector.get_columns('cards')
            indexes = inspector.get_indexes('cards')
            
            print(f"📋 cards 表結構:")
            print(f"   欄位數量: {len(columns)}")
            print(f"   索引數量: {len(indexes)}")
            
            for idx in indexes:
                print(f"   - {idx['name']}: {idx['column_names']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 數據庫狀態檢查失敗: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 OCR 名片管理系統 - 數據庫初始化")
    print("=" * 50)
    
    # 檢查現有狀態
    check_database_status()
    
    print("\n" + "-" * 30)
    
    # 初始化數據庫
    success = init_database()
    
    if success:
        print("\n" + "-" * 30)
        # 再次檢查狀態確認
        check_database_status()
        print("\n✨ 數據庫已準備就緒，可以開始使用系統！")
    else:
        print("\n💥 初始化失敗，請檢查錯誤信息")
        sys.exit(1)