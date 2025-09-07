"""
簡化的環境變數配置管理
只使用環境變數進行配置
"""
import os
from typing import List

def get_env_bool(key: str, default: bool = False) -> bool:
    """獲取布林類型環境變數"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_env_int(key: str, default: int = 0) -> int:
    """獲取整數類型環境變數"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

def get_env_list(key: str, default: List[str] = None) -> List[str]:
    """獲取列表類型環境變數 (逗號分隔)"""
    if default is None:
        default = []
    value = os.getenv(key, '')
    if not value:
        return default
    return [item.strip() for item in value.split(',') if item.strip()]

# 應用程式基本設定
APP_NAME = os.getenv('APP_NAME', 'OCR 名片管理系統')
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
DEBUG = get_env_bool('DEBUG', False)
ENV = os.getenv('ENV', 'development')

# 服務器設定
HOST = os.getenv('HOST', '0.0.0.0')
PORT = get_env_int('PORT', 8006)
WORKERS = get_env_int('WORKERS', 1)

# 數據庫設定
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./cards.db')
DB_ECHO = get_env_bool('DB_ECHO', False)

# API 設定
API_V1_PREFIX = os.getenv('API_V1_PREFIX', '/api/v1')

# CORS 設定
CORS_ORIGINS = get_env_list('CORS_ORIGINS', ['*'])
CORS_CREDENTIALS = get_env_bool('CORS_CREDENTIALS', True)
CORS_METHODS = get_env_list('CORS_METHODS', ['*'])
CORS_HEADERS = get_env_list('CORS_HEADERS', ['*'])

# 文件上傳設定
UPLOAD_DIR = os.getenv('UPLOAD_DIR', 'output/card_images')
MAX_FILE_SIZE = get_env_int('MAX_FILE_SIZE', 10 * 1024 * 1024)
ALLOWED_FILE_TYPES = get_env_list('ALLOWED_FILE_TYPES', ['.jpg', '.jpeg', '.png'])

# OCR 設定
OCR_API_URL = os.getenv('OCR_API_URL', 'http://0.0.0.0:23333/v1')
OCR_API_KEY = os.getenv('OCR_API_KEY', 'YOUR_API_KEY')
OCR_TIMEOUT = get_env_int('OCR_TIMEOUT', 30)

# 卡片增強設定
USE_CARD_ENHANCEMENT = get_env_bool('USE_CARD_ENHANCEMENT', True)
USE_OPENCV = get_env_bool('USE_OPENCV', True)
CARD_ENHANCEMENT_SCALE_FACTOR = get_env_int('CARD_ENHANCEMENT_SCALE_FACTOR', 3)
CARD_ENHANCEMENT_AUTO_DETECT = get_env_bool('CARD_ENHANCEMENT_AUTO_DETECT', True)
CARD_ENHANCEMENT_MANUAL_COORDS = get_env_list('CARD_ENHANCEMENT_MANUAL_COORDS', ['150', '440', '1130', '840'])

# 批量處理設定
BATCH_PROCESSING_SIZE = get_env_int('BATCH_PROCESSING_SIZE', 5)
MEMORY_THRESHOLD = get_env_int('MEMORY_THRESHOLD', 85)  # 85%
BATCH_PROCESSING_ENABLED = get_env_bool('BATCH_PROCESSING_ENABLED', True)

# 序號管理設定
SERIAL_CONFIG_FILE = os.getenv('SERIAL_CONFIG_FILE', 'config/serials.json')
SERIAL_DEFAULT_DURATION = get_env_int('SERIAL_DEFAULT_DURATION', 15)

# OCR服務設定
OCR_PORT = get_env_int('OCR_PORT', 8504)
OCR_HOST = os.getenv('OCR_HOST', '0.0.0.0')
OCR_UPLOAD_FOLDER = os.getenv('OCR_UPLOAD_FOLDER', 'uploads')
OCR_CONFIG_FILE = os.getenv('OCR_CONFIG_FILE', 'config/serials.json')
OCR_BATCH_API_URL = os.getenv('OCR_BATCH_API_URL', 'https://local_llm.star-bit.io/api/card')


# 日誌設定
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', None)
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 環境檢查
def is_development() -> bool:
    return ENV == 'development'

def is_production() -> bool:
    return ENV == 'production'

