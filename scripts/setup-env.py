#!/usr/bin/env python3
"""
環境設置腳本
快速創建和配置環境變數文件
"""

import os
import shutil
from pathlib import Path


def setup_backend_env():
    """設置後端環境變數"""
    backend_env_example = Path(".env.example")
    backend_env = Path(".env")
    
    if not backend_env_example.exists():
        print("❌ 找不到 .env.example 文件")
        return False
    
    if backend_env.exists():
        response = input("⚠️  .env 文件已存在，是否覆蓋？(y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("跳過後端環境配置")
            return True
    
    # 複製範本
    shutil.copy(backend_env_example, backend_env)
    
    # 讀取並修改內容
    content = backend_env.read_text(encoding='utf-8')
    
    # 詢問用戶配置
    print("\n🔧 配置後端環境變數:")
    
    # 環境類型
    env_type = input("環境類型 (development/staging/production) [development]: ").strip()
    if not env_type:
        env_type = "development"
    content = content.replace("ENV=development", f"ENV={env_type}")
    
    # 調試模式
    if env_type == "development":
        debug = "true"
    else:
        debug = input("啟用調試模式？(y/N) [N]: ").strip().lower()
        debug = "true" if debug in ['y', 'yes'] else "false"
    content = content.replace("DEBUG=false", f"DEBUG={debug}")
    
    # 服務器端口
    port = input("服務器端口 [8000]: ").strip()
    if port.isdigit():
        content = content.replace("PORT=8000", f"PORT={port}")
    
    # OCR API 配置
    ocr_api_key = input("OCR API 密鑰 [保持默認]: ").strip()
    if ocr_api_key:
        content = content.replace("OCR_API_KEY=YOUR_API_KEY", f"OCR_API_KEY={ocr_api_key}")
    
    # 寫入文件
    backend_env.write_text(content, encoding='utf-8')
    print(f"✅ 後端環境配置已保存到: {backend_env}")
    return True

def setup_frontend_env():
    """設置前端環境變數"""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ 找不到 frontend 目錄")
        return False
    
    frontend_env_example = frontend_dir / ".env.example"
    frontend_env = frontend_dir / ".env"
    
    if not frontend_env_example.exists():
        print("❌ 找不到 frontend/.env.example 文件")
        return False
    
    if frontend_env.exists():
        response = input("⚠️  frontend/.env 文件已存在，是否覆蓋？(y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("跳過前端環境配置")
            return True
    
    # 複製範本
    shutil.copy(frontend_env_example, frontend_env)
    
    # 讀取並修改內容
    content = frontend_env.read_text(encoding='utf-8')
    
    print("\n🔧 配置前端環境變數:")
    
    # API 基礎 URL
    api_url = input("後端 API URL [http://localhost:8000/api/v1]: ").strip()
    if api_url:
        content = content.replace(
            "REACT_APP_API_BASE_URL=http://localhost:8000/api/v1",
            f"REACT_APP_API_BASE_URL={api_url}"
        )
    
    # 調試模式
    debug = input("啟用前端調試模式？(Y/n) [Y]: ").strip().lower()
    debug = "false" if debug in ['n', 'no'] else "true"
    content = content.replace("REACT_APP_DEBUG=true", f"REACT_APP_DEBUG={debug}")
    
    # 寫入文件
    frontend_env.write_text(content, encoding='utf-8')
    print(f"✅ 前端環境配置已保存到: {frontend_env}")
    return True

def create_directories():
    """創建必要的目錄"""
    directories = [
        "output/card_images",
        "config",
        "logs",
        "uploads"
    ]
    
    print("\n📁 創建必要目錄:")
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")

def setup_gitignore():
    """設置 .gitignore 文件"""
    gitignore_content = """
# 環境變數文件
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# 數據庫文件
*.db
*.sqlite
*.sqlite3

# 日誌文件
logs/
*.log

# 上傳文件
uploads/
output/card_images/

# 配置文件 (可能包含敏感信息)
config/serials.json
config_report.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.vscode/
.idea/
*.swp
*.swo

# 系統文件
.DS_Store
Thumbs.db

# 臨時文件
*.tmp
*.temp
*_enhanced.jpg
"""
    
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        gitignore_path.write_text(gitignore_content.strip(), encoding='utf-8')
        print("✅ .gitignore 文件已創建")
    else:
        print("ℹ️  .gitignore 文件已存在，跳過")

def main():
    """主函數"""
    print("🚀 OCR 名片管理系統 - 環境設置工具")
    print("=" * 50)
    
    # 檢查是否在正確的目錄
    if not Path("main.py").exists():
        print("❌ 請在項目根目錄中運行此腳本")
        return
    
    success = True
    
    # 設置後端環境
    print("\n🎯 設置後端環境...")
    if not setup_backend_env():
        success = False
    
    # 設置前端環境
    print("\n🎯 設置前端環境...")
    if not setup_frontend_env():
        success = False
    
    # 創建必要目錄
    create_directories()
    
    # 設置 .gitignore
    print("\n🔒 設置 .gitignore...")
    setup_gitignore()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ 環境設置完成！")
        print("\n🔧 後續步驟:")
        print("1. 檢查並調整 .env 文件中的配置")
        print("2. 檢查並調整 frontend/.env 文件中的配置")
        print("3. 運行配置檢查: python scripts/check-config.py")
        print("4. 啟動後端服務: python main.py")
        print("5. 啟動前端服務: cd frontend && npm start")
    else:
        print("\n❌ 環境設置過程中出現問題，請檢查錯誤信息")

if __name__ == "__main__":
    main()