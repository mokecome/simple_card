import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from .exceptions import BusinessException, ErrorCode, ErrorResponse

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """統一異常處理中間件"""
    
    async def dispatch(self, request: Request, call_next):
        # 生成追蹤ID
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self._handle_exception(request, exc, trace_id)
    
    async def _handle_exception(
        self, 
        request: Request, 
        exc: Exception, 
        trace_id: str
    ) -> JSONResponse:
        """統一處理異常"""
        
        # 獲取請求路徑
        path = str(request.url.path)
        
        if isinstance(exc, BusinessException):
            # 業務異常
            error_data = {
                "code": exc.code.value,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
                "path": path,
                "trace_id": trace_id
            }
            
            # 記錄業務異常（警告級別）
            logger.warning(
                f"Business exception: {exc.code.value} - {exc.message}",
                extra={
                    "trace_id": trace_id,
                    "path": path,
                    "details": exc.details
                }
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "error": error_data
                }
            )
        
        elif isinstance(exc, ValidationError):
            # Pydantic驗證錯誤
            error_data = {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "輸入數據驗證失敗",
                "details": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "path": path,
                "trace_id": trace_id
            }
            
            logger.warning(
                f"Validation error: {str(exc)}",
                extra={"trace_id": trace_id, "path": path}
            )
            
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": error_data
                }
            )
        
        elif isinstance(exc, SQLAlchemyError):
            # 數據庫錯誤
            error_data = {
                "code": ErrorCode.DATABASE_ERROR.value,
                "message": "數據庫操作失敗",
                "details": "Database operation failed",
                "timestamp": datetime.utcnow().isoformat(),
                "path": path,
                "trace_id": trace_id
            }
            
            # 記錄數據庫錯誤（錯誤級別）
            logger.error(
                f"Database error: {str(exc)}",
                extra={"trace_id": trace_id, "path": path},
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": error_data
                }
            )
        
        else:
            # 未知異常
            error_data = {
                "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                "message": "內部服務器錯誤",
                "details": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "path": path,
                "trace_id": trace_id
            }
            
            # 記錄未知錯誤（嚴重級別）
            logger.error(
                f"Unexpected error: {str(exc)}",
                extra={"trace_id": trace_id, "path": path},
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": error_data
                }
            )

class LoggingMiddleware(BaseHTTPMiddleware):
    """請求日誌中間件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()
        trace_id = getattr(request.state, 'trace_id', str(uuid.uuid4()))
        
        # 記錄請求信息
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params)
            }
        )
        
        response = await call_next(request)
        
        # 計算處理時間
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 記錄響應信息
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time
            }
        )
        
        # 添加追蹤ID到響應頭
        response.headers["X-Trace-ID"] = trace_id
        
        return response 