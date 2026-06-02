import os
import json
import uuid
import shutil
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from backend.services.ocr_service import OCRService
from backend.services.task_manager import task_manager
from backend.core.config import UPLOAD_DIR
from backend.models.db import SessionLocal
from backend.models.card import CardORM

logger = logging.getLogger(__name__)

router = APIRouter()
# 模塊級單例：所有 OCR 呼叫（單張掃描 + 批次 + 多用戶）共用同一個
# OCRService 實例，確保 self._llm_semaphore (Semaphore(2)) 能正確限流。
ocr_service = OCRService()

MAX_BATCH_FILES = 50
ALLOWED_EXTS = (".jpg", ".jpeg", ".png")


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
        parsed_fields = await ocr_service.parse_ocr_to_fields(request.ocr_text, request.side)
        return {
            "success": True,
            "parsed_fields": parsed_fields,
            "side": request.side
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR解析失敗: {str(e)}")


@router.post("/batch-upload")
async def batch_upload(
    files: List[UploadFile] = File(...),
    groups: str = Form(...),
):
    """
    批次上傳名片圖片並背景處理 OCR（fire-and-forget）

    Args:
        files: 圖片檔案列表（最多 MAX_BATCH_FILES 張）
        groups: JSON 字串，格式為 [{"front_index": 0, "back_index": 1 或 null}, ...]

    Returns:
        立即回傳 task_id 與 batch_id，OCR 在背景進行，C-plan：每張完成立即寫入資料庫。
    """
    # ===== 驗證 =====
    if not files:
        raise HTTPException(status_code=400, detail="請至少上傳一張圖片")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"一次最多支援 {MAX_BATCH_FILES} 張圖片，目前上傳了 {len(files)} 張",
        )

    try:
        group_list = json.loads(groups)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="groups 格式錯誤，需為 JSON array")

    if not isinstance(group_list, list) or not group_list:
        raise HTTPException(status_code=400, detail="請至少建立一組名片")

    for i, g in enumerate(group_list):
        if not isinstance(g, dict) or "front_index" not in g:
            raise HTTPException(status_code=400, detail=f"第 {i+1} 組缺少 front_index")
        front_idx = g.get("front_index")
        if not isinstance(front_idx, int) or front_idx < 0 or front_idx >= len(files):
            raise HTTPException(status_code=400, detail=f"第 {i+1} 組的 front_index 超出範圍")
        back_idx = g.get("back_index")
        if back_idx is not None:
            if not isinstance(back_idx, int) or back_idx < 0 or back_idx >= len(files):
                raise HTTPException(status_code=400, detail=f"第 {i+1} 組的 back_index 超出範圍")

    # ===== 上傳前先驗證所有副檔名，避免寫到一半才失敗留下孤兒目錄 =====
    file_exts: List[str] = []
    for i, f in enumerate(files):
        ext = os.path.splitext(f.filename or "")[1].lower() or ".jpg"
        if ext not in ALLOWED_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"第 {i+1} 個檔案格式不支援：{ext}（僅接受 {', '.join(ALLOWED_EXTS)}）",
            )
        file_exts.append(ext)

    # ===== 儲存圖片到批次目錄 =====
    batch_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = os.path.join(UPLOAD_DIR, f"batch_{timestamp}_{batch_id[:8]}")
    os.makedirs(batch_dir, exist_ok=True)

    saved_paths: List[str] = []
    try:
        for i, f in enumerate(files):
            ext = file_exts[i]
            content = await f.read()
            path = os.path.join(batch_dir, f"{i:03d}{ext}")
            with open(path, "wb") as fp:
                fp.write(content)
            saved_paths.append(path)
    except Exception:
        # 寫檔過程中發生任何錯誤，清掉這次的 batch 目錄避免留下孤兒檔案
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise

    # ===== 建立任務並排程背景處理 =====
    task_id = task_manager.create_task(total=len(group_list), batch_id=batch_id)

    # Fire-and-forget：在當前 event loop 排程，確保與 ocr_service 共用同一個 Semaphore
    asyncio.create_task(_process_batch_ocr(task_id, batch_id, saved_paths, group_list))

    logger.info(
        f"批次上傳已收件: task_id={task_id}, batch_id={batch_id}, "
        f"files={len(files)}, groups={len(group_list)}"
    )

    return {
        "success": True,
        "task_id": task_id,
        "batch_id": batch_id,
        "total_groups": len(group_list),
        "message": f"已收到 {len(files)} 張圖片，OCR 將在背景處理",
    }


