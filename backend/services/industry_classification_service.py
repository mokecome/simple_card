"""
AI 產業分類服務（新版）

功能：
- 使用 OpenAI + web_search 做公司產業分類
- 優先從 company_industry_mapping_v3.json 讀取結果，找不到才呼叫 GPT
- 使用 12 大產業大類
- 對外維持原本介面：
    - classify_single(company_name, position) -> {category, confidence, reason}
    - classify_batch(cards) -> [{card_id, industry_category, confidence, reason, success}]
    - classify_single_with_retry(card, max_retries=3)
    - classify_batch_async(cards, task_id)
"""

import os
import re
import time
import json
import logging
import unicodedata
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI
from .task_manager import task_manager

logger = logging.getLogger(__name__)

# 專案根目錄：services → backend → 專案根
BASE_DIR = Path(__file__).resolve().parents[2]

# 明確從專案根目錄載入 .env
load_dotenv(BASE_DIR / ".env")


class IndustryClassificationService:
    """
    AI 产业分类服务（新版）

    主要改動：
    - 改為使用 12 大產業大類（對應 major_category_12）
    - 優先從 company_industry_mapping_v3.json 讀取分類結果
    - 找不到 mapping 時才呼叫 GPT + web_search，並將結果寫回 mapping
    - 對外介面維持原本：
        - classify_single(company_name, position)
        - classify_batch(cards)
        - classify_single_with_retry(card, max_retries=3)
        - classify_batch_async(cards, task_id)
      回傳的欄位仍為：
        - industry_category: 字串（這次會是 12 大類）
        - confidence: int, 0–100
        - reason: 字串（這次放 description + labels）
        - success: bool
    """

    # mapping 檔案路徑，優先用環境變數，否則預設放在專案根目錄下
    MAPPING_PATH = Path(
        os.getenv(
            "INDUSTRY_MAPPING_PATH",
            BASE_DIR / "company_industry_mapping_v3.json",
        )
    )

    # 12 大類清單（主要是方便 log / 檢查用）
    MAJOR_12 = {
        "資訊科技",
        "金融保險",
        "製造業／工業應用",
        "建築不動產",
        "交通運輸／物流",
        "醫療健康／生技",
        "餐飲／零售／通路",
        "廣告／媒體／行銷",
        "教育／學研",
        "政府／公部門／非營利",
        "專業服務（顧問／法務／會計等）",
        "不明／其他",
    }

    # 給 GPT 的 system prompt（就是你之前那份，略微整理排版）
    SYSTEM_PROMPT = """
你是一位專門負責「公司產業分類」的專業標註員。

【任務說明】
根據輸入的公司名稱（可能包含中文名稱與英文名稱），先利用網路搜尋查詢該公司，再依照其主要業務與產品，輸出產業分類標籤。

輸入會長這樣（其中一個可能為空字串）：
- 公司中文名稱: {{company_name_zh}}
- 公司英文名稱: {{company_name_en}}

【搜尋與判斷流程】（請務必逐步執行）
1. 使用目前可用的「網路搜尋 / Bing 搜尋工具」，以以下關鍵字組合查詢：
   - 公司中文名稱（若有）＋「官網」「官方網站」「公司簡介」
   - 公司英文名稱（若有）＋「official site」「about」「company」
   - 公司名稱 + 產品、服務相關字（如「solution」「platform」「雲端」「系統」等）
2. 優先參考的資訊來源：
   - 公司官方網站（Homepage / About / Products / Services）
   - LinkedIn 公司頁
   - 各國官方商業登記 / 工商資訊網站
   - 有可信度的新聞或報導
3. 針對公司實際情況，整理出：
   - 核心產品或服務是什麼？
   - 主要客戶族群是誰（B2B / B2C / 政府等）？
   - 公司主要在解決什麼問題，或位於哪個產業鏈位置？
4. 依「主要營收來源」判斷該公司的主要產業，不要被少數副業誤導。
5. 若完全查不到資料或資訊極少，才允許給出非常低的信心分數，並將 primary_label 設為較寬泛的類別（例如「其他」），但不要憑空捏造細節。

【12大類列表】
1. 資訊科技
2. 金融保險
3. 製造業／工業應用
4. 建築不動產
5. 交通運輸／物流
6. 醫療健康／生技
7. 餐飲／零售／通路
8. 廣告／媒體／行銷
9. 教育／學研
10. 政府／公部門／非營利
11. 專業服務（顧問／法務／會計等）
12. 不明／其他

【欄位定義】
請依照以下規則輸出一個 JSON 物件（不能有額外文字）：

- major_category_12：
  - 必須從上面 12 大類中挑一個最貼近的分類名稱。
  - 除非完全查不到任何資訊，不要選 12. 其他。
  - 若同時涉及多領域，請依「核心營收來源」決定類別。
  
- primary_label：
  - 一句話的「主要產業大類」，中文短語。
  - 例：資訊科技、金融保險、製造業、廣告行銷、教育訓練、醫療健康、零售電商、政府機關、非營利組織、旅宿觀光、物流運輸 等。
  - 請根據實際查到的資訊自行選擇最貼切的產業名稱，可以不是上述舉例裡的字眼，但必須自然且常見。

- labels：
  - 一個字串陣列（List of string），包含 1～5 個相關細標籤。
  - 用來補充細分領域、技術或服務，全部要用中文。
  - 可以從「較大類別 → 較細項」的方式書寫，例如：
    - ["資訊科技", "軟體開發", "SaaS", "雲端服務"]
    - ["金融保險", "保險科技", "線上投保平台"]
  - 若有特定 vertical（如「醫院資訊系統」「旅宿訂房平台」「工業設備製造」）也可以寫進去。

- description：
  - 使用 1～3 句中文，說明為什麼這樣分類。
  - 請盡量引用你在網路上查到的關鍵資訊（例如產品、服務、客戶族群），做成自然語句。
  - 範例：
    - "該公司提供雲端 ERP 及客製化系統整合服務，主要客戶為中大型企業，因此歸類為資訊科技與軟體開發相關產業。"

- confidence：
  - 0～1 之間的小數，代表你對這個產業分類判斷的信心程度。
  - 建議：
    - 資訊充足且來源清楚 → 0.8～1.0
    - 有部分資訊，但仍有模糊空間 → 0.5～0.79
    - 幾乎查不到資料，只能做非常粗略推測 → 0.0～0.49
  - 請輸出最多小數點兩位，例如 0.86, 0.4。

【輸出格式要求】
1. 最終只允許輸出一個 JSON 物件。
2. 不要在 JSON 之外加入任何解說文字或註解。
3. JSON 的 key 必須固定為：
   - "major_category_12"
   - "primary_label"
   - "labels"
   - "description"
   - "confidence"

【輸出範例】（注意：這只是範例，實際請依查詢結果判斷）
{
  "major_category_12": "資訊科技",
  "primary_label": "資訊科技",
  "labels": ["資訊科技", "軟體開發", "SaaS"],
  "description": "提供B2B軟體服務、系統開發或雲端平台的科技公司。",
  "confidence": 0.86
}

請依照上述規則，針對以下公司產生分類結果：
公司中文名稱: {{company_name_zh}}
公司英文名稱: {{company_name_en}}

請只輸出一個 JSON 物件，不能有其他解說文字。
"""

    def __init__(self):
        """初始化 OpenAI 客户端 + mapping cache"""
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        # 建議預設改成 gpt-4o-mini（可以再用環境變數覆蓋）
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout = int(os.getenv("OPENAI_TIMEOUT", "60"))

        self._mapping_dict: Dict[str, Dict] = {}
        self._mapping_list: List[Dict] = []
        self._mapping_loaded = False

        logger.info(
            f"初始化 AI 分类服务: model={self.model}, base_url={os.getenv('OPENAI_BASE_URL')}, "
            f"mapping_path={self.MAPPING_PATH}"
        )

    # ===================== Normalization & mapping =====================

    @staticmethod
    def _normalize_width(text: str) -> str:
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def _remove_parentheses(text: str) -> str:
        return re.sub(r"[（(].*?[）)]", "", text).strip()

    def _clean_company_name_strong(self, name: Optional[str]) -> str:
        if not name:
            return ""
        name = self._normalize_width(name).strip()
        if not name:
            return ""

        name = self._remove_parentheses(name)

        zh_suffixes = [
            "股份有限公司臺灣分公司",
            "股份有限公司台灣分公司",
            "股份有限公司台北分公司",
            "股份有限公司分公司",
            "有限公司臺灣分公司",
            "有限公司台灣分公司",
            "有限公司台北分公司",
            "有限公司分公司",
            "企業股份有限公司",
            "企業有限公司",
            "有限股份公司",
            "股份有限公司",
            "有限公司",
            "股份公司",
            "企業",
            "控股公司",
            "控股",
            "集團",
            "事業部",
            "事業群",
            "事業處",
            "事業單位",
            "分公司",
            "總公司",
            "分行",
            "分部",
            "部門",
            "部",
            "課",
            "組",
            "處",
            "公司",
        ]
        for suf in zh_suffixes:
            if name.endswith(suf):
                name = name[: -len(suf)].strip()
                break

        lowered = name.lower().rstrip(" .,")

        en_suffixes = [
            "co., ltd",
            "co, ltd",
            "co ltd",
            "co.,ltd",
            "company ltd",
            "company limited",
            "inc.",
            "inc",
            "corp.",
            "corp",
            "corporation",
            "limited",
            "ltd.",
            "ltd",
        ]
        for suf in en_suffixes:
            if lowered.endswith(suf):
                cut_len = len(suf)
                name = name[: -cut_len].rstrip(" .,")
                break

        name = re.sub(r"\s+", " ", name)
        return name.strip()

    def _make_company_key(self, company_name_zh: Optional[str], company_name_en: Optional[str]) -> Optional[str]:
        raw_zh = (company_name_zh or "").strip()
        raw_en = (company_name_en or "").strip()

        cleaned_zh = self._clean_company_name_strong(raw_zh) if raw_zh else ""
        cleaned_en = self._clean_company_name_strong(raw_en) if raw_en else ""

        if cleaned_zh:
            return cleaned_zh
        elif cleaned_en:
            return cleaned_en
        elif raw_zh:
            return raw_zh
        elif raw_en:
            return raw_en
        else:
            return None

    def _load_mapping(self) -> None:
        """載入 mapping JSON 到記憶體（只載入一次）"""
        if self._mapping_loaded:
            return

        if not self.MAPPING_PATH.exists():
            logger.warning(f"找不到 mapping 檔案：{self.MAPPING_PATH}，將從空白開始")
            self._mapping_dict = {}
            self._mapping_list = []
            self._mapping_loaded = True
            return

        data = json.loads(self.MAPPING_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"mapping 檔案格式錯誤，預期為 list，實際為 {type(data)}")

        mapping_dict: Dict[str, Dict] = {}
        for entry in data:
            key = entry.get("company_key")
            if not key:
                continue
            mapping_dict[key] = entry

        self._mapping_dict = mapping_dict
        self._mapping_list = data
        self._mapping_loaded = True

        logger.info(f"載入 mapping 完成，共 {len(self._mapping_dict)} 筆公司（company_key）")

    def _save_mapping(self) -> None:
        """把記憶體中的 mapping_list 寫回檔案"""
        if not self._mapping_loaded:
            return
        self.MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.MAPPING_PATH.write_text(
            json.dumps(self._mapping_list, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ===================== GPT 叫用邏輯 =====================

    def _call_gpt_classification(self, company_name_zh: Optional[str], company_name_en: Optional[str]) -> Dict:
        """
        呼叫 GPT（含 web_search）做一次公司分類。
        回傳 JSON：
          {
            "major_category_12": "...",
            "primary_label": "...",
            "labels": [...],
            "description": "...",
            "confidence": 0.xx
          }
        """
        user_message = (
            f"公司中文名稱: {company_name_zh or ''}\n"
            f"公司英文名稱: {company_name_en or ''}\n\n"
            "請依照 system prompt 的規則，只輸出一個 JSON 物件。"
        )

        logger.info(f"呼叫 GPT 進行產業分類：zh={company_name_zh}, en={company_name_en}")

        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            tools=[{"type": "web_search"}],
            timeout=self.timeout,
        )

        result_text = response.output_text
        logger.debug(f"GPT 原始輸出：{result_text}")

        try:
            data = json.loads(result_text)
        except Exception as e:
            logger.error(f"解析 GPT JSON 失敗，改用預設 fallback：{e}")
            return {
                "major_category_12": "不明／其他",
                "primary_label": "其他",
                "labels": ["其他"],
                "description": "解析 GPT 回應失敗，使用預設分類。",
                "confidence": 0.0,
            }

        return data

    # ===================== mapping 查詢 & 更新 =====================

    def _lookup_from_mapping(self, company_name_zh: Optional[str], company_name_en: Optional[str]) -> Tuple[Optional[str], Optional[Dict]]:
        self._load_mapping()
        key = self._make_company_key(company_name_zh, company_name_en)
        if not key:
            return None, None

        entry = self._mapping_dict.get(key)
        if entry is None:
            return key, None
        return key, entry

    def _add_or_update_mapping_entry(
        self,
        company_name_zh: Optional[str],
        company_name_en: Optional[str],
        classification: Dict,
    ) -> Tuple[str, Dict]:
        """
        將 GPT 分類結果寫回 mapping：
          - 若 mapping 沒有此 key → 新增
          - 若已有 → 比較 confidence，新的較高才覆寫
        """
        self._load_mapping()
        key = self._make_company_key(company_name_zh, company_name_en)
        if not key:
            raise ValueError("無法為公司名稱產生 company_key")

        major_category_12 = classification.get("major_category_12")
        primary_label = classification.get("primary_label")
        labels = classification.get("labels") or []
        description = classification.get("description")
        confidence = classification.get("confidence")

        # ✅ 強制把 major_category_12 修正成 12 大類之一（只根據 major + primary）
        major_category_12 = self._normalize_major_category_12(
            major=major_category_12,
            primary_label=primary_label,
        )

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        old_entry = self._mapping_dict.get(key)

        if old_entry is None:
            entry = {
                "company_key": key,
                "company_name_zh": self._clean_company_name_strong(company_name_zh) if company_name_zh else None,
                "company_name_en": self._clean_company_name_strong(company_name_en) if company_name_en else None,
                "aliases": sorted({n for n in [company_name_zh, company_name_en] if n}),
                "classification_timestamp": ts,
                "major_category_12": major_category_12,
                "primary_label": primary_label,
                "labels": labels,
                "description": description,
                "confidence": confidence,
            }
            self._mapping_dict[key] = entry
            self._mapping_list.append(entry)
            self._save_mapping()
            return key, entry

        # 已存在 → 比較信心分數
        def _to_float(val):
            try:
                return float(val)
            except Exception:
                return -1.0

        old_c = _to_float(old_entry.get("confidence"))
        new_c = _to_float(confidence)

        alias_set = set(old_entry.get("aliases") or [])
        for n in [company_name_zh, company_name_en]:
            if n:
                alias_set.add(n)
        old_entry["aliases"] = sorted(alias_set)

        if new_c > old_c:
            old_entry["classification_timestamp"] = ts
            old_entry["major_category_12"] = major_category_12
            old_entry["primary_label"] = primary_label
            old_entry["labels"] = labels
            old_entry["description"] = description
            old_entry["confidence"] = confidence
            self._save_mapping()
            return key, old_entry

        # 新的信心不比較高，只更新 aliases
        self._save_mapping()
        return key, old_entry
    

    def _build_structured_reason(
        self,
        primary_label: Optional[str],
        labels: list,
    ) -> str:
        """
        產生乾淨版的結構化 classification_reason，
        格式範例：
            primary=金融科技, labels=金融保險,金融科技,數位支付,區塊鏈,加密貨幣
        """
        parts = []
        if primary_label:
            parts.append(f"primary={primary_label}")
        if labels:
            labels_str = ",".join(labels)
            parts.append(f"labels={labels_str}")

        return ", ".join(parts)
    

    def _normalize_major_category_12(
        self,
        major: Optional[str],
        primary_label: Optional[str],
    ) -> str:
        """
        強制把 major_category_12 修正成 12 大類之一（只看 major+primary，不看 labels）：
        1. 若 major 本身就在 12 類裡 → 直接用
        2. 若不在 → 用 (major + primary_label) 的關鍵字做粗分類
        3. 還是猜不到 → 統一丟「其他（無法歸類才使用）」
        """
        # 若原本就已合法，直接回傳
        if major in self.MAJOR_12:
            return major

        text = f"{major or ''} {primary_label or ''}"

        # 金融保險
        if any(k in text for k in ["金控", "銀行", "保險", "證券", "投信", "理財", "金融"]):
            return "金融保險"

        # 製造業／工業應用
        if any(k in text for k in ["製造", "工業", "機械", "設備", "零件", "加工", "材料", "工廠", "半導體", "電子元件", "OEM", "ODM"]):
            return "製造業／工業應用"

        # 建築不動產
        if any(k in text for k in ["建設", "營造", "不動產", "地產", "房屋", "住宅", "商辦", "租賃", "仲介"]):
            return "建築不動產"

        # 交通運輸／物流
        if any(k in text for k in ["物流", "運輸", "快遞", "貨運", "航運", "航空", "配送", "倉儲", "車隊"]):
            return "交通運輸／物流"

        # 醫療健康／生技
        if any(k in text for k in ["醫療", "診所", "醫院", "藥局", "藥品", "生技", "醫材", "保健", "健康", "製藥"]):
            return "醫療健康／生技"

        # 餐飲／零售／通路
        if any(k in text for k in ["餐飲", "餐廳", "咖啡", "飲料", "超商", "超市", "量販", "百貨", "零售", "賣場", "通路"]):
            return "餐飲／零售／通路"

        # 廣告／媒體／行銷
        if any(k in text for k in ["廣告", "行銷", "媒體", "公關", "branding", "品牌", "數位行銷", "整合行銷", "martech"]):
            return "廣告／媒體／行銷"

        # 教育／學研
        if any(k in text for k in ["學校", "大學", "學院", "補習", "教育", "學習", "研發", "研究中心", "研究所", "培訓"]):
            return "教育／學研"

        # 政府／公部門／非營利
        if any(k in text for k in ["市政府", "縣政府", "公所", "部會", "署", "局", "政府", "協會", "基金會", "公會", "非營利", "NPO", "NGO"]):
            return "政府／公部門／非營利"

        # 專業服務（顧問／法務／會計等）
        if any(k in text for k in ["顧問", "consulting", "會計", "記帳", "審計", "律師", "法律", "設計事務所", "地政士", "代書", "人力資源", "獵頭"]):
            return "專業服務（顧問／法務／會計等）"

        # 資訊科技（很常見，放最後）
        if any(k in text for k in ["資訊", "軟體", "SaaS", "雲端", "系統", "平台", "app", "AI", "人工智慧", "IT", "網路", "科技", "數位轉型"]):
            return "資訊科技"

        # 真的完全看不出來就丟其他
        return "不明／其他"




    # ===================== 對外：單筆 classification pipeline =====================

    def _classify_runtime(self, company_name_zh: Optional[str], company_name_en: Optional[str]) -> Dict[str, any]:
        """
        新版單筆分類流程（不含 retry）：
        1. 先查 mapping
        2. 找不到時 call GPT + web_search，並更新 mapping
        3. 回傳格式：
            {
                "industry_category": <12大類>,
                "confidence": <0~1 小數>,
                "reason": 結構化字串 (primary + labels + key),
                "source": "mapping" / "gpt_new",
                "classified_at": <時間字串>,
                "success": True/False,
            }
        """
        self._load_mapping()
        key, entry = self._lookup_from_mapping(company_name_zh, company_name_en)

        # ---- 1. 先用 mapping ----
        if key and entry:
            source = "mapping"
            major = entry.get("major_category_12") or "不明／其他"
            primary = entry.get("primary_label")
            labels = entry.get("labels") or []
            raw_conf = entry.get("confidence")

            # 統一用 0~1 小數
            try:
                conf_float = float(raw_conf) if raw_conf is not None else 0.0
            except Exception:
                conf_float = 0.0
            conf_float = max(0.0, min(1.0, conf_float))

            # 結構化 reason
            reason = self._build_structured_reason(
                primary_label=primary,
                labels=labels,
            )

            classified_at = entry.get("classification_timestamp") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return {
                "industry_category": major,
                "confidence": conf_float,
                "reason": reason,
                "source": source,
                "classified_at": classified_at,
                "success": True,
            }

        # ---- 2. mapping 沒有 → call GPT + 更新 mapping ----
        cls = self._call_gpt_classification(company_name_zh, company_name_en)
        source = "gpt_new"
        key, final_entry = self._add_or_update_mapping_entry(company_name_zh, company_name_en, cls)

        major = final_entry.get("major_category_12") or "不明／其他"
        primary = final_entry.get("primary_label")
        labels = final_entry.get("labels") or []
        raw_conf = final_entry.get("confidence")

        try:
            conf_float = float(raw_conf) if raw_conf is not None else 0.0
        except Exception:
            conf_float = 0.0
        conf_float = max(0.0, min(1.0, conf_float))

        reason = self._build_structured_reason(
            primary_label=primary,
            labels=labels,
        )

        classified_at = final_entry.get("classification_timestamp") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "industry_category": major,
            "confidence": conf_float,
            "reason": reason,
            "source": source,
            "classified_at": classified_at,
            "success": True,
        }

    # ===================== 對外接口：維持原本 method 介面 =====================

    def classify_single(self, company_name: str, position: str) -> Dict[str, any]:
        """
        單筆分類（相容舊介面）
        新增功能：自動判斷 company_name 是中文還是英文
        然後將 zh + en 分開欄位，與批次邏輯完全一致
        """

        def detect_lang(name: str):
            # 有中文字 → 中文名
            if re.search(r"[\u4e00-\u9fff]", name):
                return "zh"
            # 沒中文 → 當作英文
            return "en"

        lang = detect_lang(company_name)

        if lang == "zh":
            company_name_zh = company_name
            company_name_en = None
        else:
            company_name_zh = None
            company_name_en = company_name
        try:
            logger.info(f"[單筆分類] zh={company_name_zh}, en={company_name_en}")

            # 🔥 這裡開始與批次完全一致！
            result = self._classify_runtime(
                company_name_zh=company_name_zh,
                company_name_en=company_name_en
            )

            logger.info(f"[單筆分類完成] result={result}")

            return {
                "category": result["industry_category"],
                "confidence": result["confidence"],
                "reason": result["reason"],
            }

        except Exception as e:
            logger.error(f"AI 分類失敗: {str(e)}")
            return {
                "category": "不明／其他",
                "confidence": 0,
                "reason": "",
            }

    def classify_batch(self, cards: List[Dict]) -> List[Dict]:
        """
        批量分類名片（同步）
        Args:
            cards: 每個名片包含 id, company_name_zh/en, position_zh/en
        Returns:
            [
              {
                "card_id": ...,
                "industry_category": ...,
                "confidence": ...,
                "reason": ...,
                "success": True/False
              },
              ...
            ]
        """
        results = []
        total = len(cards)

        logger.info(f"開始批量分類 {total} 張名片（同步）")

        for index, card in enumerate(cards, 1):
            company_zh = card.get("company_name_zh")
            company_en = card.get("company_name_en")
            logger.info(f"[{index}/{total}] 分类名片 ID={card['id']} 公司={company_zh}/{company_en}")

            try:
                r = self._classify_runtime(company_zh, company_en)
                results.append({
                    "card_id": card["id"],
                    "industry_category": r["industry_category"],
                    "confidence": r["confidence"],
                    "reason": r["reason"],
                    "success": r["success"],
                })
            except Exception as e:
                logger.error(f"名片 {card['id']} 批量分類失敗: {e}")
                results.append({
                    "card_id": card["id"],
                    "industry_category": "不明／其他",
                    "confidence": 0,
                    "reason": "",
                    "success": False,
                })

        logger.info(
            f"批量分類完成: 總數={total}, 成功={sum(1 for r in results if r['success'])}"
        )
        return results

    def classify_single_with_retry(self, card: Dict, max_retries: int = 3) -> Dict:
        """
        新版單張名片分類（帶重試），會使用 company_name_zh/en

        Args:
            card: 名片資料
            max_retries: 最大重試次數
        """
        company_zh = card.get("company_name_zh")
        company_en = card.get("company_name_en")

        for attempt in range(max_retries):
            try:
                r = self._classify_runtime(company_zh, company_en)
                if r["success"] and r["confidence"] > 0:
                    return {
                        "card_id": card["id"],
                        "industry_category": r["industry_category"],
                        "confidence": r["confidence"],
                        "reason": r["reason"],
                        "success": True,
                    }

                if attempt < max_retries - 1:
                    logger.warning(
                        f"名片 {card['id']} 分類置信度為0，重試 {attempt + 1}/{max_retries - 1}"
                    )
                    time.sleep(1)

            except Exception as e:
                logger.error(
                    f"名片 {card['id']} 分類失敗 (嘗試 {attempt + 1}/{max_retries}): {str(e)}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return {
                        "card_id": card["id"],
                        "industry_category": "不明／其他",
                        "confidence": 0,
                        "reason": "",
                        "success": False,
                    }

        return {
            "card_id": card["id"],
            "industry_category": "不明／其他",
            "confidence": 0,
            "reason": "",
            "success": False,
        }

    def classify_batch_async(self, cards: List[Dict], task_id: str) -> List[Dict]:
        """
        異步批量分類名片（多執行緒併發）

        Args:
            cards: 名片列表
            task_id: 任務 ID

        Returns:
            分類結果列表
        """
        total = len(cards)
        logger.info(f"開始異步批量分類 {total} 張名片，任務ID: {task_id}")

        results: List[Dict] = []
        max_workers = 5

        def process_card(card):
            if task_manager.is_cancelled(task_id):
                logger.info(f"任務 {task_id} 已取消，停止處理名片 {card['id']}")
                return None

            result = self.classify_single_with_retry(card, max_retries=3)
            task_manager.update_progress(task_id, success=result["success"])
            return result

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_card = {executor.submit(process_card, card): card for card in cards}

            for future in as_completed(future_to_card):
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    card = future_to_card[future]
                    logger.error(f"處理名片 {card['id']} 時發生異常: {str(e)}")
                    results.append({
                        "card_id": card["id"],
                        "industry_category": "不明／其他",
                        "confidence": 0,
                        "reason": "",
                        "success": False,
                    })
                    task_manager.update_progress(task_id, success=False)

        success_count = sum(1 for r in results if r["success"])
        logger.info(
            f"異步批量分類完成: 任務ID={task_id}, 總數={total}, 成功={success_count}, 失敗={total - success_count}"
        )
        return results
