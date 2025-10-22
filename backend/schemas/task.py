"""
任务相关的 Pydantic Schema 定义
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str  # pending, processing, completed, failed, cancelled
    total: int
    completed: int
    failed: int
    success_count: int
    error_message: str
    created_at: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    progress_percent: float

    class Config:
        from_attributes = True


class BatchClassifyRequest(BaseModel):
    """批量分类请求"""
    card_ids: Optional[list] = None  # None 表示所有未分类的名片


class BatchClassifyResponse(BaseModel):
    """批量分类响应"""
    success: bool
    message: str
    data: TaskStatusResponse


class TaskCancelResponse(BaseModel):
    """任务取消响应"""
    success: bool
    message: str
