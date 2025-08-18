#!/usr/bin/env python3
"""
配置檢查工具
用於驗證環境變數和配置是否正確設置
"""

import os
import sys
import json
from pathlib import Path

# 添加後端路徑到 Python 路徑
sys.path.append(str(Path(__file__).parent.parent))

try:
    from backend.core.config import *
    from backend.core.response import ResponseHandler
except ImportError as e:
    print(f"❌ 無法導入後端模組: {e}")
    print("請確保您在正確的目錄中運行此腳本，並且已安裝所有依賴")
    sys.exit(1)

def check_file_permissions():
    """檢查文件權限"""
    issues = []
    
    # 檢查上傳目錄
    upload_dir = Path(UPLOAD_DIR)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        # 測試寫入權限
        test_file = upload_dir / "test_permission.tmp"
        test_file.write_text("test")
        test_file.unlink()
    except PermissionError:
        issues.append(f"沒有上傳目錄的寫入權限: {upload_dir}")
    except Exception as e:
        issues.append(f"上傳目錄權限檢查失敗: {e}")
    
    # 檢查序號配置文件目錄
    config_dir = Path(SERIAL_CONFIG_FILE).parent
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        issues.append(f"沒有配置目錄的寫入權限: {config_dir}")
    except Exception as e:
        issues.append(f"配置目錄權限檢查失敗: {e}")
    
    return issues

def check_database_connection():
    """檢查數據庫連接"""
    try:
        from backend.models.db import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return []
    except Exception as e:
        return [f"數據庫連接失敗: {e}"]

def check_required_files():
    """檢查必要文件是否存在"""
    issues = []
    
    # 檢查 .env 文件
    env_file = Path(".env")
    if not env_file.exists():
        issues.append("缺少 .env 文件，請從 .env.example 複製並配置")
    
    return issues

def generate_config_report():
    """生成配置報告"""
    report = {
        "app_info": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "environment": ENV,
            "debug": DEBUG
        },
        "server": {
            "host": HOST,
            "port": PORT,
            "workers": WORKERS
        },
        "database": {
            "url": DATABASE_URL,
            "echo": DB_ECHO
        },
        "api": {
            "prefix": API_V1_PREFIX,
            "cors_origins": CORS_ORIGINS
        },
        "upload": {
            "directory": UPLOAD_DIR,
            "max_file_size": MAX_FILE_SIZE,
            "allowed_types": ALLOWED_FILE_TYPES
        },
        "ocr": {
            "api_url": OCR_API_URL,
            "timeout": OCR_TIMEOUT,
            "api_key": "***" if OCR_API_KEY != "YOUR_API_KEY" else "未設置"
        },
        "logging": {
            "level": LOG_LEVEL,
            "file": LOG_FILE
        }
    }
    
    return report

def main():
    """主函數"""
    print("🔍 OCR 名片管理系統 - 配置檢查工具")
    print("=" * 50)
    
    # 檢查各項配置
    all_issues = []
    
    print("\n📋 基本配置檢查...")
    if check_config():
        print("  ✅ 基本配置正常")
    else:
        print("  ⚠️ 發現配置問題，請檢查上方輸出")
    
    print("\n📁 文件權限檢查...")
    file_issues = check_file_permissions()
    if file_issues:
        all_issues.extend(file_issues)
        for issue in file_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ 文件權限正常")
    
    print("\n💾 數據庫連接檢查...")
    db_issues = check_database_connection()
    if db_issues:
        all_issues.extend(db_issues)
        for issue in db_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ 數據庫連接正常")
    
    print("\n📄 必要文件檢查...")
    file_check_issues = check_required_files()
    if file_check_issues:
        all_issues.extend(file_check_issues)
        for issue in file_check_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ 必要文件齊全")
    
    # 生成配置報告
    print("\n📊 配置報告...")
    report = generate_config_report()
    
    # 保存報告到文件
    report_file = Path("config_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  📁 配置報告已保存到: {report_file}")
    
    # 總結
    print("\n" + "=" * 50)
    if all_issues:
        print(f"❌ 發現 {len(all_issues)} 個配置問題:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        print("\n請解決這些問題後重新運行檢查")
        sys.exit(1)
    else:
        print("✅ 所有配置檢查通過！系統已準備就緒")
        print(f"🚀 您可以使用以下命令啟動服務:")
        print(f"   python main.py")
        sys.exit(0)

if __name__ == "__main__":
    main()