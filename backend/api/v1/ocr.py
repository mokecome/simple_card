from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from backend.services.ocr_service import OCRService
from typing import Optional

router = APIRouter()
ocr_service = OCRService()

class OCRParseRequest(BaseModel):
    ocr_text: str
    side: str  # 'front' or 'back'

@router.post("/image")
async def ocr_image(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = await ocr_service.ocr_image(content)
        return {"success": True, "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR失敗: {str(e)}")

@router.post("/parse-fields")
async def parse_ocr_fields(request: OCRParseRequest):
    """
    智能解析OCR文字到標準化欄位
    """
    try:
        parsed_fields = ocr_service.parse_ocr_to_fields(request.ocr_text, request.side)
        return {
            "success": True, 
            "parsed_fields": parsed_fields,
            "side": request.side
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR解析失敗: {str(e)}") 