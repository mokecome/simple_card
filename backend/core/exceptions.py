from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ErrorCode(str, Enum):
    # 業務錯誤
    CARD_NOT_FOUND = "CARD_NOT_FOUND"
    CARD_CREATE_FAILED = "CARD_CREATE_FAILED"
    CARD_UPDATE_FAILED = "CARD_UPDATE_FAILED"
    CARD_DELETE_FAILED = "CARD_DELETE_FAILED"
    
    # OCR錯誤
    OCR_SERVICE_UNAVAILABLE = "OCR_SERVICE_UNAVAILABLE"
    OCR_PARSE_FAILED = "OCR_PARSE_FAILED"
    
    # 文件錯誤
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    FILE_TYPE_NOT_SUPPORTED = "FILE_TYPE_NOT_SUPPORTED"
    
    # 系統錯誤
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"

class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]
    timestamp: datetime
    path: str
    trace_id: Optional[str] = None

class BusinessException(Exception):
    """業務邏輯異常類"""
    def __init__(
        self, 
        code: ErrorCode, 
        message: str, 
        details: Optional[str] = None,
        status_code: int = 400
    ):
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(message)

# 常用的業務異常工廠函數
def card_not_found_error(card_id: int) -> BusinessException:
    return BusinessException(
        code=ErrorCode.CARD_NOT_FOUND,
        message="名片不存在",
        details=f"Card with ID {card_id} not found",
        status_code=404
    )

def card_create_failed_error(details: str = None) -> BusinessException:
    return BusinessException(
        code=ErrorCode.CARD_CREATE_FAILED,
        message="創建名片失敗",
        details=details,
        status_code=500
    )

def card_update_failed_error(card_id: int, details: str = None) -> BusinessException:
    return BusinessException(
        code=ErrorCode.CARD_UPDATE_FAILED,
        message="更新名片失敗",
        details=details or f"Failed to update card with ID {card_id}",
        status_code=500
    )

def card_delete_failed_error(card_id: int) -> BusinessException:
    return BusinessException(
        code=ErrorCode.CARD_DELETE_FAILED,
        message="刪除名片失敗",
        details=f"Failed to delete card with ID {card_id}",
        status_code=500
    )

def ocr_service_unavailable_error(details: str = None) -> BusinessException:
    return BusinessException(
        code=ErrorCode.OCR_SERVICE_UNAVAILABLE,
        message="OCR服務暫時不可用",
        details=details,
        status_code=503
    )

def ocr_parse_failed_error(details: str = None) -> BusinessException:
    return BusinessException(
        code=ErrorCode.OCR_PARSE_FAILED,
        message="OCR解析失敗",
        details=details,
        status_code=422
    )

def file_upload_failed_error(details: str = None) -> BusinessException:
    return BusinessException(
        code=ErrorCode.FILE_UPLOAD_FAILED,
        message="文件上傳失敗",
        details=details,
        status_code=400
    )

def validation_error(details: str) -> BusinessException:
    return BusinessException(
        code=ErrorCode.VALIDATION_ERROR,
        message="輸入數據驗證失敗",
        details=details,
        status_code=400
    ) 