def print_settings_summary():
    """打印配置摘要"""
    print(f"\n{'='*50}")
    print(f"🚀 {APP_NAME} v{APP_VERSION}")
    print(f"{'='*50}")
    print(f"環境: {ENV}")
    print(f"調試: {DEBUG}")
    print(f"服務器: {HOST}:{PORT}")
    print(f"數據庫: {DATABASE_URL}")
    print(f"上傳目錄: {UPLOAD_DIR}")
    print(f"日誌級別: {LOG_LEVEL}")
    print(f"{'='*50}")
    print(f"📸 卡片增強功能")
    print(f"智能增強: {'✅ 啟用' if USE_CARD_ENHANCEMENT else '❌ 禁用'}")
    print(f"OpenCV檢測: {'✅ 啟用' if USE_OPENCV else '❌ 禁用'}")
    print(f"自動檢測: {'✅ 啟用' if CARD_ENHANCEMENT_AUTO_DETECT else '❌ 禁用'}")
    print(f"放大倍數: {CARD_ENHANCEMENT_SCALE_FACTOR}x")
    print(f"🔄 批量處理功能")
    print(f"批量處理: {'✅ 啟用' if BATCH_PROCESSING_ENABLED else '❌ 禁用'}")
    print(f"批次大小: {BATCH_PROCESSING_SIZE}")
    print(f"記憶體閾值: {MEMORY_THRESHOLD}%")
    print(f"{'='*50}\n")

def check_environment():
    """檢查環境配置"""
    issues = []
    
    if is_production() and DEBUG:
        issues.append("生產環境不應啟用 DEBUG")
    
    if OCR_API_KEY == 'YOUR_API_KEY':
        issues.append("OCR_API_KEY 需要設置")
    
    if issues:
        print("⚠️  配置問題:")
        for issue in issues:
            print(f"   - {issue}")
    
    return issues

# 創建一個settings對象來匹配main.py中的調用
class Settings:
    APP_NAME = APP_NAME
    APP_VERSION = APP_VERSION
    DEBUG = DEBUG
    ENV = ENV
    HOST = HOST
    PORT = PORT
    WORKERS = WORKERS
    DATABASE_URL = DATABASE_URL
    API_V1_PREFIX = API_V1_PREFIX
    CORS_ORIGINS = CORS_ORIGINS
    CORS_CREDENTIALS = CORS_CREDENTIALS
    CORS_METHODS = CORS_METHODS
    CORS_HEADERS = CORS_HEADERS
    UPLOAD_DIR = UPLOAD_DIR
    LOG_LEVEL = LOG_LEVEL
    LOG_FORMAT = LOG_FORMAT
    
    # OCR相關設定
    OCR_API_URL = OCR_API_URL
    OCR_API_KEY = OCR_API_KEY
    OCR_TIMEOUT = OCR_TIMEOUT
    OCR_PORT = OCR_PORT
    OCR_HOST = OCR_HOST
    OCR_UPLOAD_FOLDER = OCR_UPLOAD_FOLDER
    OCR_CONFIG_FILE = OCR_CONFIG_FILE
    OCR_BATCH_API_URL = OCR_BATCH_API_URL
    
    # 卡片增強設定
    USE_CARD_ENHANCEMENT = USE_CARD_ENHANCEMENT
    USE_OPENCV = USE_OPENCV
    CARD_ENHANCEMENT_SCALE_FACTOR = CARD_ENHANCEMENT_SCALE_FACTOR
    CARD_ENHANCEMENT_AUTO_DETECT = CARD_ENHANCEMENT_AUTO_DETECT
    CARD_ENHANCEMENT_MANUAL_COORDS = CARD_ENHANCEMENT_MANUAL_COORDS
    
    # 批量處理設定
    BATCH_PROCESSING_SIZE = BATCH_PROCESSING_SIZE
    MEMORY_THRESHOLD = MEMORY_THRESHOLD
    BATCH_PROCESSING_ENABLED = BATCH_PROCESSING_ENABLED
    
    # 序號管理設定
    SERIAL_CONFIG_FILE = SERIAL_CONFIG_FILE
    SERIAL_DEFAULT_DURATION = SERIAL_DEFAULT_DURATION
    
    # 文件相關設定
    MAX_FILE_SIZE = MAX_FILE_SIZE
    ALLOWED_FILE_TYPES = ALLOWED_FILE_TYPES
    
    @property
    def is_development(self):
        return ENV == 'development'
    
    @property
    def is_production(self):
        return ENV == 'production'

settings = Settings() 