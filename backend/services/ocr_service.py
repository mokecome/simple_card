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

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OCRService:
    """OCR Service class for business card text recognition"""
    
    def __init__(self):
        self.llm_api = LLMApi()
        # Initialize card enhancement service
        self.card_enhancer = CardEnhancementService()
        # Frontend implementation displays 25 fields
        self.CARD_FIELDS = [
            # Basic information (8 fields)
            "name_zh", "name_en", "company_name_zh", "company_name_en", "position_zh", "position_en", "position1_zh", "position1_en",
            # Department/Group info (6 fields)
            "department1_zh", "department1_en", "department2_zh", "department2_en", "department3_zh", "department3_en",
            # Contact information (5 fields)
            "mobile_phone", "company_phone1", "company_phone2", "email", "line_id",
            # Address information (4 fields)
            "company_address1_zh", "company_address1_en", "company_address2_zh", "company_address2_en",
            # Note information (2 fields)
            "note1", "note2"
        ]
        self.BATCH_OCR_API_URL = os.getenv("OCR_BATCH_API_URL", "https://local_llm.star-bit.io/api/card")
        self.IMAGE_EXTS = (".jpg", ".jpeg", ".png")
    
    async def ocr_image(self, image_content: bytes) -> str:
        """OCR text recognition - Use local OCR API only"""
        try:
            # Save temporary file
            temp_filename = f"{uuid.uuid4()}.jpg"
            temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
            
            with open(temp_path, "wb") as f:
                f.write(image_content)
            
            # Use local OCR with structured JSON prompt (same as external service)
            structured_prompt = '''你是專業的名片資訊提取助手。請從圖片中識別名片上的所有文字資訊，並按照以下JSON格式返回結構化數據。

重要：請從實際圖片內容中提取真實資訊，絕對不要使用下方範例中的數據。

請仔細識別以下25個欄位（如果某個欄位在名片上沒有找到，請設為空字符串）：

【個人資訊】(8個欄位)
- 姓名（中文）
- 姓名（英文）
- 職位（中文）
- 職位（英文）
- 職位1（中文）
- 職位1（英文）
- 公司名稱（中文）
- 公司名稱（英文）

【部門組織架構】(6個欄位)
- 部門1（中文）
- 部門1（英文）
- 部門2（中文）
- 部門2（英文）
- 部門3（中文）
- 部門3（英文）

【聯絡方式】(5個欄位)
- 手機號碼
- 公司電話1
- 公司電話2
- 電子郵件
- Line ID

【地址資訊】(4個欄位)
- 公司地址1（中文）
- 公司地址1（英文）
- 公司地址2（中文）
- 公司地址2（英文）

【備註資訊】(2個欄位)
- 備註1
- 備註2

請嚴格按照以下JSON格式返回，使用正確的欄位名稱，填入從圖片中實際識別到的內容：

{
  "name_zh": "[從圖片識別的中文姓名]",
  "name_en": "[從圖片識別的英文姓名]",
  "company_name_zh": "[從圖片識別的中文公司名稱]",
  "company_name_en": "[從圖片識別的英文公司名稱]",
  "position_zh": "[從圖片識別的中文職位]",
  "position_en": "[從圖片識別的英文職位]",
  "position1_zh": "[從圖片識別的中文職位1]",
  "position1_en": "[從圖片識別的英文職位1]",
  "department1_zh": "[從圖片識別的中文部門1]",
  "department1_en": "[從圖片識別的英文部門1]",
  "department2_zh": "[從圖片識別的中文部門2]",
  "department2_en": "[從圖片識別的英文部門2]",
  "department3_zh": "[從圖片識別的中文部門3]",
  "department3_en": "[從圖片識別的英文部門3]",
  "mobile_phone": "[從圖片識別的手機號碼]",
  "company_phone1": "[從圖片識別的公司電話1]",
  "company_phone2": "[從圖片識別的公司電話2]",
  "email": "[從圖片識別的電子郵件]",
  "line_id": "[從圖片識別的Line ID]",
  "company_address1_zh": "[從圖片識別的中文地址1]",
  "company_address1_en": "[從圖片識別的英文地址1]",
  "company_address2_zh": "[從圖片識別的中文地址2]",
  "company_address2_en": "[從圖片識別的英文地址2]",
  "note1": "[從圖片識別的備註1]",
  "note2": "[從圖片識別的備註2]"
}

注意：請將方括號及其內容替換為實際識別到的資訊，若某欄位沒有內容則填入空字符串""。絕對不要使用上方的範例數據！'''
            print(f"[OCR] Using local OCR API with structured prompt for: {temp_path}")
            result = self.llm_api.ocr_generate(temp_path, structured_prompt)
            
            # If original fails, try enhanced image
            if not result or len(result.strip()) < 20:
                print(f"[OCR] Local OCR result too short, trying enhanced image")
                enhanced_path = process_image(temp_path)
                if enhanced_path and enhanced_path != temp_path:
                    result = self.llm_api.ocr_generate(enhanced_path, structured_prompt)
                    # Clean up enhanced image
                    try:
                        os.remove(enhanced_path)
                    except:
                        pass
            
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"File cleanup error: {e}")
            
            return result or "OCR recognition failed"
            
        except Exception as e:
            print(f"OCR processing error: {e}")
            return "Please wait for processing"
    

    def parse_ocr_to_fields(self, ocr_text: str, side: str) -> Dict[str, str]:
        """Parse OCR text to standard fields"""
        try:
            print(f"[DEBUG] Starting OCR field parsing for side: {side}")
            print(f"[DEBUG] OCR text length: {len(ocr_text)}")
            
            # Check if OCR text is already in JSON format (from local or external OCR)
            try:
                import json
                # Try to extract JSON from the text (might have markdown formatting)
                text_to_parse = ocr_text.strip()
                
                # Remove markdown formatting if present
                if "```json" in text_to_parse:
                    start = text_to_parse.find("```json") + len("```json")
                    end = text_to_parse.find("```", start)
                    if end != -1:
                        text_to_parse = text_to_parse[start:end].strip()
                
                # Look for JSON object
                start_brace = text_to_parse.find('{')
                end_brace = text_to_parse.rfind('}')
                
                if start_brace != -1 and end_brace != -1 and start_brace < end_brace:
                    json_text = text_to_parse[start_brace:end_brace+1]
                    parsed_json = json.loads(json_text)
                    print(f"[DEBUG] Successfully parsed JSON from OCR text, fields: {len(parsed_json)}")
                    
                    # Filter and validate fields
                    valid_fields = {
                        "name_zh", "name_en", "company_name_zh", "company_name_en", 
                        "position_zh", "position_en", "position1_zh", "position1_en",
                        "department1_zh", "department1_en", "department2_zh", "department2_en", 
                        "department3_zh", "department3_en", "mobile_phone", "company_phone1", 
                        "company_phone2", "email", "line_id", "company_address1_zh", 
                        "company_address1_en", "company_address2_zh", "company_address2_en",
                        "note1", "note2"
                    }
                    
                    result = {}
                    for key, value in parsed_json.items():
                        if key in valid_fields and value and str(value).strip():
                            result[key] = str(value).strip()
                    
                    print(f"[DEBUG] Valid fields extracted: {len(result)}")
                    if result:  # Only return if we have valid data
                        return result
                    
            except (json.JSONDecodeError, Exception) as e:
                print(f"[DEBUG] JSON parsing failed, will use LLM fallback: {e}")
            
            # Fallback: Use the LLM-based parsing with _zh suffix field names to match database schema
            prompt = '''You are an assistant for parsing business card information and outputting standard JSON format.

IMPORTANT: Extract actual information from the OCR text provided. Do NOT use the placeholder examples below.

Please identify the following 25 fields from the OCR text (set empty string if not found):

{
  "name_zh": "[Actual Chinese name from OCR]",
  "name_en": "[Actual English name from OCR]", 
  "company_name_zh": "[Actual Chinese company name from OCR]",
  "company_name_en": "[Actual English company name from OCR]",
  "position_zh": "[Actual Chinese position from OCR]",
  "position_en": "[Actual English position from OCR]",
  "position1_zh": "[Actual Chinese position1 from OCR]", 
  "position1_en": "[Actual English position1 from OCR]",
  "department1_zh": "[Actual Chinese department1 from OCR]",
  "department1_en": "[Actual English department1 from OCR]",
  "department2_zh": "[Actual Chinese department2 from OCR]", 
  "department2_en": "[Actual English department2 from OCR]",
  "department3_zh": "[Actual Chinese department3 from OCR]",
  "department3_en": "[Actual English department3 from OCR]", 
  "mobile_phone": "[Actual mobile phone from OCR]",
  "company_phone1": "[Actual company phone1 from OCR]",
  "company_phone2": "[Actual company phone2 from OCR]",
  "email": "[Actual email from OCR]",
  "line_id": "[Actual Line ID from OCR]",
  "company_address1_zh": "[Actual Chinese address1 from OCR]",
  "company_address1_en": "[Actual English address1 from OCR]", 
  "company_address2_zh": "[Actual Chinese address2 from OCR]",
  "company_address2_en": "[Actual English address2 from OCR]",
  "note1": "[Actual note1 from OCR]",
  "note2": "[Actual note2 from OCR]"
}

Note: Replace the brackets and their content with actual information from the OCR text. If a field has no content, use empty string "".

Please parse the following OCR text and return only JSON format: ''' + ocr_text
            
            print(f"[DEBUG] OCR parsing prompt: {prompt[:200]}...")
            result = self.llm_api.ocr_generate("", prompt)
            print(f"[DEBUG] LLM returned result: {result[:300]}...")
            
            # Try to parse JSON result
            import json
            try:
                # Clean possible Markdown formatting
                clean_result = result.strip()
                if clean_result.startswith("```json"):
                    clean_result = clean_result[7:]
                if clean_result.endswith("```"):
                    clean_result = clean_result[:-3]
                clean_result = clean_result.strip()
                
                parsed = json.loads(clean_result)
                print(f"[DEBUG] JSON parsing successful, field count: {len(parsed)}")
                
                # Validate and filter fields with _zh suffix to match database schema
                valid_fields = {
                    "name_zh", "name_en", "company_name_zh", "company_name_en", 
                    "position_zh", "position_en", "position1_zh", "position1_en",
                    "department1_zh", "department1_en", "department2_zh", "department2_en", 
                    "department3_zh", "department3_en", "mobile_phone", "company_phone1", 
                    "company_phone2", "email", "line_id", "company_address1_zh", 
                    "company_address1_en", "company_address2_zh", "company_address2_en",
                    "note1", "note2"
                }
                
                # Remove invalid fields and empty values
                cleaned_result = {}
                for key, value in parsed.items():
                    if key in valid_fields and value and str(value).strip():
                        cleaned_result[key] = str(value).strip()
                
                print(f"[DEBUG] After cleaning: {list(cleaned_result.keys())}")
                print(f"[DEBUG] Non-empty fields: {len(cleaned_result)}")
                return cleaned_result
                
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON parsing failed: {e}")
                print(f"[ERROR] Raw response content: {result}")
                print(f"[ERROR] OCR text preview: {ocr_text[:200]}...")
                # Return empty dict instead of polluting note fields with error messages
                return {}

        except Exception as e:
            print(f"[ERROR] Field parsing error: {e}")
            print(f"[ERROR] OCR text preview: {ocr_text[:200]}...")
            # Return empty dict instead of polluting note fields with error messages
            return {}
    
    def log_message(self, message):
        """Output message to console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
    
    def is_chinese(self, char):
        """Check if character is Chinese"""
        return '\u4e00' <= char <= '\u9fff'
    
    def filter_data(self, merged_data):
        """Filter field content, Chinese fields only Chinese, English fields only English/symbols"""
        
        # No need to filter these fields: contact info and notes
        ignore_filter = ["mobile_phone", "company_phone1", "company_phone2", "email", "line_id", "note1", "note2"]
        
        # English field identifiers
        en_identifiers = ("_en",)

        filtered_result = OrderedDict()

        for key, value in merged_data.items():
            if key in ignore_filter:
                filtered_result[key] = value
                continue

            if any(id in key for id in en_identifiers):
                # English fields: remove Chinese characters
                filtered_result[key] = "".join(c for c in str(value) if not self.is_chinese(c)).strip()
            else:
                # Chinese fields: keep only Chinese characters
                filtered_result[key] = "".join(c for c in str(value) if self.is_chinese(c)).strip()
                
        return filtered_result
    
    def batch_ocr_image(self, image_path, max_retries=3):
        """Batch OCR processing with retry mechanism"""
        filename = os.path.basename(image_path)
        
        for attempt in range(max_retries):
            try:
                self.log_message(f"Processing OCR: {filename} (attempt {attempt + 1}/{max_retries})")
                
                with open(image_path, "rb") as f:
                    files = {"file": (filename, f, "image/jpeg")}
                    
                    # Adjust timeout based on attempt number
                    timeout_duration = 10 + (attempt * 10)  # 10, 20, 30 seconds
                    
                    resp = requests.post(self.BATCH_OCR_API_URL, files=files, 
                                       verify=False, timeout=timeout_duration)
                    resp.raise_for_status()
                    
                    # Extract 'result' field from response JSON
                    result_json = resp.json()
                    text_content = result_json.get("result", result_json.get("text", "{}"))
                    
                    # Check if result is empty
                    if not text_content or text_content.strip() in ["{}", ""]:
                        self.log_message(f"API returned empty content: {filename}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return {}
                    
                    # Enhanced JSON extraction logic
                    if "```json" in text_content:
                        start = text_content.find("```json") + len("```json")
                        end = text_content.find("```", start)
                        if end != -1:
                            text_content = text_content[start:end].strip()
                        else:
                            text_content = text_content[start:].strip()
                    elif text_content.startswith("Here"):
                        if "```json" in text_content:
                            start = text_content.find("```json") + len("```json")
                            end = text_content.find("```", start)
                            if end != -1:
                                text_content = text_content[start:end].strip()
                    
                    # Parse JSON string
                    parsed_result = json.loads(text_content)
                    self.log_message(f"OCR processing complete: {filename}")
                    return parsed_result
                    
            except requests.exceptions.Timeout:
                self.log_message(f"Request timeout: {filename} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except requests.exceptions.RequestException as e:
                self.log_message(f"Request error: {filename}, error: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except json.JSONDecodeError as e:
                self.log_message(f"JSON parsing failed: {filename}, error: {e}")
                if 'text_content' in locals():
                    self.log_message(f"Raw text: {text_content[:200]}...")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            except Exception as e:
                self.log_message(f"OCR processing exception: {filename}, error: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        # All retries failed
        self.log_message(f"OCR processing completely failed: {filename}, retried {max_retries} times")
        return {}
    
    def merge_fields(self, results):
        """Merge multiple card fields, take first non-empty value"""
        merged = OrderedDict((k, "") for k in self.CARD_FIELDS)
        for field in self.CARD_FIELDS:
            for r in results:
                v = r.get(field, "")
                if v and not merged[field]:
                    merged[field] = str(v)
        return merged
    
    def process_single_image(self, image_path):
        """Process single image"""
        try:
            # Execute OCR
            ocr_result = self.batch_ocr_image(image_path)
            
            if not ocr_result:
                return None
            
            # Fill field data
            processed_result = OrderedDict((k, "") for k in self.CARD_FIELDS)
            for field in self.CARD_FIELDS:
                if field in ocr_result:
                    processed_result[field] = str(ocr_result[field])
            
            # Filter empty values
            filtered_result = self.filter_data(processed_result)
            
            return filtered_result
            
        except Exception as e:
            self.log_message(f"Single image processing failed: {image_path}, error: {e}")
            return None
    
    async def batch_process_directory(self, base_dir, progress_callback=None):
        """Batch process all images in directory"""
        try:
            if not os.path.exists(base_dir):
                self.log_message(f"Directory does not exist: {base_dir}")
                return []
            
            # Find all image files
            all_images = []
            for file in os.listdir(base_dir):
                if file.lower().endswith(self.IMAGE_EXTS):
                    all_images.append(os.path.join(base_dir, file))
            
            self.log_message(f"Starting batch processing, total {len(all_images)} images")
            
            results = []
            for i, image_path in enumerate(all_images):
                try:
                    result = self.process_single_image(image_path)
                    
                    if result:
                        results.append(result)
                        self.log_message(f"Processing {os.path.basename(image_path)} successful ({i+1}/{len(all_images)})")
                    else:
                        self.log_message(f"Processing {os.path.basename(image_path)} failed ({i+1}/{len(all_images)})")
                    
                    # Progress callback
                    if progress_callback:
                        await progress_callback({
                            'current': i + 1,
                            'total': len(all_images),
                            'filename': os.path.basename(image_path),
                            'success': result is not None,
                            'result': result
                        })
                    
                    # Random delay
                    sleep_time = random.uniform(0.5, 1)
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    self.log_message(f"Exception processing image {os.path.basename(image_path)}: {e}")
            
            self.log_message(f"Batch processing complete, successfully processed {len(results)} images")
            return results
            
        except Exception as e:
            self.log_message(f"Batch processing failed: {e}")
            return []

# OCR service doesn't need matplotlib font settings, removed

# Background task management
cleanup_task = None

async def cleanup_expired_sessions():
    """Periodically clean up expired sessions and update usage records"""
    while True:
        try:
            # Check expired sessions
            expired_sessions = []
            current_time = datetime.now()
            
            for session_id, session in serial_sessions.items():
                expires_at = datetime.fromisoformat(session["expires_at"])
                if current_time >= expires_at:
                    expired_sessions.append(session_id)
            
            # Clean expired sessions and update usage records
            for session_id in expired_sessions:
                session = serial_sessions[session_id]
                serial_code = session.get("serial_code")
                if serial_code:
                    update_serial_usage(serial_code, "expire", session_id)
                    print(f"[OCR] Session {session_id[:8]}... expired and record updated")
                del serial_sessions[session_id]
            
            # Check active sessions in config file
            config = load_serial_config()
            config_updated = False
            
            for serial in config.get("valid_serials", []):
                for record in serial.get("usage_records", []):
                    if record.get("status") == "active":
                        # Check if session should expire
                        started_at = datetime.fromisoformat(record["started_at"])
                        duration_minutes = serial.get("duration_minutes", config.get("default_duration", 15))
                        expected_end = started_at + timedelta(minutes=duration_minutes)
                        
                        if current_time >= expected_end:
                            record["ended_at"] = current_time.isoformat()
                            record["status"] = "expired"
                            config_updated = True
                            print(f"[OCR] Serial {serial['code']} session expired")
            
            # Save updates
            if config_updated:
                save_serial_config(config)
                
        except Exception as e:
            print(f"[OCR] Session cleanup error: {e}")
        
        # Execute every 30 seconds
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    global cleanup_task
    # On startup
    cleanup_task = asyncio.create_task(cleanup_expired_sessions())
    print("[OCR] Started session cleanup background task")
    yield
    # On shutdown
    if cleanup_task:
        cleanup_task.cancel()
        print("[OCR] Stopped session cleanup background task")

app = FastAPI(title="OCR Service - Serial Management", lifespan=lifespan)

# Configuration
OCR_PORT = int(os.getenv("OCR_PORT", "8504"))
OCR_HOST = os.getenv("OCR_HOST", "0.0.0.0")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
CONFIG_FILE = os.getenv("CONFIG_FILE", "config/serials.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory serial usage tracking
serial_sessions = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serial management functions
def load_serial_config():
    """Load serial configuration file"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Ensure usage records structure exists
        for serial in config.get("valid_serials", []):
            if "usage_records" not in serial:
                serial["usage_records"] = []
                
        # Ensure settings exist
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
        print(f"Loading config file error: {e}")
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
    """Save serial configuration file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Saving config file error: {e}")
        return False

def update_serial_usage(serial_code: str, action: str, session_id: str = None):
    """Update serial usage records"""
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
                # Check concurrent limit
                concurrent_limit = settings.get("concurrent_sessions_limit", 1)
                active_sessions = [
                    record for record in serial["usage_records"]
                    if record.get("status") == "active"
                ]
                
                if len(active_sessions) >= concurrent_limit:
                    return False
                
                # Check cooldown period
                cooldown_minutes = settings.get("usage_cooldown_minutes", 0)
                if cooldown_minutes > 0:
                    recent_usage = [
                        record for record in serial["usage_records"]
                        if record.get("ended_at") and 
                        (now - datetime.fromisoformat(record["ended_at"])).total_seconds() < cooldown_minutes * 60
                    ]
                    
                    if recent_usage:
                        return False
                
                # Add new usage record
                usage_record = {
                    "session_id": session_id,
                    "started_at": now.isoformat(),
                    "status": "active",
                    "ip_address": "unknown"  # Can be extracted from request
                }
                serial["usage_records"].append(usage_record)
                
            elif action == "end":
                # End usage record
                for record in serial["usage_records"]:
                    if record.get("session_id") == session_id and record.get("status") == "active":
                        record["ended_at"] = now.isoformat()
                        record["status"] = "completed"
                        break
            
            elif action == "expire":
                # Mark as expired
                for record in serial["usage_records"]:
                    if record.get("session_id") == session_id and record.get("status") == "active":
                        record["ended_at"] = now.isoformat()
                        record["status"] = "expired"
                        break
            
            # Save config
            save_serial_config(config)
            return True
    
    return False

def check_serial_availability(serial_code: str) -> dict:
    """Check serial availability"""
    config = load_serial_config()
    settings = config.get("serial_usage_settings", {})
    
    for serial in config.get("valid_serials", []):
        if serial["code"] == serial_code:
            # Check basic expiry
            if serial.get("expires"):
                try:
                    expires_date = datetime.strptime(serial["expires"], "%Y-%m-%d")
                    if datetime.now() > expires_date:
                        return {"available": False, "reason": "Serial has expired"}
                except:
                    pass
            
            # Check single use mode
            if settings.get("single_use_mode", False):
                completed_usage = [
                    record for record in serial.get("usage_records", [])
                    if record.get("status") in ["completed", "expired", "force_ended"]
                ]
                if completed_usage:
                    return {"available": False, "reason": "Serial has been used"}
            
            # Check concurrent limit
            concurrent_limit = settings.get("concurrent_sessions_limit", 1)
            active_sessions = [
                record for record in serial.get("usage_records", [])
                if record.get("status") == "active"
            ]
            
            if len(active_sessions) >= concurrent_limit:
                return {"available": False, "reason": "Serial is currently in use"}
            
            # Check cooldown period
            cooldown_minutes = settings.get("usage_cooldown_minutes", 0)
            if cooldown_minutes > 0:
                now = datetime.now()
                recent_usage = [
                    record for record in serial.get("usage_records", [])
                    if record.get("ended_at") and 
                    (now - datetime.fromisoformat(record["ended_at"])).total_seconds() < cooldown_minutes * 60
                ]
                
                if recent_usage:
                    return {"available": False, "reason": f"Serial is in cooldown period, please wait {cooldown_minutes} minutes"}
            
            return {"available": True}
    
    return {"available": False, "reason": "Invalid serial"}

def validate_serial(serial_code: str) -> Dict[str, Any]:
    """Validate if serial is usable"""
    # First check availability
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
    
    return {"valid": False, "error": "Invalid serial"}

def get_session_status(session_id: str) -> Dict[str, Any]:
    """Get session status"""
    if session_id not in serial_sessions:
        return {"active": False, "remaining_seconds": 0}
    
    session = serial_sessions[session_id]
    now = datetime.now()
    expires_at = datetime.fromisoformat(session["expires_at"])
    
    remaining = (expires_at - now).total_seconds()
    
    # Add 5 second tolerance to handle network delays
    if remaining <= -5:
        # Session has definitely expired, clean up and update usage records
        print(f"Session {session_id} has expired: {remaining:.1f} seconds")
        
        # Update usage records for expiry
        serial_code = session.get("serial_code")
        if serial_code:
            update_serial_usage(serial_code, "expire", session_id)
        
        del serial_sessions[session_id]
        return {"active": False, "remaining_seconds": 0}
    
    # If remaining <= 0 but within tolerance range, return 0 but keep active
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
        self.client = OpenAI(
            api_key=os.getenv("OCR_API_KEY", "YOUR_API_KEY"), 
            base_url=os.getenv("OCR_API_URL", "http://0.0.0.0:23333/v1"),
            timeout=60.0,  # 60 seconds timeout
            max_retries=2
        )

    def ocr_generate(self, image_path, prompt="Only return the OCR result and don't provide any other explanations.", max_retries=3):
        for attempt in range(max_retries):
            try:
                # Check if image path exists and is valid
                if not image_path or not os.path.exists(image_path):
                    print(f"[OCR ERROR] Image path does not exist: {image_path}")
                    return "OCR錯誤: 圖片路徑不存在或無效"
                
                image_url = f"{os.path.abspath(image_path)}"
                print(f"[OCR DEBUG] Processing image (attempt {attempt + 1}/{max_retries}): {image_url}")
                
                # Get model list with timeout handling
                try:
                    models = self.client.models.list()
                    if not models.data:
                        print("[OCR ERROR] No models available")
                        return "OCR錯誤: 沒有可用的模型"
                        
                    model_name = models.data[0].id
                    print(f"[OCR DEBUG] Using model: {model_name}")
                except Exception as model_error:
                    print(f"[OCR ERROR] Failed to get models: {model_error}")
                    if attempt < max_retries - 1:
                        continue
                    return f"OCR錯誤: 無法獲取模型列表 - {str(model_error)}"
                
                # Make OCR request with proper error handling
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[{
                        'role': 'user',
                        'content': [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': image_url}}]
                    }],
                    temperature=0,
                    timeout=45.0  # Per-request timeout
                )
                
                result = response.choices[0].message.content
                if result and len(result.strip()) > 0:
                    print(f"[OCR SUCCESS] OCR result length: {len(result)}")
                    if len(result) > 100:  # Show preview for long results
                        print(f"[OCR PREVIEW] {result[:100]}...")
                    return result.strip()
                else:
                    print(f"[OCR WARNING] Empty result on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    return "OCR錯誤: 識別結果為空"
                
            except Exception as e:
                print(f"[OCR ERROR] API call failed on attempt {attempt + 1}: {e}")
                print(f"[OCR ERROR] Exception type: {type(e).__name__}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # Wait before retry
                    continue
                return f"OCR識別失敗: {str(e)}"
        
        return "OCR錯誤: 所有重試均失敗"
    

def process_image(image_path):
    """Image processing to improve OCR recognition rate - Integrated smart enhancement"""
    try:
        # Priority: try using smart card enhancement
        use_card_enhancement = os.getenv("USE_CARD_ENHANCEMENT", "true").lower() == "true"
        
        if use_card_enhancement:
            try:
                # Use smart card enhancement service
                enhancer = CardEnhancementService()
                success, enhanced_path = enhancer.process_image(
                    image_path, 
                    auto_detect=True,
                    scale_factor=3
                )
                
                if success and enhanced_path and enhanced_path != image_path:
                    print(f"Smart card enhancement successful: {enhanced_path}")
                    return enhanced_path
                else:
                    print(f"Smart enhancement failed or disabled, using traditional method")
                    # Continue with traditional method
            except Exception as enhancement_error:
                print(f"Smart enhancement exception, using traditional method: {enhancement_error}")
                # Continue with traditional method
        
        # Fallback: use OpenCV detection
        use_opencv = os.getenv("USE_OPENCV", "true").lower() == "true"
        
        if use_opencv:
            try:
                # Use OpenCV detector
                detector = CardDetector()
                success, enhanced_path = detector.process_card_image(image_path)
                
                if success:
                    print(f"OpenCV processing successful: {enhanced_path}")
                    return enhanced_path
                else:
                    print(f"OpenCV processing failed, using traditional method: {enhanced_path}")
                    # Continue with traditional method
            except Exception as opencv_error:
                print(f"OpenCV processing exception, using traditional method: {opencv_error}")
                # Continue with traditional method
        
        # Traditional PIL processing method (kept as final fallback)
        with open(image_path, "rb") as f:
            image_data = f.read()
        image = Image.open(BytesIO(image_data))

        if image.mode == "RGBA":
            image = image.convert("RGB")

        dpi = image.info.get("dpi", (100, 100))
        x_dpi = dpi[0]

        # If DPI is greater than 100, no enhancement needed
        if x_dpi > 100:
            return image_path

        # Basic enhancement: scale up to improve clarity
        scale_factor = 1.5  # Smaller scaling factor
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        enhanced_image = image.resize((new_width, new_height), Image.LANCZOS)
        enhanced_path = os.path.splitext(image_path)[0] + "_enhanced.jpg"
        enhanced_image.save(enhanced_path, "JPEG", quality=95, dpi=(200, 200))  # High quality and DPI
        return enhanced_path
    except Exception as e:
        print(f"Image processing error: {e}")
        return image_path  # Return original path instead of None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return filename.lower().endswith((".png", ".jpg", ".jpeg"))

def write_file(path, content):
    """Write file content"""
    with open(path, "wb") as f:
        f.write(content)

def get_image_base64(image_path):
    """Convert image to Base64 encoding"""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        print(f"Convert to Base64 error: {e}")
        return None

# ==================== API Routes ====================

@app.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...), session_id: str = Form(None)):
    """OCR API - Requires valid serial session"""
    
    # Check session permissions
    if not session_id:
        raise HTTPException(status_code=401, detail="Valid serial session required")
    
    session_status = get_session_status(session_id)
    if not session_status["active"]:
        raise HTTPException(status_code=401, detail="Serial session has expired, please validate again")
    
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only JPG/PNG files supported")

    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    content = await file.read()
    write_file(path, content)

    enhanced_path = process_image(path)
    if not enhanced_path:
        raise HTTPException(status_code=500, detail="Image enhancement failed")

    llm = LLMApi()
    result = llm.ocr_generate(enhanced_path, prompt="Only return the OCR result and don't provide any other explanations.")
    
    # Clean up files
    try:
        os.remove(path)
        if enhanced_path != path:
            os.remove(enhanced_path)
    except Exception as e:
        print(f"File cleanup error: {e}")
    
    return { 
        "result": result,
        "remaining_seconds": session_status["remaining_seconds"]
    }

@app.post("/api/card")
async def api_card(file: UploadFile = File(...)):
    """Business card recognition API"""
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only JPG/PNG files supported")

    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_FOLDER, filename)
    content = await file.read()
    write_file(path, content)

    enhanced_path = process_image(path)
    if not enhanced_path:
        raise HTTPException(status_code=500, detail="Image enhancement failed")

    llm = LLMApi()
    result = llm.ocr_generate(enhanced_path, prompt='''You are an assistant for parsing business card information into structured data fields with _zh suffix for Chinese fields. 

IMPORTANT: Extract actual information from the business card image. Do NOT use the placeholder examples below.

Please identify the following 25 fields from the business card (set empty string if not found):

{
  "name_zh": "[Actual Chinese name from card]",
  "name_en": "[Actual English name from card]", 
  "company_name_zh": "[Actual Chinese company name from card]",
  "company_name_en": "[Actual English company name from card]",
  "position_zh": "[Actual Chinese position from card]",
  "position_en": "[Actual English position from card]",
  "position1_zh": "[Actual Chinese position1 from card]", 
  "position1_en": "[Actual English position1 from card]",
  "department1_zh": "[Actual Chinese department1 from card]",
  "department1_en": "[Actual English department1 from card]",
  "department2_zh": "[Actual Chinese department2 from card]", 
  "department2_en": "[Actual English department2 from card]",
  "department3_zh": "[Actual Chinese department3 from card]",
  "department3_en": "[Actual English department3 from card]", 
  "mobile_phone": "[Actual mobile phone from card]",
  "company_phone1": "[Actual company phone1 from card]",
  "company_phone2": "[Actual company phone2 from card]",
  "email": "[Actual email from card]",
  "line_id": "[Actual Line ID from card]",
  "company_address1_zh": "[Actual Chinese address1 from card]",
  "company_address1_en": "[Actual English address1 from card]", 
  "company_address2_zh": "[Actual Chinese address2 from card]",
  "company_address2_en": "[Actual English address2 from card]",
  "note1": "[Actual note1 from card]",
  "note2": "[Actual note2 from card]"
}

Note: Replace the brackets and their content with actual information from the business card. If a field has no content, use empty string "".

Please parse the following business card and return ONLY JSON format:''')
    
    # Clean up files
    try:
        os.remove(path)
        if enhanced_path != path:
            os.remove(enhanced_path)
    except Exception as e:
        print(f"File cleanup error: {e}")
    
    return {"result": result}

# Serial validation API
@app.post("/api/validate-serial")
async def validate_serial_api(serial_code: str = Form(...)):
    """Validate serial and create session"""
    validation_result = validate_serial(serial_code)
    
    if not validation_result["valid"]:
        raise HTTPException(status_code=400, detail=validation_result["error"])
    
    # Create session
    session_id = str(uuid.uuid4())
    
    # Record serial usage start
    if not update_serial_usage(serial_code, "start", session_id):
        raise HTTPException(status_code=400, detail="Serial is currently unavailable")
    
    serial_sessions[session_id] = {
        "serial_code": serial_code,
        "expires_at": validation_result["expires_at"],
        "duration_minutes": validation_result["duration_minutes"],
        "created_at": datetime.now().isoformat()
    }
    
    # Calculate remaining seconds
    duration_seconds = validation_result["duration_minutes"] * 60
    
    print(f"Serial validation successful - Session ID: {session_id[:8]}..., Serial: {serial_code}, Duration: {validation_result['duration_minutes']} minutes")
    
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
    """Check session status"""
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")
    
    status = get_session_status(session_id)
    
    # Log status check
    if status["active"]:
        remaining_min = status["remaining_seconds"] // 60
        remaining_sec = status["remaining_seconds"] % 60
        print(f"Session status check - ID: {session_id[:8]}..., Remaining: {remaining_min:02d}:{remaining_sec:02d}")
    else:
        print(f"Session expired - ID: {session_id[:8]}...")
    
    return status

# Health check
@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "OCR Service",
        "port": OCR_PORT,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print(f"Starting OCR Service...")
    print(f"User access URL: http://{OCR_HOST}:{OCR_PORT}")
    print(f"Serial validation and OCR functionality ready")
    uvicorn.run(app, host=OCR_HOST, port=OCR_PORT)