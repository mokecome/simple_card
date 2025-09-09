"""
Temporary OCR Service - minimal implementation to test card enhancement functionality
"""
import os
import io
from PIL import Image
from backend.services.card_enhancement_service import CardEnhancementService

class OCRService:
    """Temporary OCR Service for testing card enhancement"""
    
    def __init__(self):
        self.card_enhancer = CardEnhancementService()
    
    async def ocr_image(self, image_content: bytes) -> str:
        """Process image with card enhancement and return dummy OCR result"""
        try:
            # Save the image temporarily
            temp_path = "/tmp/temp_ocr_image.jpg"
            with open(temp_path, "wb") as f:
                f.write(image_content)
            
            # Process with card enhancement
            enhanced_path = self.process_image(temp_path)
            
            # Return dummy OCR result indicating enhancement was applied
            if enhanced_path and enhanced_path != temp_path:
                return f"圖片已通過智能增強處理：{enhanced_path}"
            else:
                return f"圖片處理完成：{temp_path}"
        except Exception as e:
            return f"處理失敗：{str(e)}"
    
    def process_image(self, image_path: str) -> str:
        """Process image with intelligent enhancement"""
        try:
            # Use card enhancement service
            use_card_enhancement = os.getenv("USE_CARD_ENHANCEMENT", "true").lower() == "true"
            
            if use_card_enhancement and self.card_enhancer:
                # Try intelligent enhancement first
                enhanced_path = self.card_enhancer.process_image(image_path)
                if enhanced_path:
                    return enhanced_path
            
            # Fallback to original image
            return image_path
            
        except Exception as e:
            print(f"圖片處理失敗：{e}")
            return image_path
    
    def parse_ocr_to_fields(self, ocr_text: str, side: str) -> dict:
        """Parse OCR text to standardized fields - unified parsing for both sides"""
        import re
        
        try:
            # Initialize complete field structure
            fields = {
                "name_zh": "",
                "name_en": "",
                "company_name_zh": "",
                "company_name_en": "",
                "position_zh": "",
                "position_en": "",
                "position1_zh": "",
                "position1_en": "",
                "department1_zh": "",
                "department1_en": "",
                "department2_zh": "",
                "department2_en": "",
                "department3_zh": "",
                "department3_en": "",
                "mobile_phone": "",
                "company_phone1": "",
                "company_phone2": "",
                "email": "",
                "address_zh": "",
                "address_en": "",
                "website": "",
                "fax": "",
                "line_id": "",
                "note": ""
            }
            
            if not ocr_text or not ocr_text.strip():
                return fields
            
            lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
            
            # Extract phone numbers
            phone_patterns = [
                r'(\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4})',
                r'(\d{10,11})',
                r'(\(\d{2,4}\)\s?\d{3,4}[-\s]?\d{3,4})'
            ]
            phones = []
            for pattern in phone_patterns:
                phones.extend(re.findall(pattern, ocr_text))
            
            # Extract email addresses
            email_pattern = r'([a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            emails = re.findall(email_pattern, ocr_text)
            
            # Extract websites
            website_patterns = [
                r'(https?://[^\s]+)',
                r'(www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9.-]+\.com)',
                r'([a-zA-Z0-9.-]+\.tw)',
                r'([a-zA-Z0-9.-]+\.net)'
            ]
            websites = []
            for pattern in website_patterns:
                websites.extend(re.findall(pattern, ocr_text))
            
            # Helper function to detect Chinese characters
            def has_chinese(text):
                return bool(re.search(r'[\u4e00-\u9fff]', text))
            
            # Helper function to detect if line is likely a name
            def is_likely_name(line):
                # Names are usually short and may contain Chinese or English
                if len(line) > 20:
                    return False
                # Common title words that indicate NOT a name
                exclude_words = ['經理', '總監', '主任', '工程師', '部長', '科長', '組長', '主管', 
                               'Manager', 'Director', 'Engineer', 'Supervisor', 'CEO', 'CTO']
                return not any(word in line for word in exclude_words)
            
            # Helper function to detect if line is likely a company
            def is_likely_company(line):
                company_indicators = ['公司', '企業', '集團', '股份', '有限', '科技', '工業', 
                                    'Company', 'Corp', 'Ltd', 'Inc', 'Technology', 'Industries']
                return any(indicator in line for indicator in company_indicators)
            
            # Helper function to detect if line is likely a position
            def is_likely_position(line):
                position_indicators = ['經理', '總監', '主任', '工程師', '部長', '科長', '組長', '主管',
                                     'Manager', 'Director', 'Engineer', 'Supervisor', 'CEO', 'CTO',
                                     'Developer', 'Analyst', 'Specialist', '專員', '顧問']
                return any(indicator in line for indicator in position_indicators)
            
            # Helper function to detect if line is likely an address
            def is_likely_address(line):
                address_indicators = ['路', '街', '巷', '號', '樓', '區', '市', '縣', '鄉', '鎮',
                                    'Road', 'Street', 'Ave', 'Avenue', 'Building', 'Floor']
                return any(indicator in line for indicator in address_indicators) or len(line) > 15
            
            # Process each line
            name_candidates_zh = []
            name_candidates_en = []
            company_candidates_zh = []
            company_candidates_en = []
            position_candidates_zh = []
            position_candidates_en = []
            address_candidates_zh = []
            address_candidates_en = []
            
            for line in lines:
                # Skip lines that are just phone numbers, emails, or websites
                if any(phone in line for phone in phones) and len(line) < 20:
                    continue
                if any(email in line for email in emails):
                    continue
                if any(website in line for website in websites):
                    continue
                
                if has_chinese(line):
                    # Chinese line processing
                    if is_likely_company(line):
                        company_candidates_zh.append(line)
                    elif is_likely_position(line):
                        position_candidates_zh.append(line)
                    elif is_likely_address(line):
                        address_candidates_zh.append(line)
                    elif is_likely_name(line):
                        name_candidates_zh.append(line)
                else:
                    # English line processing
                    if is_likely_company(line):
                        company_candidates_en.append(line)
                    elif is_likely_position(line):
                        position_candidates_en.append(line)
                    elif is_likely_address(line):
                        address_candidates_en.append(line)
                    elif is_likely_name(line):
                        name_candidates_en.append(line)
            
            # Assign extracted information to fields
            if phones:
                fields["mobile_phone"] = phones[0] if len(phones) > 0 else ""
                fields["company_phone1"] = phones[1] if len(phones) > 1 else ""
                fields["company_phone2"] = phones[2] if len(phones) > 2 else ""
            
            if emails:
                fields["email"] = emails[0]
            
            if websites:
                fields["website"] = websites[0]
            
            if name_candidates_zh:
                fields["name_zh"] = name_candidates_zh[0]
            if name_candidates_en:
                fields["name_en"] = name_candidates_en[0]
            
            if company_candidates_zh:
                fields["company_name_zh"] = company_candidates_zh[0]
            if company_candidates_en:
                fields["company_name_en"] = company_candidates_en[0]
            
            if position_candidates_zh:
                fields["position_zh"] = position_candidates_zh[0]
                if len(position_candidates_zh) > 1:
                    fields["position1_zh"] = position_candidates_zh[1]
            if position_candidates_en:
                fields["position_en"] = position_candidates_en[0]
                if len(position_candidates_en) > 1:
                    fields["position1_en"] = position_candidates_en[1]
            
            if address_candidates_zh:
                fields["address_zh"] = address_candidates_zh[0]
            if address_candidates_en:
                fields["address_en"] = address_candidates_en[0]
            
            # Look for fax numbers (usually labeled)
            fax_pattern = r'(?:傳真|FAX|fax)[:\s]*(\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4})'
            fax_matches = re.findall(fax_pattern, ocr_text, re.IGNORECASE)
            if fax_matches:
                fields["fax"] = fax_matches[0]
            
            # Look for Line ID
            line_pattern = r'(?:LINE|line)[:\s]*([a-zA-Z0-9._-]+)'
            line_matches = re.findall(line_pattern, ocr_text, re.IGNORECASE)
            if line_matches:
                fields["line_id"] = line_matches[0]
            
            return fields
            
        except Exception as e:
            print(f"OCR解析失敗：{e}")
            # Return empty structure instead of error
            return {
                "name_zh": "",
                "name_en": "",
                "company_name_zh": "",
                "company_name_en": "",
                "position_zh": "",
                "position_en": "",
                "position1_zh": "",
                "position1_en": "",
                "department1_zh": "",
                "department1_en": "",
                "department2_zh": "",
                "department2_en": "",
                "department3_zh": "",
                "department3_en": "",
                "mobile_phone": "",
                "company_phone1": "",
                "company_phone2": "",
                "email": "",
                "address_zh": "",
                "address_en": "",
                "website": "",
                "fax": "",
                "line_id": "",
                "note": ""
            }
    
    def process_single_image(self, image_path: str) -> dict:
        """Process single image and return dummy card data"""
        try:
            # Process the image with enhancement
            enhanced_path = self.process_image(image_path)
            
            # Return dummy card data to simulate OCR extraction
            return {
                "name": "測試名片",
                "title": "軟體工程師",
                "company": "測試公司", 
                "phone": "0912-345-678",
                "email": "test@example.com",
                "address": "測試地址",
                "note": f"已通過智能增強處理: {enhanced_path}",
                "enhanced": enhanced_path != image_path
            }
        except Exception as e:
            print(f"處理單張圖片失敗：{e}")
            return None