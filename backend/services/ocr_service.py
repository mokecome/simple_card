import os
import uuid
import json
import asyncio
import re
import requests
import urllib3
import time
import random
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from io import BytesIO
import base64
from openai import OpenAI
from typing import Dict, Any, Optional, List
from collections import OrderedDict
from .card_detector import CardDetector
from .card_enhancement_service import CardEnhancementService

# 禁用 SSL 警�?
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OCRService:
    """OCR?��?類�??��??��??��?識別?�能"""
    
    def __init__(self):
        self.llm_api = LLMApi()
        # 初始化卡片增強服務
        self.card_enhancer = CardEnhancementService()
        # ?��??�面實�?顯示??6?��?�?
        self.CARD_FIELDS = [
            # ?�本資�? (8??
            "name_zh", "name_en", "company_name_zh", "company_name_en", "position_zh", "position_en", "position1_zh", "position1_en",
            # ?��?組�??��? (6??
            "department1_zh", "department1_en", "department2_zh", "department2_en", "department3_zh", "department3_en",
            # ?�絡資�? (5?? 
            "mobile_phone", "company_phone1", "company_phone2", "email", "line_id",
            # ?��?資�? (4??
            "company_address1_zh", "company_address1_en", "company_address2_zh", "company_address2_en",
            # ?�註資�? (2??
            "note1", "note2"
        ]
        self.BATCH_OCR_API_URL = os.getenv("OCR_BATCH_API_URL", "https://local_llm.star-bit.io/api/card")
        self.IMAGE_EXTS = (".jpg", ".jpeg", ".png")
    
    async def ocr_image(self, image_content: bytes) -> str:
        """OCR?��?識別"""
        try:
            # 保�??��??�件
            temp_filename = f"{uuid.uuid4()}.jpg"
            temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
            
            with open(temp_path, "wb") as f:
                f.write(image_content)
            
            # ?��??��?
            enhanced_path = process_image(temp_path)
            if not enhanced_path:
                return "?��??��?失�?"
            
            # OCR識別
            result = self.llm_api.ocr_generate(enhanced_path)
            
            # 清�??��??�件
            try:
                os.remove(temp_path)
                if enhanced_path != temp_path:
                    os.remove(enhanced_path)
            except Exception as e:
                print(f"清�??��??�件?�誤: {e}")
            
            return result or "OCR識別失�?"
            
        except Exception as e:
            print(f"OCR?��??�誤: {e}")
            return "等�??��??��?��"
    
    def parse_ocr_to_fields(self, ocr_text: str, side: str) -> Dict[str, str]:
        """�??OCR?��??��?準�?欄�?"""
        try:
            # 使用統�??�英?��?位�??�示詞�??��??��??�誤
            prompt = '''你是一?��??�助?��??��??��??��??��?訊�?並輸?��?準JSON?��???
請�??�以下�?位�?�?沒�??��?位設?�空字串):

{
  "name": "中�?姓�?",
  "name_en": "English Name", 
  "company_name": "中�??�司?�稱",
  "company_name_en": "English Company Name",
  "position": "中�??��?",
  "position_en": "English Position",
  "position1": "中�??��?1", 
  "position1_en": "English Position1",
  "department1": "中�??��?1",
  "department1_en": "English Department1",
  "department2": "中�??��?2", 
  "department2_en": "English Department2",
  "department3": "中�??��?3",
  "department3_en": "English Department3", 
  "mobile_phone": "?��??�碼",
  "company_phone1": "?�司?�話1",
  "company_phone2": "?�司?�話2",
  "email": "?��??�件",
  "line_id": "Line ID",
  "company_address1": "中�??��?1",
  "company_address1_en": "English Address1", 
  "company_address2": "中�??��?2",
  "company_address2_en": "English Address2",
  "note1": "?�註1",
  "note2": "?�註2"
}

請解?�以下OCR?��?，只返�?JSON?��?: ''' + ocr_text
            
            print(f"[DEBUG] OCR�???�示�? {prompt[:200]}...")
            result = self.llm_api.ocr_generate("", prompt)
            print(f"[DEBUG] LLM返�?結�?: {result[:300]}...")
            
            # ?�試�??JSON結�?
            import json
            try:
                # 清�??�能?�Markdown?��?
                clean_result = result.strip()
                if clean_result.startswith("```json"):
                    clean_result = clean_result[7:]
                if clean_result.endswith("```"):
                    clean_result = clean_result[:-3]
                clean_result = clean_result.strip()
                
                parsed = json.loads(clean_result)
                print(f"[DEBUG] JSON�???��?，�?位數?? {len(parsed)}")
                
                # 驗�?並�??��?�?
                valid_fields = {
                    "name", "name_en", "company_name", "company_name_en", 
                    "position", "position_en", "position1", "position1_en",
                    "department1", "department1_en", "department2", "department2_en", 
                    "department3", "department3_en", "mobile_phone", "company_phone1", 
                    "company_phone2", "email", "line_id", "company_address1", 
                    "company_address1_en", "company_address2", "company_address2_en",
                    "note1", "note2"
                }
                
                # ?��??��??��?位�?移除空�?
                cleaned_result = {}
                for key, value in parsed.items():
                    if key in valid_fields and value and str(value).strip():
                        cleaned_result[key] = str(value).strip()
                
                print(f"[DEBUG] 清�?後�??��?�? {list(cleaned_result.keys())}")
                return cleaned_result
                
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON�??失�?: {e}")
                print(f"[ERROR] ?��?返�??�容: {result}")
                return {
                    "note1": f"JSON�??失�?: {str(e)}", 
                    "note2": f"?��?OCR?��?: {ocr_text[:200]}..."
                }
                
        except Exception as e:
            print(f"[ERROR] 欄�?�???�誤: {e}")
            return {
                "note1": f"�???��??�誤: {str(e)}", 
                "note2": f"?��?OCR?��?: {ocr_text[:200]}..."
            }
    
    def log_message(self, message):
        """輸出信息?�控?�台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
    
    def is_chinese(self, char):
        """檢查字�??�否?�中?��?"""
        return '\u4e00' <= char <= '\u9fff'
    
    def filter_data(self, merged_data):
        """?�濾欄�??�容，中?��?位只?�中?��??��?欄�??��??��?/符�?"""
        
        # 不�?要�?濾�?欄�?：聯絡�?訊�??�註
        ignore_filter = ["mobile_phone", "company_phone1", "company_phone2", "email", "line_id", "note1", "note2"]
        
        # ?��?欄�??��?識符
        en_identifiers = ("_en",)

        filtered_result = OrderedDict()

        for key, value in merged_data.items():
            if key in ignore_filter:
                filtered_result[key] = value
                continue

            if any(id in key for id in en_identifiers):
                # ?��?欄�?：移?�中?��?
                filtered_result[key] = "".join(c for c in str(value) if not self.is_chinese(c)).strip()
            else:
                # 中�?欄�?：只保�?中�?�?
                filtered_result[key] = "".join(c for c in str(value) if self.is_chinese(c)).strip()
                
        return filtered_result
    
    def batch_ocr_image(self, image_path, max_retries=3):
        """?��?OCR?��??��?，�??��?試�???""
        filename = os.path.basename(image_path)
        
        for attempt in range(max_retries):
            try:
                self.log_message(f"?��?OCR?��?：{filename} (?�試 {attempt + 1}/{max_retries})")
                
                with open(image_path, "rb") as f:
                    files = {"file": (filename, f, "image/jpeg")}
                    
                    # ?��??�試次數調整超�??��?
                    timeout_duration = 10 + (attempt * 10)  # 10, 20, 30�?
                    
                    resp = requests.post(self.BATCH_OCR_API_URL, files=files, 
                                       verify=False, timeout=timeout_duration)
                    resp.raise_for_status()
                    
                    # 從�??��? JSON 中�???'result' 欄�?
                    result_json = resp.json()
                    text_content = result_json.get("result", result_json.get("text", "{}"))
                    
                    # 檢查?��??�否?�空
                    if not text_content or text_content.strip() in ["{}", ""]:
                        self.log_message(f"API返�?空內容�?{filename}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return {}
                    
                    # 增強?�JSON?��??�輯
                    if "```json" in text_content:
                        start = text_content.find("```json") + len("```json")
                        end = text_content.find("```", start)
                        if end != -1:
                            text_content = text_content[start:end].strip()
                        else:
                            text_content = text_content[start:].strip()
                    elif text_content.startswith("?��??��?"):
                        if "```json" in text_content:
                            start = text_content.find("```json") + len("```json")
                            end = text_content.find("```", start)
                            if end != -1:
                                text_content = text_content[start:end].strip()
                    
                    # �?? JSON 字串
                    parsed_result = json.loads(text_content)
                    self.log_message(f"OCR?��??��?：{filename}")
                    return parsed_result
                    
            except requests.exceptions.Timeout:
                self.log_message(f"請�?超�?：{filename} (?�試 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except requests.exceptions.RequestException as e:
                self.log_message(f"請�??�誤：{filename}，錯誤�?{e} (?�試 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except json.JSONDecodeError as e:
                self.log_message(f"JSON �??失�?：{filename}，錯誤�?{e}")
                if 'text_content' in locals():
                    self.log_message(f"?��??�本：{text_content[:200]}...")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except Exception as e:
                self.log_message(f"OCR?��??�常：{filename}，錯誤�?{e} (?�試 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        # 所有重試都失敗
        self.log_message(f"OCR處理完全失敗: {filename}, 已重試 {max_retries} 次")
        return {}
    
    def merge_fields(self, results):
        """多張欄位合併, 取首個非空值"""
        merged = OrderedDict((k, "") for k in self.CARD_FIELDS)
        for field in self.CARD_FIELDS:
            for r in results:
                v = r.get(field, "")
                if v and not merged[field]:
                    merged[field] = str(v)
        return merged
    
    def process_single_image(self, image_path):
        """處理單張圖片"""
        try:
            # 執行OCR
            ocr_result = self.batch_ocr_image(image_path)
            
            if not ocr_result:
                return None
            
            # 填充欄位資料
            processed_result = OrderedDict((k, "") for k in self.CARD_FIELDS)
            for field in self.CARD_FIELDS:
                if field in ocr_result:
                    processed_result[field] = str(ocr_result[field])
            
            # 過濾空值
            filtered_result = self.filter_data(processed_result)
            
            return filtered_result
            
        except Exception as e:
            self.log_message(f"處理單張圖片失敗：{image_path}，錯誤：{e}")
            return None
    
    async def batch_process_directory(self, base_dir, progress_callback=None):
        """批量處理目錄下的所有圖片"""
        try:
            if not os.path.exists(base_dir):
                self.log_message(f"目錄不存在：{base_dir}")
                return []
            
            # 找出所有圖片檔案
            all_images = []
            for file in os.listdir(base_dir):
                if file.lower().endswith(self.IMAGE_EXTS):
                    all_images.append(os.path.join(base_dir, file))
            
            self.log_message(f"開始批量處理，總共 {len(all_images)} 張圖片")
            
            results = []
            for i, image_path in enumerate(all_images):
                try:
                    result = self.process_single_image(image_path)
                    
                    if result:
                        results.append(result)
                        self.log_message(f"處理 {os.path.basename(image_path)} 成功 ({i+1}/{len(all_images)})")
                    else:
                        self.log_message(f"處理 {os.path.basename(image_path)} 失敗 ({i+1}/{len(all_images)})")
                    
                    # 進度回調
                    if progress_callback:
                        await progress_callback({
                            'current': i + 1,
                            'total': len(all_images),
                            'filename': os.path.basename(image_path),
                            'success': result is not None,
                            'result': result
                        })
                    
                    # 隨機延遲
                    sleep_time = random.uniform(0.5, 1)
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    self.log_message(f"處理圖片 {os.path.basename(image_path)} 時發生異常：{e}")
            
            self.log_message(f"批量處理完成，成功處理 {len(results)} 張圖片")
            return results
            
        except Exception as e:
            self.log_message(f"批量處理失敗：{e}")
            return []

# OCR服務不需要matplotlib字體設置，已移除

# 背景任務管理
cleanup_task = None

async def cleanup_expired_sessions():
    """定期清理過期會話並更新使用記錄"""
    while True:
        try:
            # 檢查過期中的會話
            expired_sessions = []
            current_time = datetime.now()
            
            for session_id, session in serial_sessions.items():
                expires_at = datetime.fromisoformat(session["expires_at"])
                if current_time >= expires_at:
                    expired_sessions.append(session_id)
            
            # 清理過期會話並更新使用記錄
            for session_id in expired_sessions:
                session = serial_sessions[session_id]
                serial_code = session.get("serial_code")
                if serial_code:
                    update_serial_usage(serial_code, "expire", session_id)
                    print(f"[OCR] ?�話 {session_id[:8]}... 已�??�並?�新記�?")
                del serial_sessions[session_id]
            
            # 檢查?�置?�件中�?活�??�話
            config = load_serial_config()
            config_updated = False
            
            for serial in config.get("valid_serials", []):
                for record in serial.get("usage_records", []):
                    if record.get("status") == "active":
                        # 檢查?�話?�否?�該?��?
                        started_at = datetime.fromisoformat(record["started_at"])
                        duration_minutes = serial.get("duration_minutes", config.get("default_duration", 15))
                        expected_end = started_at + timedelta(minutes=duration_minutes)
                        
                        if current_time >= expected_end:
                            record["ended_at"] = current_time.isoformat()
                            record["status"] = "expired"
                            config_updated = True
                            print(f"[OCR] 序�? {serial['code']} ?��?話已?��?")
            
            # 保�??�新
            if config_updated:
                save_serial_config(config)
                
        except Exception as e:
            print(f"[OCR] 清理會話錯誤: {e}")
        
        # 每30秒執行一次
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    global cleanup_task
    # 啟動時
    cleanup_task = asyncio.create_task(cleanup_expired_sessions())
    print("[OCR] 啟動會話清理背景任務")
    yield
    # 關閉時
    if cleanup_task:
        cleanup_task.cancel()
        print("[OCR] 停止會話清理背景任務")

app = FastAPI(title="OCR服務 - 序號管理", lifespan=lifespan)

# 配置
OCR_PORT = int(os.getenv("OCR_PORT", "8504"))
OCR_HOST = os.getenv("OCR_HOST", "0.0.0.0")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
CONFIG_FILE = os.getenv("CONFIG_FILE", "config/serials.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ?��?中�?序�?使用?�??
serial_sessions = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 序號管理函數
def load_serial_config():
    """載入序號配置檔案"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 確保使用記錄結構存在
        for serial in config.get("valid_serials", []):
            if "usage_records" not in serial:
                serial["usage_records"] = []
                
        # 確�?設�?存在
        if "serial_usage_settings" not in config:
            config["serial_usage_settings"] = {
                "enable_usage_tracking": True,
                "single_use_mode": False,
                "concurrent_sessions_limit": 1,
                "usage_cooldown_minutes": 0
            }
            
        return config
    except FileNotFoundError:
        return {
            "valid_serials": [],
            "admin_password": "admin123",
            "default_duration": 15,
            "max_duration": 120,
            "serial_usage_settings": {
                "enable_usage_tracking": True,
                "single_use_mode": False,
                "concurrent_sessions_limit": 1,
                "usage_cooldown_minutes": 0
            }
        }
    except Exception as e:
        print(f"載入?�置?�件?�誤: {e}")
        return {
            "valid_serials": [], 
            "admin_password": "admin123", 
            "default_duration": 15, 
            "max_duration": 120,
            "serial_usage_settings": {
                "enable_usage_tracking": True,
                "single_use_mode": False,
                "concurrent_sessions_limit": 1,
                "usage_cooldown_minutes": 0
            }
        }

def save_serial_config(config):
    """保�?序�??�置?�件"""
    try:
        # 確�??��?存在
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保�??�置?�件?�誤: {e}")
        return False

def update_serial_usage(serial_code: str, action: str, session_id: str = None):
    """?�新序�?使用記�?"""
    config = load_serial_config()
    settings = config.get("serial_usage_settings", {})
    
    if not settings.get("enable_usage_tracking", True):
        return True
    
    for serial in config.get("valid_serials", []):
        if serial["code"] == serial_code:
            if "usage_records" not in serial:
                serial["usage_records"] = []
            
            now = datetime.now()
            
            if action == "start":
                # 檢查併發?�制
                concurrent_limit = settings.get("concurrent_sessions_limit", 1)
                active_sessions = [
                    record for record in serial["usage_records"]
                    if record.get("status") == "active"
                ]
                
                if len(active_sessions) >= concurrent_limit:
                    return False
                
                # 檢查?�卻?��?
                cooldown_minutes = settings.get("usage_cooldown_minutes", 0)
                if cooldown_minutes > 0:
                    recent_usage = [
                        record for record in serial["usage_records"]
                        if record.get("ended_at") and 
                        (now - datetime.fromisoformat(record["ended_at"])).total_seconds() < cooldown_minutes * 60
                    ]
                    
                    if recent_usage:
                        return False
                
                # 添�??��?使用記�?
                usage_record = {
                    "session_id": session_id,
                    "started_at": now.isoformat(),
                    "status": "active",
                    "ip_address": "unknown"  # ?�以從�?求中?��?
                }
                serial["usage_records"].append(usage_record)
                
            elif action == "end":
                # 結�?使用記�?
                for record in serial["usage_records"]:
                    if record.get("session_id") == session_id and record.get("status") == "active":
                        record["ended_at"] = now.isoformat()
                        record["status"] = "completed"
                        break
            
            elif action == "expire":
                # 標�??��???
                for record in serial["usage_records"]:
                    if record.get("session_id") == session_id and record.get("status") == "active":
                        record["ended_at"] = now.isoformat()
                        record["status"] = "expired"
                        break
            
            # 保�??�置
            save_serial_config(config)
            return True
    
    return False

def check_serial_availability(serial_code: str) -> dict:
    """檢查序�??�用??""
    config = load_serial_config()
    settings = config.get("serial_usage_settings", {})
    
    for serial in config.get("valid_serials", []):
        if serial["code"] == serial_code:
            # 檢查?�本?��???
            if serial.get("expires"):
                try:
                    expires_date = datetime.strptime(serial["expires"], "%Y-%m-%d")
                    if datetime.now() > expires_date:
                        return {"available": False, "reason": "序�?已�???}
                except:
                    pass
            
            # 檢查?�次使用模�?
            if settings.get("single_use_mode", False):
                completed_usage = [
                    record for record in serial.get("usage_records", [])
                    if record.get("status") in ["completed", "expired", "force_ended"]
                ]
                if completed_usage:
                    return {"available": False, "reason": "序�?已被使用??}
            
            # 檢查併發?�制
            concurrent_limit = settings.get("concurrent_sessions_limit", 1)
            active_sessions = [
                record for record in serial.get("usage_records", [])
                if record.get("status") == "active"
            ]
            
            if len(active_sessions) >= concurrent_limit:
                return {"available": False, "reason": "序�?�?��使用�?}
            
            # 檢查?�卻?��?
            cooldown_minutes = settings.get("usage_cooldown_minutes", 0)
            if cooldown_minutes > 0:
                now = datetime.now()
                recent_usage = [
                    record for record in serial.get("usage_records", [])
                    if record.get("ended_at") and 
                    (now - datetime.fromisoformat(record["ended_at"])).total_seconds() < cooldown_minutes * 60
                ]
                
                if recent_usage:
                    return {"available": False, "reason": f"序�??�冷?��?中�?請�?�?{cooldown_minutes} ?��?"}
            
            return {"available": True}
    
    return {"available": False, "reason": "?��??��???}

def validate_serial(serial_code: str) -> Dict[str, Any]:
    """驗�?序�??�否?��?"""
    # 首�?檢查?�用??
    availability = check_serial_availability(serial_code)
    if not availability["available"]:
        return {"valid": False, "error": availability["reason"]}
    
    config = load_serial_config()
    
    for serial in config.get("valid_serials", []):
        if serial["code"] == serial_code:
            duration = serial.get("duration_minutes", config.get("default_duration", 15))
            return {
                "valid": True,
                "duration_minutes": duration,
                "description": serial.get("description", ""),
                "expires_at": (datetime.now() + timedelta(minutes=duration)).isoformat()
            }
    
    return {"valid": False, "error": "?��??��???}

def get_session_status(session_id: str) -> Dict[str, Any]:
    """?��??�話?�??""
    if session_id not in serial_sessions:
        return {"active": False, "remaining_seconds": 0}
    
    session = serial_sessions[session_id]
    now = datetime.now()
    expires_at = datetime.fromisoformat(session["expires_at"])
    
    remaining = (expires_at - now).total_seconds()
    
    # 增�?5秒寬容�??��??��?網絡延遲導致?��??��?�?
    if remaining <= -5:
        # ?�話已確實�??��?清�?並更?�使?��???
        print(f"?�話 {session_id} 已�??��??��??��?: {remaining:.1f}�?)
        
        # ?�新使用記�??��???
        serial_code = session.get("serial_code")
        if serial_code:
            update_serial_usage(serial_code, "expire", session_id)
        
        del serial_sessions[session_id]
        return {"active": False, "remaining_seconds": 0}
    
    # 如�??��??��?小於等於0但在寬容範�??��?返�?0但�??�active
    actual_remaining = max(0, int(remaining))
    
    return {
        "active": True,
        "remaining_seconds": actual_remaining,
        "serial_code": session.get("serial_code", ""),
        "expires_at": session["expires_at"]
    }

class LLMApi:
    def __init__(self, model_path="/data1/models/OpenGVLab/InternVL3-8B"):
        self.model_path = model_path
        self.client = OpenAI(api_key=os.getenv("OCR_API_KEY", "YOUR_API_KEY"), base_url=os.getenv("OCR_API_URL", "http://0.0.0.0:23333/v1"))

    def ocr_generate(self, image_path, prompt="Only return the OCR result and don't provide any other explanations."):
        try:
            image_url = f"{os.path.abspath(image_path)}"
            model_name = self.client.models.list().data[0].id
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[{
                    'role': 'user',
                    'content': [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': image_url}}]
                }],
                temperature=0
            )
            print(response.choices[0].message.content)
            return response.choices[0].message.content
        except Exception as e:
            print(f"OCR?��???��失�?: {e}")
            # ?��??�OCR?��?不可?��?，�??�模?�數?�用?�測�?
            return self._get_mock_ocr_result(prompt)
    
    def _get_mock_ocr_result(self, prompt):
        """?��?模擬OCR結�?"""
        print("[DEBUG] OCR?��?不可?��?使用模擬?��?")
        
        # 檢查?�否?��??��??��?�?
        if "?��??��?" in prompt or "JSON?��?" in prompt:
            # 返�?標�?JSON?��??�模?��??�數??
            return '''{
  "name": "張�???,
  "name_en": "Zhang Xiaoming", 
  "company_name": "?�新科�??�份?��??�司",
  "company_name_en": "Innovation Technology Co., Ltd.",
  "position": "資深工�?�?,
  "position_en": "Senior Engineer",
  "position1": "專�?經�?",
  "position1_en": "Project Manager",
  "department1": "?�發??,
  "department1_en": "R&D Department",
  "department2": "軟�??�發�?, 
  "department2_en": "Software Development Group",
  "department3": "",
  "department3_en": "",
  "mobile_phone": "0912-345-678",
  "company_phone1": "02-2712-3456",
  "company_phone2": "",
  "email": "zhang@innovation-tech.com",
  "line_id": "@innovation_tech",
  "company_address1": "?��?市信義�?信義路�?�???,
  "company_address1_en": "No. 7, Sec. 5, Xinyi Rd., Xinyi Dist., Taipei City",
  "company_address2": "",
  "company_address2_en": "",
  "note1": "模擬OCR識別結�? - 測試模�?",
  "note2": ""
}'''
        else:
            # 返�?一?�OCR?��?識別結�?
            return """張�???Zhang Xiaoming
資深工�?�?/ 專�?經�?
Senior Engineer / Project Manager
?�新科�??�份?��??�司
Innovation Technology Co., Ltd.
?�發??軟�??�發�?
R&D Department Software Development Group
?�話: 02-2712-3456
?��?: 0912-345-678
Email: zhang@innovation-tech.com
Line ID: @innovation_tech
?��?: ?��?市信義�?信義路�?�???
No. 7, Sec. 5, Xinyi Rd., Xinyi Dist., Taipei City

???�是模擬OCR識別結�?，實?�使?��??�要�?置OCR?��?"""

def process_image(image_path):
    """圖片處理，提高OCR識別率 - 整合智能增強功能"""
    try:
        # 優先嘗試使用智能卡片增強
        use_card_enhancement = os.getenv("USE_CARD_ENHANCEMENT", "true").lower() == "true"
        
        if use_card_enhancement:
            try:
                # 使用智能卡片增強服務
                enhancer = CardEnhancementService()
                success, enhanced_path = enhancer.process_image(
                    image_path, 
                    auto_detect=True,
                    scale_factor=3
                )
                
                if success and enhanced_path and enhanced_path != image_path:
                    print(f"智能卡片增強成功: {enhanced_path}")
                    return enhanced_path
                else:
                    print(f"智能增強失敗或未啟用，使用傳統方法")
                    # 繼續使用傳統方法
            except Exception as enhancement_error:
                print(f"智能增強異常，使用傳統方法: {enhancement_error}")
                # 繼續使用傳統方法
        
        # 備選方案：使用OpenCV檢測
        use_opencv = os.getenv("USE_OPENCV", "true").lower() == "true"
        
        if use_opencv:
            try:
                # 使用OpenCV檢測器
                detector = CardDetector()
                success, enhanced_path = detector.process_card_image(image_path)
                
                if success:
                    print(f"OpenCV處理成功: {enhanced_path}")
                    return enhanced_path
                else:
                    print(f"OpenCV處理失敗，使用傳統方法: {enhanced_path}")
                    # 繼續使用傳統方法
            except Exception as opencv_error:
                print(f"OpenCV處理異常，使用傳統方法: {opencv_error}")
                # 繼續使用傳統方法
        
        # 傳統PIL處理方法（保留作為最後備選）
        with open(image_path, "rb") as f:
            image_data = f.read()
        image = Image.open(BytesIO(image_data))

        if image.mode == "RGBA":
            image = image.convert("RGB")

        dpi = image.info.get("dpi", (100, 100))
        x_dpi = dpi[0]

        # 如果DPI大於100，不需要增強
        if x_dpi > 100:
            return image_path

        # 基礎增強：放大以提高清晰度
        scale_factor = 1.5  # 較小的放大倍率
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        enhanced_image = image.resize((new_width, new_height), Image.LANCZOS)
        enhanced_path = os.path.splitext(image_path)[0] + "_enhanced.jpg"
        enhanced_image.save(enhanced_path, "JPEG", quality=95, dpi=(200, 200))  # 高質量和DPI
        return enhanced_path
    except Exception as e:
        print(f"圖片處理錯誤: {e}")
        return image_path  # 返回原始路徑而不是None

def allowed_file(filename):
    """檢查?�件?��??�是?��?�?""
    return filename.lower().endswith((".png", ".jpg", ".jpeg"))

def write_file(path, content):
    """寫入?�件?�容"""
    with open(path, "wb") as f:
        f.write(content)

def get_image_base64(image_path):
    """將�??��??�為Base64編碼"""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        print(f"?��??��?Base64?�誤: {e}")
        return None

# ==================== API 路由 ====================

@app.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...), session_id: str = Form(None)):
    """OCR API - ?�要�??��?序�??�話"""
    
    # 檢查?�話權�?
    if not session_id:
        raise HTTPException(status_code=401, detail="?�要�??��?序�??�話")
    
    session_status = get_session_status(session_id)
    if not session_status["active"]:
        raise HTTPException(status_code=401, detail="序�??�話已�??��?請�??��?�?)
    
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="?�支??JPG/PNG ?��?")

    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    content = await file.read()
    write_file(path, content)

    enhanced_path = process_image(path)
    if not enhanced_path:
        raise HTTPException(status_code=500, detail="?��??��?失�?")

    llm = LLMApi()
    result = llm.ocr_generate(enhanced_path, prompt="Only return the OCR result and don't provide any other explanations.")
    
    # 清�??��??�件
    try:
        os.remove(path)
        if enhanced_path != path:
            os.remove(enhanced_path)
    except Exception as e:
        print(f"清�?檔�??�誤: {e}")
    
    return { 
        "result": result,
        "remaining_seconds": session_status["remaining_seconds"]
    }

@app.post("/api/card")
async def api_card(file: UploadFile = File(...)):
    """?��?識別API"""
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="?�支??JPG/PNG ?��?")

    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    content = await file.read()
    write_file(path, content)

    enhanced_path = process_image(path)
    if not enhanced_path:
        raise HTTPException(status_code=500, detail="?��??��?失�?")

    llm = LLMApi()
    result = llm.ocr_generate(enhanced_path, prompt='''你是一?��??�助???��??��??��??�?�資�?["姓�?","name_en","?�司?�稱","company_name_en","?��?1","?��?2","position_en","position1_en","?��?1(?��?1)","?��?2(?��?2)","?��?3(?��?3)","Department1","Department2","Department3","?��?","?�司?�話1","?�司?�話2","Email","Line ID","?�司?��?一","?�司?��?�?,"company_address1_en","company_address2_en","note1","note2"]
                    ,?��?如�??��?(沒�??�到?�空字串,?��?識別?�放?��?�?:
                    {  
                      "姓�?": "?��???,  
                      "name_en": "Chen Xiaohua",
                      "?�司?�稱": "?�新科�??�份?��??�司",
                      "company_name_en": "Innovation Technology Co., Ltd.",    
                      "?��?": "工�?�?,
                      "?��?1": "資深工�?�?,
                      "position_en": "Engineer",
                      "position1_en": "Senior Engineer",    
                      "?��?1": "機�??��?業群",
                      "?��?2": "?��?設�???,
                      "?��?3": "",
                      "Department1": "M.O.E.B.G",
                      "Department2": "Electronic Design Dept.",
                      "Department3": "",
                      "?��?": "135-1234-5678",  
                      "?�司?�話1": "02-2712-3456-803",  
                      "?�司?�話2": "02-2712-1234-803",  
                      "Email": "chen@tech-innovation.com",  
                      "Line ID": "@tech_innovation",  
                      "?�司?��?一": "?��?市大安�??�復?�路100??,  
                      "?�司?��?�?: "",
                      "company_address1_en": "No. 100, Guangfu South Road, Da'an District, Taipei City",  
                      "company_address2_en": "",
                      "note1": "",
                      "note2": ""    
                    }''')
    
    # 清�?檔�?
    try:
        os.remove(path)
        if enhanced_path != path:
            os.remove(enhanced_path)
    except Exception as e:
        print(f"清�?檔�??�誤: {e}")
    
    return {"result": result}

# 序�?驗�?API
@app.post("/api/validate-serial")
async def validate_serial_api(serial_code: str = Form(...)):
    """驗�?序�?並創建�?�?""
    validation_result = validate_serial(serial_code)
    
    if not validation_result["valid"]:
        raise HTTPException(status_code=400, detail=validation_result["error"])
    
    # ?�建?�話
    session_id = str(uuid.uuid4())
    
    # 記�?序�?使用?��?
    if not update_serial_usage(serial_code, "start", session_id):
        raise HTTPException(status_code=400, detail="序�??��?不可使用")
    
    serial_sessions[session_id] = {
        "serial_code": serial_code,
        "expires_at": validation_result["expires_at"],
        "duration_minutes": validation_result["duration_minutes"],
        "created_at": datetime.now().isoformat()
    }
    
    # 計�??��??��??��?
    duration_seconds = validation_result["duration_minutes"] * 60
    
    print(f"??序�?驗�??��? - ?�話ID: {session_id[:8]}..., 序�?: {serial_code}, ?�長: {validation_result['duration_minutes']}?��?")
    
    return {
        "success": True,
        "session_id": session_id,
        "duration_minutes": validation_result["duration_minutes"],
        "remaining_time": duration_seconds,
        "expires_at": validation_result["expires_at"],
        "description": validation_result.get("description", "")
    }

@app.get("/api/check-status")
async def check_status_api(session_id: str):
    """檢查?�話?�??""
    if not session_id:
        raise HTTPException(status_code=400, detail="缺�??�話ID")
    
    status = get_session_status(session_id)
    
    # 記�??�?�檢?�日�?
    if status["active"]:
        remaining_min = status["remaining_seconds"] // 60
        remaining_sec = status["remaining_seconds"] % 60
        print(f"?? ?�話?�?�檢??- ID: {session_id[:8]}..., ?��?: {remaining_min:02d}:{remaining_sec:02d}")
    else:
        print(f"?��? ?�話已失??- ID: {session_id[:8]}...")
    
    return status

# ?�康檢查
@app.get("/health")
async def health_check():
    """?��??�康檢查"""
    return {
        "status": "healthy",
        "service": "OCR?��?",
        "port": OCR_PORT,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print(f"?? OCR?��??��?�?..")
    print(f"?? ?�戶訪�??��?: http://{OCR_HOST}:{OCR_PORT}")
    print(f"?? 序�?驗�??�OCR?�能已就�?)
    uvicorn.run(app, host=OCR_HOST, port=OCR_PORT) 