import os
import traceback
from pathlib import Path

from dotenv import load_dotenv
from backend.services.industry_classification_service import IndustryClassificationService


def main():
    # 先明確載入 .env
    base_dir = Path(__file__).resolve().parent  # manage_card 資料夾
    env_path = base_dir / ".env"
    load_dotenv(env_path)
    
    print("=== 環境檢查 ===")
    print("Python 執行目錄 (CWD):", Path.cwd())
    print("OPENAI_API_KEY 設了嗎:", bool(os.getenv("OPENAI_API_KEY")))
    print("OPENAI_MODEL:", os.getenv("OPENAI_MODEL"))
    print("OPENAI_BASE_URL:", os.getenv("OPENAI_BASE_URL"))

    # 檢查 mapping 路徑實際指到哪裡
    svc = IndustryClassificationService()
    mapping_path = svc.MAPPING_PATH
    print("Mapping 路徑 (from service):", mapping_path)
    print("Mapping 絕對路徑:", mapping_path.resolve())
    print("Mapping 存在嗎:", mapping_path.exists())

    print("\n=== 嘗試呼叫 classify_single ===")
    try:
        result = svc.classify_single("聯強國際股份有限公司", "工程師")
        print("classify_single 成功，結果：", result)
    except Exception as e:
        print("classify_single 發生錯誤：", repr(e))
        traceback.print_exc()


if __name__ == "__main__":
    main()
