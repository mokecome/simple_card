"""
后台任务管理器

用于管理长时间运行的异步任务（如批量AI分类）
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务对象"""
    def __init__(self, task_id: str, total: int):
        self.task_id = task_id
        self.status = TaskStatus.PENDING
        self.total = total
        self.completed = 0
        self.failed = 0
        self.error_message = ""
        self.created_at = datetime.now()
        self.started_at = None
        self.finished_at = None
        self.cancelled = False
        self.lock = threading.Lock()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "success_count": self.completed - self.failed,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "progress_percent": round((self.completed / self.total * 100) if self.total > 0 else 0, 1)
        }


class TaskManager:
    """任务管理器（单例）"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.tasks = {}
                    cls._instance.tasks_lock = threading.Lock()
        return cls._instance

    def create_task(self, total: int) -> str:
        """
        创建新任务

        Args:
            total: 总任务数

        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, total)

        with self.tasks_lock:
            self.tasks[task_id] = task

        logger.info(f"创建任务: {task_id}, 总数={total}")
        return task_id

    def start_task(self, task_id: str):
        """标记任务开始"""
        task = self.get_task(task_id)
        if task:
            with task.lock:
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now()
            logger.info(f"任务开始: {task_id}")

    def update_progress(self, task_id: str, success: bool = True):
        """
        更新任务进度

        Args:
            task_id: 任务ID
            success: 是否成功
        """
        task = self.get_task(task_id)
        if task:
            with task.lock:
                task.completed += 1
                if not success:
                    task.failed += 1

                # 日志记录
                if task.completed % 10 == 0 or task.completed == task.total:
                    logger.info(f"任务进度: {task_id} - {task.completed}/{task.total}")

    def complete_task(self, task_id: str, error_message: str = ""):
        """
        完成任务

        Args:
            task_id: 任务ID
            error_message: 错误信息（如果有）
        """
        task = self.get_task(task_id)
        if task:
            with task.lock:
                task.status = TaskStatus.FAILED if error_message else TaskStatus.COMPLETED
                task.error_message = error_message
                task.finished_at = datetime.now()

            logger.info(f"任务完成: {task_id}, 状态={task.status}, 成功={task.completed - task.failed}/{task.total}")

    def cancel_task(self, task_id: str):
        """取消任务"""
        task = self.get_task(task_id)
        if task:
            with task.lock:
                task.cancelled = True
                task.status = TaskStatus.CANCELLED
                task.finished_at = datetime.now()
            logger.info(f"任务取消: {task_id}")

    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否已取消"""
        task = self.get_task(task_id)
        return task.cancelled if task else False

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务对象"""
        with self.tasks_lock:
            return self.tasks.get(task_id)

    def get_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典，如果不存在返回None
        """
        task = self.get_task(task_id)
        return task.to_dict() if task else None

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务（可选）"""
        now = datetime.now()
        to_remove = []

        with self.tasks_lock:
            for task_id, task in self.tasks.items():
                if task.finished_at:
                    age = (now - task.finished_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)

            for task_id in to_remove:
                del self.tasks[task_id]
                logger.info(f"清理旧任务: {task_id}")


# 全局单例
task_manager = TaskManager()
