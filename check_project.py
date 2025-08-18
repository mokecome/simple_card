#!/usr/bin/env python3
"""
OCR名片應用項目檢查腳本
檢查項目依賴、配置和基本功能
"""

import sys
import os
import importlib
import subprocess
from pathlib import Path

def check_python_version():
    """檢查Python版本"""
    print("🐍 檢查Python版本...")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 8:
        print("   ✅ Python版本符合要求")
        return True
    else:
        print("   ❌ Python版本過低，需要3.8+")
        return False

def check_dependencies():
    """檢查Python依賴"""
    print("\n📦 檢查Python依賴...")
    
    required_packages = [
        'fastapi',
        'uvicorn', 
        'sqlalchemy',
        'pydantic',
        'requests',
        'pillow'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (缺失)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n   需要安裝缺失的依賴: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_backend_modules():
    """檢查後端模組"""
    print("\n🔧 檢查後端模組...")
    
    # 添加backend路徑
    backend_path = Path(__file__).parent / 'backend'
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    modules_to_check = [
        ('backend.core.config', '配置模組'),
        ('backend.core.response', '響應處理模組'),
        ('backend.core.exceptions', '異常處理模組'),
        ('backend.models.card', '名片模型'),
        ('backend.services.ocr_service', 'OCR服務'),
        ('backend.api.v1.card', '名片API'),
    ]
    
    for module_name, description in modules_to_check:
        try:
            importlib.import_module(module_name)
            print(f"   ✅ {description}")
        except ImportError as e:
            print(f"   ❌ {description} - {e}")
            return False
    
    return True

def check_frontend():
    """檢查前端"""
    print("\n🌐 檢查前端...")
    
    frontend_path = Path(__file__).parent / 'frontend'
    package_json = frontend_path / 'package.json'
    node_modules = frontend_path / 'node_modules'
    
    if not package_json.exists():
        print("   ❌ package.json不存在")
        return False
    
    print("   ✅ package.json存在")
    
    if not node_modules.exists():
        print("   ⚠️  node_modules不存在，需要運行: cd frontend && npm install")
        return False
    
    print("   ✅ node_modules存在")
    return True

def check_database():
    """檢查數據庫"""
    print("\n🗄️  檢查數據庫...")
    
    db_file = Path(__file__).parent / 'cards.db'
    if db_file.exists():
        print("   ✅ 數據庫文件存在")
    else:
        print("   ⚠️  數據庫文件不存在，首次啟動時會自動創建")
    
    return True

def check_directories():
    """檢查必要目錄"""
    print("\n📁 檢查目錄結構...")
    
    required_dirs = [
        'backend',
        'frontend', 
        'output/card_images',
        'share-docs/tasks'
    ]
    
    for dir_path in required_dirs:
        full_path = Path(__file__).parent / dir_path
        if full_path.exists():
            print(f"   ✅ {dir_path}")
        else:
            print(f"   ⚠️  {dir_path} (不存在，將自動創建)")
            full_path.mkdir(parents=True, exist_ok=True)
    
    return True

def check_config():
    """檢查配置"""
    print("\n⚙️  檢查配置...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'backend'))
        from backend.core.config import settings, check_environment
        
        print(f"   ✅ 應用名稱: {settings.APP_NAME}")
        print(f"   ✅ 版本: {settings.APP_VERSION}")
        print(f"   ✅ 環境: {settings.ENV}")
        print(f"   ✅ 主機: {settings.HOST}:{settings.PORT}")
        
        issues = check_environment()
        if issues:
            print(f"   ⚠️  配置問題: {', '.join(issues)}")
        else:
            print("   ✅ 配置檢查通過")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 配置檢查失敗: {e}")
        return False

def main():
    """主檢查函數"""
    print("=" * 50)
    print("🚀 OCR名片應用項目檢查")
    print("=" * 50)
    
    checks = [
        check_python_version,
        check_dependencies,
        check_directories,
        check_backend_modules,
        check_config,
        check_database,
        check_frontend
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        if check():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 檢查結果: {passed}/{total} 項通過")
    
    if passed == total:
        print("🎉 項目檢查完全通過！可以正常運行")
        print("\n啟動命令:")
        print("   後端: python main.py")
        print("   前端: cd frontend && npm start")
    else:
        print("⚠️  發現問題，請根據上述提示進行修復")
    
    print("=" * 50)

if __name__ == "__main__":
    main() 