async def _process_batch_ocr(
    task_id: str,
    batch_id: str,
    saved_paths: List[str],
    group_list: List[dict],
):
    """
    背景處理：依序對每一組執行 OCR，每組完成後立即寫入資料庫（C-plan）。
    單一組失敗不會中斷整體流程，會建立一張占位 Card 讓使用者可以看見並處理。
    外層 try/except 處理 per-group loop 外的意外，避免 task 卡在 PENDING。
    """
    try:
        task_manager.start_task(task_id)

        for idx, group in enumerate(group_list):
            if task_manager.is_cancelled(task_id):
                logger.info(f"批次任務 {task_id} 已取消，停止處理")
                break

            db = SessionLocal()
            front_path: Optional[str] = None
            back_path: Optional[str] = None
            try:
                front_path = saved_paths[group["front_index"]]
                back_index = group.get("back_index")
                back_path = saved_paths[back_index] if back_index is not None else None

                # 正面 OCR + 解析（共用 ocr_service 單例，Semaphore 正確生效）
                front_fields, front_ocr_text = await _ocr_and_parse(front_path, "front")

                back_ocr_text = ""
                if back_path:
                    back_fields, back_ocr_text = await _ocr_and_parse(back_path, "back")
                    # 將反面解析結果合併至正面（只填補空欄位）
                    for key, val in back_fields.items():
                        if val and not front_fields.get(key):
                            front_fields[key] = val

                name_zh = (front_fields.get("name_zh") or "").strip() or f"未命名_{idx+1}"

                card = CardORM(
                    name_zh=name_zh,
                    name_en=front_fields.get("name_en", ""),
                    company_name_zh=front_fields.get("company_name_zh", ""),
                    company_name_en=front_fields.get("company_name_en", ""),
                    position_zh=front_fields.get("position_zh", ""),
                    position_en=front_fields.get("position_en", ""),
                    position1_zh=front_fields.get("position1_zh", ""),
                    position1_en=front_fields.get("position1_en", ""),
                    department1_zh=front_fields.get("department1_zh", ""),
                    department1_en=front_fields.get("department1_en", ""),
                    department2_zh=front_fields.get("department2_zh", ""),
                    department2_en=front_fields.get("department2_en", ""),
                    department3_zh=front_fields.get("department3_zh", ""),
                    department3_en=front_fields.get("department3_en", ""),
                    mobile_phone=front_fields.get("mobile_phone", ""),
                    company_phone1=front_fields.get("company_phone1", ""),
                    company_phone2=front_fields.get("company_phone2", ""),
                    email=front_fields.get("email", ""),
                    line_id=front_fields.get("line_id", ""),
                    company_address1_zh=front_fields.get("company_address1_zh", ""),
                    company_address1_en=front_fields.get("company_address1_en", ""),
                    company_address2_zh=front_fields.get("company_address2_zh", ""),
                    company_address2_en=front_fields.get("company_address2_en", ""),
                    note1=front_fields.get("note1", ""),
                    note2=front_fields.get("note2", ""),
                    front_image_path=front_path,
                    back_image_path=back_path,
                    front_ocr_text=front_ocr_text,
                    back_ocr_text=back_ocr_text,
                    batch_id=batch_id,
                    confirmed_at=None,
                )
                db.add(card)
                db.commit()
                task_manager.update_progress(task_id, success=True)
                logger.info(
                    f"批次 {batch_id} 第 {idx+1}/{len(group_list)} 組已存入: {name_zh}"
                )

            except Exception as e:
                logger.error(
                    f"批次 {batch_id} 第 {idx+1} 組 OCR 處理失敗: {e}", exc_info=True
                )
                # 仍存入一張占位 Card，讓使用者可以看到失敗項目並後續處理
                try:
                    db.rollback()
                    placeholder = CardORM(
                        name_zh=f"辨識失敗_{idx+1}",
                        note1=f"OCR辨識失敗: {str(e)[:200]}",
                        front_image_path=front_path,
                        back_image_path=back_path,
                        batch_id=batch_id,
                        confirmed_at=None,
                    )
                    db.add(placeholder)
                    db.commit()
                except Exception as inner:
                    logger.error(f"建立失敗占位 Card 也失敗: {inner}")
                    db.rollback()
                task_manager.update_progress(task_id, success=False)
            finally:
                db.close()

        task_manager.complete_task(task_id)
        logger.info(f"批次任務 {task_id} 完成 (batch_id={batch_id})")

    except Exception as e:
        # 外層守門：捕捉 loop 外（如 task_manager.start_task）與其他意料外的錯誤，
        # 避免 asyncio fire-and-forget task 靜默死掉，使 TaskManager 卡在 PENDING。
        logger.error(
            f"批次任務 {task_id} (batch_id={batch_id}) 意外中斷: {e}", exc_info=True
        )
        try:
            task_manager.complete_task(
                task_id, error_message=f"批次處理意外中斷: {str(e)}"
            )
        except Exception as inner:
            logger.error(f"標記任務失敗也失敗: {inner}")


async def _ocr_and_parse(image_path: str, side: str):
    """
    讀檔 → OCR → 解析欄位。
    使用模塊級 ocr_service 單例，確保 _llm_semaphore 共用。
    """
    with open(image_path, "rb") as f:
        content = f.read()
    ocr_text = await ocr_service.ocr_image(content)
    parsed = await ocr_service.parse_ocr_to_fields(ocr_text, side)
    return parsed, ocr_text


@router.get("/batch-status/{task_id}")
async def batch_status(task_id: str):
    """查詢批次 OCR 處理進度"""
    status = task_manager.get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任務不存在")
    return {"success": True, "data": status}
