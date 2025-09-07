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