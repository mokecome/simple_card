# backend/services/wcxf_import_service.py
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

import plistlib
import datetime
import base64
import uuid
import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.core.config import settings
#from backend.models.db import SessionLocal
from backend.services.card_service import bulk_create_cards
from backend.schemas.card import CardCreate

class DictModelWrapper:
    """讓 dict 適配 CardService.bulk_create_cards 所需介面"""
    def __init__(self, data: dict):
        self._data = data

    def model_dump(self, *args, **kwargs) -> dict:
        """
        模擬 Pydantic v2 的 model_dump 介面：
        - 接受任意參數（例如 exclude_unset=True）
        - 但實際上直接回傳原始 dict
        """
        return self._data

class WcxfImportService:
    def __init__(self, wcxf_path: Path):
        self.wcxf_path = wcxf_path
        # 圖片要存去哪裡：請對應你 config.py 裡實際的變數名稱
        self.card_image_dir = Path(settings.UPLOAD_DIR)

    # ---------- Step 1: 解析 wcxf → 取得「原始 card list」 ----------
    def _load_cards(self) -> List[dict]:
        """用 plistlib 讀取 wcxf，回傳名片的 list"""
        try:
            with self.wcxf_path.open("rb") as f:
                plist = plistlib.load(f)
        except Exception as e:
            logger.error(f"Failed to load wcxf file {self.wcxf_path}: {e}")
            return []

        # 名片王通常會有類似 "kWCXF_R_CardArray" 這個 key
        return plist.get("kWCXF_R_CardArray", [])

    # ---------- Step 2: 把一張名片的欄位 mapping 成我們系統的格式 ----------
    
    #----Helper:判斷字串是中文或英文----
    def _split_zh_en(self, text) -> Tuple[Optional[str], Optional[str]]:
        """
        給一段字串：
        - 如果是 None 或空字串 → (None, None)
        - 如果全 ASCII → (None, text) 視為英文
        - 否則 → (text, None) 視為中文（或含中文的混合）
        """
        text = self._safe_text(text)
        if not text:
            return None, None

        # 全都是英文 / 數字 / 符號
        # 只要有非 ASCII，就當作中文那邊
        return (None, text) if text.isascii() else (text, None)
            
        
    #----Helper:從多個字串中，分別找出第一個中文和第一個英文----
    def _pick_zh_en_from_list(self, values: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        把多個字串分成 (第一個中文, 第一個英文)
        例如 ['思偉達創新科技', 'STARBIT'] → ('思偉達創新科技', 'STARBIT')
        """
        zh = en = None

        for v in values:
            if not v or not (v := v.strip()):
                continue

            z, e = self._split_zh_en(v)
            zh = zh or z
            en = en or e

            if zh and en:
                break

        return zh, en
    

    #----Helper:統一轉乘list----
    def _normalize_to_list(self, raw) -> List:
        """
        將 WCXF 欄位統一轉成 list：
        - None → []
        - dict → [dict]
        - str → [str]
        - list → 原樣（不管裡面是 dict 或 str）
        """
        if raw is None:
            return []

        if isinstance(raw, list):
            return raw

        # 單一 dict 或單一 str
        return [raw]
    

    #----Helper:從item中抽出字串----
    def _extract_value(self, item, key: str = None) -> str:
        """
        從 item 中抽出字串：
        - 如果 item 是 dict → 回傳 item[key] 或空字串
        - 如果 item 是 str → 回傳它自身
        """
        if item is None:
            return ""

        if isinstance(item, dict):
            if key:
                return (item.get(key, "") or "").strip()
            return ""

        # 其他型態（str 等）直接轉成字串
        return str(item).strip()    
    

    def _safe_text(self, v) -> str:
        """
        把 None / str / list / dict 轉成安全字串（可 strip）
        - list: 會把每個元素轉字串後用 ", " 串起來
        - dict: 會取 dict 裡所有可轉字串的 value 串起來（避免不知道 key）
        """
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, list):
            parts = []
            for x in v:
                s = self._safe_text(x)
                if s:
                    parts.append(s)
            return ", ".join(parts).strip()
        if isinstance(v, dict):
            parts = []
            for x in v.values():
                s = self._safe_text(x)
                if s:
                    parts.append(s)
            return ", ".join(parts).strip()
        return str(v).strip()


    #通用多筆欄位抽取方法
    def _extract_multiple_fields(
        self, 
        items: List[str], 
        zh_count: int = 0, 
        en_count: int = 0
    ) -> Dict[str, Optional[str]]:
        """
        通用方法：從字串列表中提取指定數量的中英文欄位
        
        Args:
            items: 原始字串列表
            zh_count: 需要的中文欄位數量
            en_count: 需要的英文欄位數量
            
        Returns:
            包含 zh_1, zh_2... en_1, en_2... 的字典
        """
        zh_list = []
        en_list = []

        for item in self._normalize_to_list(items):
            item = self._safe_text(item)
            if not item:
                continue

            z, e = self._split_zh_en(item)
            if z:
                zh_list.append(z)
            elif e:
                en_list.append(e)

        result = {}
        
        # 填充中文欄位
        for i in range(zh_count):
            key = f"zh_{i + 1}" if i > 0 else "zh"
            result[key] = zh_list[i] if i < len(zh_list) else None
        
        # 填充英文欄位
        for i in range(en_count):
            key = f"en_{i + 1}" if i > 0 else "en"
            result[key] = en_list[i] if i < len(en_list) else None

        return result
    

    # 從 wcxf 的 Name 欄位中抽取姓名
    def _extract_names(self, card: dict) -> Tuple[Optional[str], Optional[str]]:
        """提取姓名（中/英各1個），同時容錯 list[dict] / list[str] / 單一字串"""
        raw = card.get("kWCXF_CDL1_Name")
        name_list = self._normalize_to_list(raw)

        name_candidates = []
        for item in name_list:
            # 如果是 dict → 用 kWCXF_CDL2_Name_Full
            # 如果是 str → 直接字串
            value = self._extract_value(item, "kWCXF_CDL2_Name_Full")
            if value:
                name_candidates.append(value)

        return self._pick_zh_en_from_list(name_candidates)
    

    # 從 wcxf 的 Company 欄位中抽取公司名稱
    def _extract_companies(self, card: dict) -> Tuple[Optional[str], Optional[str]]:
        """提取公司名稱（中/英各1個），支援 list[dict] / list[str] / dict / str 混合格式"""
        raw = card.get("kWCXF_CDL1_Company")

        # 統一轉成 list：None → []，dict/str → [item]，list → 原樣
        company_list = self._normalize_to_list(raw)

        company_names: List[str] = []

        for item in company_list:
            # 若是 dict → 取 kWCXF_CDL2_Company_Name
            # 若是 str / 其他 → _extract_value 會直接轉成字串
            value = self._extract_value(item, "kWCXF_CDL2_Company_Name")
            if value:
                company_names.append(value)

        if not company_names:
            return None, None

        # 共用你原本的中/英分配邏輯（第一個中文＋第一個英文）
        return self._pick_zh_en_from_list(company_names)

    
    # 從 Position 列表中抽取職稱
    def _extract_positions(self, card: dict) -> Dict[str, Optional[str]]:
        """提取職位（中/英各最多2個）"""
        pos_list = card.get("kWCXF_CDL1_Position", []) or []
        return self._extract_multiple_fields(pos_list, zh_count=2, en_count=2)
    

    # 從 Department 列表中抽取部門名稱
    def _extract_departments(self, card: dict) -> Dict[str, Optional[str]]:
        """提取部門（中/英各最多3個）"""
        dept_list = card.get("kWCXF_CDL1_Department", []) or []
        return self._extract_multiple_fields(dept_list, zh_count=3, en_count=3)


    # 抽取電話資訊
    # Line / WeChat 目前 wcxf 未提供，預設 None。
    def _extract_phones(self, card: dict) -> Dict[str, Optional[str]]:
        """提取電話資訊"""
        phone_info = card.get("kWCXF_CDL1_Phone", {}) or {}

        # ---- 手機：kWCXF_CDL2_Phone_Mobile 可能是 str 或 list ----
        mobile_raw = phone_info.get("kWCXF_CDL2_Phone_Mobile")
        mobile_list = self._normalize_to_list(mobile_raw)

        mobile: Optional[str] = None
        for item in mobile_list:
            v = self._extract_value(item)  # 不給 key → 直接當字串處理
            if v:
                mobile = v
                break

        # ---- 公司電話：kWCXF_CDL2_Phone_Work 可能是 str 或 list ----
        work_raw = phone_info.get("kWCXF_CDL2_Phone_Work")
        work_list = self._normalize_to_list(work_raw)

        work_numbers: List[str] = []
        for item in work_list:
            v = self._extract_value(item)
            if v:
                work_numbers.append(v)

        company_phone1 = work_numbers[0] if len(work_numbers) > 0 else None
        company_phone2 = work_numbers[1] if len(work_numbers) > 1 else None

        # ---- 傳真：kWCXF_CDL2_Phone_WorkFax 有時是 str，有時是 list ----
        fax_raw = phone_info.get("kWCXF_CDL2_Phone_WorkFax")
        fax_list = self._normalize_to_list(fax_raw)

        fax: Optional[str] = None
        for item in fax_list:
            v = self._extract_value(item)
            if v:
                fax = v
                break

        return {
            "mobile_phone": mobile,
            "company_phone1": company_phone1,
            "company_phone2": company_phone2,
            "fax": fax,
            "line_id": None,   # wcxf 沒提供，維持 None
            "wechat_id": None, # wcxf 沒提供，維持 None
        }
    

    # 地址方面判斷中英文要用自己的方法
    def _is_address_english(self, addr: dict) -> bool:
        """
        判斷地址是否為英文
        注意：Country 欄位可能總是中文，所以主要根據 Street, City, State 判斷
        """
        # 取得主要地址欄位（不含 Country，因為可能總是中文）
        main_fields = [
            addr.get("kWCXF_CDL3_Address_Street", "").strip(),
            addr.get("kWCXF_CDL3_Address_City", "").strip(),
            addr.get("kWCXF_CDL3_Address_State", "").strip(),
        ]
        
        # 過濾掉空字串
        main_fields = [f for f in main_fields if f]
        
        if not main_fields:
            return False
        
        # 統計各欄位的語言特徵
        ascii_count = sum(1 for f in main_fields if f.isascii())
        
        # 如果大部分欄位（>=60%）都是 ASCII，判定為英文
        return ascii_count >= len(main_fields) * 0.6


    # 從 Work 地址列表中組成完整地址字串
    def _extract_addresses(self, card: dict) -> Dict[str, Optional[str]]:
        """提取地址（中/英各最多2個 Work 地址）"""
        addr_info = card.get("kWCXF_CDL1_Address", {}) or {}
        work_raw = addr_info.get("kWCXF_CDL2_Address_Work", []) or []

        # ✅ 統一轉成 list：None → []、dict/str → [item]、list → 原樣
        work_addrs = self._normalize_to_list(work_raw)

        zh_addresses: List[str] = []
        en_addresses: List[str] = []
        
        for addr in work_addrs:
        # 情況一：整個 addr 就是一條字串地址
            if isinstance(addr, str):
                text = addr.strip()
                if not text:
                    continue

                # 粗略判斷語言：全 ASCII → 英文，否則當中文
                if text.isascii():
                    en_addresses.append(text)
                else:
                    zh_addresses.append(text)
                continue

            # 情況二：正常的 dict 格式
            if not isinstance(addr, dict):
                # 其他奇怪型別先略過
                continue

            # 用你定義好的 helper 抽欄位，避免 .get 直接炸掉
            country = self._extract_value(addr, "kWCXF_CDL3_Address_Country")
            state = self._extract_value(addr, "kWCXF_CDL3_Address_State")
            city = self._extract_value(addr, "kWCXF_CDL3_Address_City")
            street = self._extract_value(addr, "kWCXF_CDL3_Address_Street")
            zip_code = self._extract_value(addr, "kWCXF_CDL3_Address_ZIP")

            # 保留你原本的地址語言判斷邏輯
            is_english = self._is_address_english(addr)

            if is_english:
                # ✅ 英文格式：Street, City, State ZIP, Country
                components: List[str] = []

                if street:
                    components.append(street)
                if city:
                    components.append(city)

                if state and zip_code:
                    components.append(f"{state} {zip_code}")
                elif state:
                    components.append(state)
                elif zip_code:
                    components.append(zip_code)

                if country:
                    components.append(country)

                full = ", ".join(c for c in components if c).strip()
                if full:
                    en_addresses.append(full)
            else:
                # ✅ 中文格式：Country ZIP State City Street
                components = [country, zip_code, state, city, street]
                full = "".join(c for c in components if c).strip()
                if full:
                    zh_addresses.append(full)

        return {
            "company_address1_zh": zh_addresses[0] if len(zh_addresses) > 0 else None,
            "company_address2_zh": zh_addresses[1] if len(zh_addresses) > 1 else None,
            "company_address1_en": en_addresses[0] if len(en_addresses) > 0 else None,
            "company_address2_en": en_addresses[1] if len(en_addresses) > 1 else None,
        }


    # 主 mapping 函式：
    def _parse_single_card_fields(self, card: dict) -> Dict[str, Any]:
        """
        把一筆 wcxf 的名片 card dict，轉成我們系統 Card 的欄位格式（不含圖片）
        """
        # 姓名
        name_zh, name_en = self._extract_names(card)
        
        # 公司名稱
        company_name_zh, company_name_en = self._extract_companies(card)
        
        # 職位
        positions = self._extract_positions(card)
        
        # 部門
        departments = self._extract_departments(card)
        
        # 聯絡方式
        phones = self._extract_phones(card)
        
        # 地址
        addresses = self._extract_addresses(card)
        
        # Email
        email_info = card.get("kWCXF_CDL1_Email", {}) or {}
        email_raw = email_info.get("kWCXF_CDL2_Email_Work")
        email_list = self._normalize_to_list(email_raw)
        email = None
        for it in email_list:
            v = self._safe_text(it)
            if v:
                email = v
                break
        
        # 備註
        note1 = self._safe_text(card.get("kWCXF_CDL1_Note")) or None
        
        # 時間欄位
        created_at = card.get("kWCXF_CDL1_CreateTime") or datetime.datetime.utcnow()
        updated_at = card.get("kWCXF_CDL1_ModifiedTime") or created_at

        return {
            # 姓名
            "name_zh": name_zh,
            "name_en": name_en,
            
            # 公司
            "company_name_zh": company_name_zh,
            "company_name_en": company_name_en,
            
            # 職位
            "position_zh": positions.get("zh"),
            "position_en": positions.get("en"),
            "position1_zh": positions.get("zh_2"),
            "position1_en": positions.get("en_2"),
            
            # 部門
            "department1_zh": departments.get("zh"),
            "department1_en": departments.get("en"),
            "department2_zh": departments.get("zh_2"),
            "department2_en": departments.get("en_2"),
            "department3_zh": departments.get("zh_3"),
            "department3_en": departments.get("en_3"),
            
            # 聯絡方式
            **phones,
            "email": email,
            
            # 地址
            **addresses,
            
            # 備註
            "note1": note1,
            "note2": None,
            
            # 圖片與 OCR（Step3 再補）
            "front_image_path": None,
            "back_image_path": None,
            "front_ocr_text": None,
            "back_ocr_text": None,
            
            # 時間
            "created_at": created_at,
            "updated_at": updated_at,
            
            # 產業分類（後續處理）
            "industry_category": None,
            "classification_confidence": None,
            "classification_reason": None,
            "classified_at": None,
        }
    

    # ---------- Step 3: 從 card 裡抽出 front / back image ----------
    def _ensure_bytes(self, data) -> Optional[bytes]:
        """
        將 wcxf 中的圖片欄位統一轉成 bytes：
        - 若已是 bytes 直接回傳
        - 若是 base64 字串則嘗試 decode
        - 其他型態或失敗則回傳 None
        """
        if data is None:
            return None

        if isinstance(data, bytes):
            return data

        if isinstance(data, str):
            try:
                decoded = base64.b64decode(data, validate=True)
                return decoded if self._validate_image(decoded) else None
            except (base64.binascii.Error, ValueError) as e:
                logger.warning(f"Failed to decode base64 image data: {e}")
                return None

        logger.warning(f"Unexpected image data type: {type(data)}")
        return None
    

    def _validate_image(self, data: bytes) -> bool:
        """驗證是否為有效的圖片格式"""
        if not data or len(data) < 10:
            return False
        
        # 檢查常見圖片格式的文件頭 (magic numbers)
        image_signatures = {
            b'\xff\xd8\xff': 'JPEG',
            b'\x89PNG\r\n\x1a\n': 'PNG',
            b'GIF87a': 'GIF',
            b'GIF89a': 'GIF',
            b'BM': 'BMP',
        }
        
        for signature in image_signatures:
            if data.startswith(signature):
                return True
        
        logger.warning(f"Unknown image format (first 20 bytes): {data[:20]}")
        return False


    def _extract_images(self, card: dict) -> Dict[str, Optional[str]]:
        """
        Step 3：從 wcxf 名片資料中抽出正/反面圖片，存成檔案。
        
        - 不使用 WCXF 的 UniqueID
        - 每筆名片會產生一個新的 UUID（與原本後端的命名模式一致）
        - 儲存位置：settings.UPLOAD_DIR（預設 output/card_images）
        - 檔名格式：{uuid}_front.jpg / {uuid}_back.jpg

        Returns:
            包含 front_image_path, back_image_path 的字典
        """
        # ⭐ 先抓這張卡在 wcxf 裡的 UniqueID，方便之後寫 log 用
        wcxf_id = card.get("kWCXF_CDL1_UniqueID", "unknown")

        # 抽 raw bytes
        image_info = card.get("kWCXF_CDL1_Image", {}) or {}
        front_raw = image_info.get("kWCXF_CDL2_Image_Front")
        back_raw = image_info.get("kWCXF_CDL2_Image_Back")

        front_bytes = self._ensure_bytes(front_raw)
        back_bytes = self._ensure_bytes(back_raw)

        # 若兩張圖都沒有 → 直接回傳空欄位
        if not front_bytes and not back_bytes:
            logger.debug("No valid images found in card")
            return {
                "front_image_path": None,
                "back_image_path": None,
            }

        # 🔥 產生新的 UUID（與你們原本 backend 的圖片命名方式一致）
        file_uuid = str(uuid.uuid4())
        logger.info(f"[wcxf_id={wcxf_id}] Processing images for new card UUID: {file_uuid}")

        # 圖片存放路徑（程式會自動 mkdir）
        image_dir = self.card_image_dir
        image_dir.mkdir(parents=True, exist_ok=True)

        front_path = None
        back_path = None

        # 正面圖片
        if front_bytes:
            front_path = self._save_image(
                image_bytes=front_bytes,
                image_dir=image_dir,
                filename=f"{file_uuid}_front.jpg"
            )

        # 反面圖片
        if back_bytes:
            back_path = self._save_image(
                image_bytes=back_bytes,
                image_dir=image_dir,
                filename=f"{file_uuid}_back.jpg"
            )

        # 如果兩張圖都寫入失敗，返回 None
        if not front_path and not back_path:
            logger.warning(f"[wcxf_id={wcxf_id}] Failed to save any images for UUID: {file_uuid}")
            return {
                "front_image_path": None,
                "back_image_path": None,
            }

        return {
            "front_image_path": front_path,
            "back_image_path": back_path,
        }
    

    def _save_image(
        self,
        image_bytes: bytes,
        image_dir: Path,
        filename: str
    ) -> Optional[str]:
        """
        儲存圖片到檔案系統
        
        Args:
            image_bytes: 圖片的二進制數據
            image_dir: 儲存目錄
            filename: 檔案名稱
            
        Returns:
            成功時返回檔案完整路徑，失敗時返回 None
        """
        try:
            file_path = image_dir / filename
            file_path.write_bytes(image_bytes)
            logger.info(f"Successfully saved image: {file_path}")

            # ⭐ 關鍵：存進 DB 前把 Windows 的反斜線換成斜線
            db_path = str(file_path).replace("\\", "/")
            return str(db_path)
        except IOError as e:
            logger.error(f"Failed to write image {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error saving image {filename}: {e}")
            return None
        

    # ---------- Step 4: 主流程：解析 + 儲存圖片 + 寫入 DB ----------
    def run_import(self, db: Session) -> Dict:
        cards_raw = self._load_cards()
        card_dicts = []
        failed_records = []

        for idx, card in enumerate(cards_raw, start=1):
            fields = self._parse_single_card_fields(card)

            # 1. 檢查姓名（中/英至少有一個）
            if not fields.get("name_zh") and not fields.get("name_en"):
                failed_records.append({
                    "index": idx,
                    "reason": "缺少姓名（中文 & 英文皆無）",
                })
                continue

            # 2. ⭐ 這裡接 Step3：抽圖片 → 更新路徑
            image_paths = self._extract_images(card)
            fields["front_image_path"] = image_paths.get("front_image_path")
            fields["back_image_path"] = image_paths.get("back_image_path")

            # 3. 加入待寫入清單
            card_dicts.append(fields)

        # 4. 寫入資料庫（照你原本的 bulk_create 寫法）

        wrapped_models = [DictModelWrapper(fields) for fields in card_dicts]
        success, failed_db = bulk_create_cards(db, wrapped_models)

        return {
            "total": len(cards_raw),
            "imported": len(success),
            "failed": len(failed_records) + len(failed_db),
            "failed_missing_name": failed_records,
            "failed_db_insert": failed_db,
        }