from typing import Any, Optional, Dict, List
from pydantic import BaseModel
from fastapi import status
from fastapi.responses import JSONResponse
import traceback
from datetime import datetime

class APIResponse(BaseModel):
    """統一的 API 響應模型"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: str = datetime.now().isoformat()
    
class ResponseHandler:
    """API 響應處理器"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        status_code: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """成功響應"""
        response = APIResponse(
            success=True,
            data=data,
            message=message
        )
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump()
        )
    
    @staticmethod
    def error(
        message: str = "操作失敗",
        error: Optional[Exception] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """錯誤響應"""
        error_detail = {
            "message": str(error) if error else message,
            "type": type(error).__name__ if error else "Error"
        }
        
        if details:
            error_detail.update(details)
            
        # 在開發環境中包含堆棧跟踪
        if error and hasattr(error, '__traceback__'):
            error_detail["traceback"] = traceback.format_exc()
        
        response = APIResponse(
            success=False,
            message=message,
            error=error_detail
        )
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump()
        )
    
    @staticmethod
    def paginated(
        data: List[Any],
        total: int,
        page: int,
        per_page: int,
        message: str = "查詢成功"
    ) -> JSONResponse:
        """分頁響應"""
        pagination_data = {
            "items": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
        return ResponseHandler.success(
            data=pagination_data,
            message=message
        )