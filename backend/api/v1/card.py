from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException
from sqlalchemy.orm import Session
from backend.models.card import Card, CardORM
from backend.services.card_service import get_cards, get_card, create_card, update_card, delete_card, bulk_create_cards, get_cards_paginated, get_cards_count
from backend.models.db import get_db
from backend.core.exceptions import (
    card_not_found_error, 
    card_create_failed_error, 
    card_update_failed_error,
    card_delete_failed_error,
    file_upload_failed_error
)
from backend.core.response import ResponseHandler
from backend.core.cache import cache
from backend.schemas.card import CardCreate, CardUpdate, CardResponse
from typing import List, Optional
from fastapi.responses import StreamingResponse
import csv
import io
import openpyxl
import logging
import os
import shutil
from datetime import datetime
import glob
from PIL import Image
import json
import tempfile

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# 創建圖片存儲目錄
UPLOAD_DIR = "output/card_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/")
def list_cards(
    skip: int = Query(0, ge=0, description="跳過記錄數"),
    limit: int = Query(100, ge=1, le=1000, description="每頁記錄數"),
    search: Optional[str] = Query(None, description="搜索關鍵詞"),
    use_pagination: bool = Query(False, description="是否使用分頁"),
    db: Session = Depends(get_db)
):
    try:
        if use_pagination:
            # 使用分頁查詢
            cards, total = get_cards_paginated(db, skip=skip, limit=limit, search=search)
            return ResponseHandler.success(
                data={
                    "items": cards,
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "has_more": (skip + len(cards)) < total
                },
                message="獲取名片列表成功"
            )
        else:
            # 保持向後兼容，返回所有數據
            cards = get_cards(db)
            return ResponseHandler.success(
                data=cards,
                message="獲取名片列表成功"
            )
    except Exception as e:
        logger.error(f"獲取名片列表失敗: {str(e)}")
        return ResponseHandler.error(
            message="獲取名片列表失敗",
            error=e
        )

@router.get("/stats")
def get_cards_stats(db: Session = Depends(get_db)):
    """獲取名片統計數據 - 全局統計，不受篩選影響"""
    try:
        # 獲取所有名片進行統計
        all_cards = get_cards(db)
        
        # 統計邏輯與前端保持一致
        def check_card_status_backend(card):
            """後端統計用的狀態檢查邏輯，與前端 checkCardStatus 保持一致"""
            missing_fields = []
            
            # 檢查姓名 (中文OR英文)
            name_zh = card.get('name', '').strip() if card.get('name') else ''
            name_en = card.get('name_en', '').strip() if card.get('name_en') else ''
            if not (name_zh or name_en):
                missing_fields.append('姓名')
            
            # 檢查公司 (中文OR英文)
            company_zh = card.get('company_name', '').strip() if card.get('company_name') else ''
            company_en = card.get('company_name_en', '').strip() if card.get('company_name_en') else ''
            if not (company_zh or company_en):
                missing_fields.append('公司')
            
            # 檢查職位或部門 (職位或部門有其中一個即可)
            position_zh = card.get('position', '').strip() if card.get('position') else ''
            position_en = card.get('position_en', '').strip() if card.get('position_en') else ''
            position1_zh = card.get('position1', '').strip() if card.get('position1') else ''
            position1_en = card.get('position1_en', '').strip() if card.get('position1_en') else ''
            has_position = bool(position_zh or position_en or position1_zh or position1_en)
            
            dept1_zh = card.get('department1', '').strip() if card.get('department1') else ''
            dept1_en = card.get('department1_en', '').strip() if card.get('department1_en') else ''
            dept2_zh = card.get('department2', '').strip() if card.get('department2') else ''
            dept2_en = card.get('department2_en', '').strip() if card.get('department2_en') else ''
            dept3_zh = card.get('department3', '').strip() if card.get('department3') else ''
            dept3_en = card.get('department3_en', '').strip() if card.get('department3_en') else ''
            has_department = bool(dept1_zh or dept1_en or dept2_zh or dept2_en or dept3_zh or dept3_en)
            
            if not (has_position or has_department):
                missing_fields.append('職位或部門')
            
            # 檢查聯絡方式 (手機 OR 公司電話 OR Email OR Line ID，至少要有一個)
            mobile = card.get('mobile_phone', '').strip() if card.get('mobile_phone') else ''
            phone1 = card.get('company_phone1', '').strip() if card.get('company_phone1') else ''
            phone2 = card.get('company_phone2', '').strip() if card.get('company_phone2') else ''
            email = card.get('email', '').strip() if card.get('email') else ''
            line_id = card.get('line_id', '').strip() if card.get('line_id') else ''
            if not (mobile or phone1 or phone2 or email or line_id):
                missing_fields.append('聯絡方式')
            
            return {
                'status': 'normal' if len(missing_fields) == 0 else 'problem',
                'missing_fields': missing_fields,
                'missing_count': len(missing_fields)
            }
        
        # 計算統計數據
        total_count = len(all_cards)
        normal_count = 0
        problem_count = 0
        
        for card in all_cards:
            card_status = check_card_status_backend(card)
            if card_status['status'] == 'normal':
                normal_count += 1
            else:
                problem_count += 1
        
        stats_data = {
            'total': total_count,
            'normal': normal_count,
            'problem': problem_count
        }
        
        return ResponseHandler.success(
            data=stats_data,
            message="獲取統計數據成功"
        )
        
    except Exception as e:
        logger.error(f"獲取統計數據失敗: {str(e)}")
        return ResponseHandler.error(
            message="獲取統計數據失敗",
            error=e
        )

@router.get("/{card_id}")
def read_card(card_id: int, db: Session = Depends(get_db)):
    try:
        # 嘗試從緩存獲取
        cache_key = f"card_{card_id}"
        cached_card = cache.get(cache_key)
        if cached_card:
            return ResponseHandler.success(
                data=cached_card,
                message="獲取名片成功"
            )
        
        card = get_card(db, card_id)
        if not card:
            return ResponseHandler.error(
                message=f"找不到ID為 {card_id} 的名片",
                status_code=404
            )
        
        # 緩存結果
        cache.set(cache_key, card, ttl_minutes=10)
        
        return ResponseHandler.success(
            data=card,
            message="獲取名片成功"
        )
    except Exception as e:
        logger.error(f"獲取名片失敗: {str(e)}")
        return ResponseHandler.error(
            message="獲取名片失敗",
            error=e
        )

@router.post("/")
async def add_card(
    # 基本資訊（中英文）
    name: str = Form(...),
    name_en: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    company_name_en: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    position_en: Optional[str] = Form(None),
    position1: Optional[str] = Form(None),
    position1_en: Optional[str] = Form(None),
    
    # 部門組織架構（中英文，三層）
    department1: Optional[str] = Form(None),
    department1_en: Optional[str] = Form(None),
    department2: Optional[str] = Form(None),
    department2_en: Optional[str] = Form(None),
    department3: Optional[str] = Form(None),
    department3_en: Optional[str] = Form(None),
    
    # 聯絡資訊
    mobile_phone: Optional[str] = Form(None),
    company_phone1: Optional[str] = Form(None),
    company_phone2: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    line_id: Optional[str] = Form(None),
    
    # 地址資訊（中英文）
    company_address1: Optional[str] = Form(None),
    company_address1_en: Optional[str] = Form(None),
    company_address2: Optional[str] = Form(None),
    company_address2_en: Optional[str] = Form(None),
    
    # 備註資訊
    note1: Optional[str] = Form(None),
    note2: Optional[str] = Form(None),
    
    # 圖片文件和OCR數據
    front_image: Optional[UploadFile] = File(None),
    back_image: Optional[UploadFile] = File(None),
    front_ocr_text: Optional[str] = Form(None),
    back_ocr_text: Optional[str] = Form(None),
    
    db: Session = Depends(get_db)
):
    """
    創建新名片，支持圖片上傳和OCR數據
    """
    try:
        # 保存圖片文件
        front_image_path = None
        back_image_path = None
        
        if front_image and front_image.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            front_filename = f"front_{timestamp}_{front_image.filename}"
            front_image_path = os.path.join(UPLOAD_DIR, front_filename)
            
            with open(front_image_path, "wb") as buffer:
                shutil.copyfileobj(front_image.file, buffer)
        
        if back_image and back_image.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            back_filename = f"back_{timestamp}_{back_image.filename}"
            back_image_path = os.path.join(UPLOAD_DIR, back_filename)
            
            with open(back_image_path, "wb") as buffer:
                shutil.copyfileobj(back_image.file, buffer)
        
        # 創建名片數據對象
        card_data = Card(
            name=name,
            name_en=name_en,
            company_name=company_name,
            company_name_en=company_name_en,
            position=position,
            position_en=position_en,
            position1=position1,
            position1_en=position1_en,
            department1=department1,
            department1_en=department1_en,
            department2=department2,
            department2_en=department2_en,
            department3=department3,
            department3_en=department3_en,
            mobile_phone=mobile_phone,
            company_phone1=company_phone1,
            company_phone2=company_phone2,
            email=email,
            line_id=line_id,
            company_address1=company_address1,
            company_address1_en=company_address1_en,
            company_address2=company_address2,
            company_address2_en=company_address2_en,
            note1=note1,
            note2=note2,
            front_image_path=front_image_path,
            back_image_path=back_image_path,
            front_ocr_text=front_ocr_text,
            back_ocr_text=back_ocr_text
        )
        
        created_card = create_card(db, card_data)
        return ResponseHandler.success(
            data=created_card,
            message="名片創建成功",
            status_code=201
        )
        
    except Exception as e:
        logger.error(f"創建名片失敗: {str(e)}")
        return ResponseHandler.error(
            message="創建名片失敗",
            error=e,
            status_code=400
        )

@router.put("/{card_id}")
async def edit_card(
    card_id: int,
    # 基本資訊（中英文） - 修復：使用空字符串作為默認值以支持清空欄位
    name: str = Form(...),
    name_en: str = Form(""),
    company_name: str = Form(""),
    company_name_en: str = Form(""),
    position: str = Form(""),
    position_en: str = Form(""),
    position1: str = Form(""),
    position1_en: str = Form(""),
    
    # 部門組織架構（中英文，三層）
    department1: str = Form(""),
    department1_en: str = Form(""),
    department2: str = Form(""),
    department2_en: str = Form(""),
    department3: str = Form(""),
    department3_en: str = Form(""),
    
    # 聯絡資訊
    mobile_phone: str = Form(""),
    company_phone1: str = Form(""),
    company_phone2: str = Form(""),
    email: str = Form(""),
    line_id: str = Form(""),
    
    # 地址資訊（中英文）
    company_address1: str = Form(""),
    company_address1_en: str = Form(""),
    company_address2: str = Form(""),
    company_address2_en: str = Form(""),
    
    # 備註資訊
    note1: str = Form(""),
    note2: str = Form(""),
    
    # 可選的圖片文件和OCR數據
    front_image: Optional[UploadFile] = File(None),
    back_image: Optional[UploadFile] = File(None),
    front_ocr_text: str = Form(""),
    back_ocr_text: str = Form(""),
    
    db: Session = Depends(get_db)
):
    """
    更新名片資料，支持圖片上傳和OCR數據
    """
    try:
        # 檢查名片是否存在
        existing_card = get_card(db, card_id)
        if not existing_card:
            return ResponseHandler.error(
                message=f"找不到ID為 {card_id} 的名片",
                status_code=404
            )
        
        # 處理圖片文件
        front_image_path = existing_card.get('front_image_path')
        back_image_path = existing_card.get('back_image_path')
        
        if front_image and front_image.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            front_filename = f"front_{timestamp}_{front_image.filename}"
            front_image_path = os.path.join(UPLOAD_DIR, front_filename)
            
            with open(front_image_path, "wb") as buffer:
                shutil.copyfileobj(front_image.file, buffer)
        
        if back_image and back_image.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            back_filename = f"back_{timestamp}_{back_image.filename}"
            back_image_path = os.path.join(UPLOAD_DIR, back_filename)
            
            with open(back_image_path, "wb") as buffer:
                shutil.copyfileobj(back_image.file, buffer)
        
        # 創建名片更新數據對象
        card_data = Card(
            id=card_id,
            name=name,
            name_en=name_en,
            company_name=company_name,
            company_name_en=company_name_en,
            position=position,
            position_en=position_en,
            position1=position1,
            position1_en=position1_en,
            department1=department1,
            department1_en=department1_en,
            department2=department2,
            department2_en=department2_en,
            department3=department3,
            department3_en=department3_en,
            mobile_phone=mobile_phone,
            company_phone1=company_phone1,
            company_phone2=company_phone2,
            email=email,
            line_id=line_id,
            company_address1=company_address1,
            company_address1_en=company_address1_en,
            company_address2=company_address2,
            company_address2_en=company_address2_en,
            note1=note1,
            note2=note2,
            front_image_path=front_image_path,
            back_image_path=back_image_path,
            front_ocr_text=front_ocr_text if front_ocr_text else existing_card.get('front_ocr_text'),
            back_ocr_text=back_ocr_text if back_ocr_text else existing_card.get('back_ocr_text'),
            created_at=existing_card.get('created_at')  # 保持原創建時間
        )
        
        updated = update_card(db, card_id, card_data)
        if not updated:
            return ResponseHandler.error(
                message="更新名片失敗",
                status_code=400
            )
        
        # 清除緩存
        cache_key = f"card_{card_id}"
        cache.delete(cache_key)
        
        return ResponseHandler.success(
            data=updated,
            message="名片更新成功"
        )
        
    except Exception as e:
        logger.error(f"更新名片失敗: {str(e)}")
        return ResponseHandler.error(
            message="更新名片失敗",
            error=e,
            status_code=400
        )

@router.delete("/all")
def delete_all_cards(db: Session = Depends(get_db)):
    """刪除所有名片"""
    try:
        # 獲取所有名片數量
        total_count = db.query(CardORM).count()
        
        if total_count == 0:
            return ResponseHandler.success(
                message="沒有名片需要刪除"
            )
        
        # 直接使用 SQL 刪除所有記錄
        deleted_count = db.query(CardORM).delete()
        db.commit()
        
        # 清除所有相關緩存
        cache.clear()
        
        logger.info(f"成功刪除 {deleted_count}/{total_count} 張名片")
        
        return ResponseHandler.success(
            data={
                "deleted_count": deleted_count,
                "total_count": total_count
            },
            message=f"成功刪除 {deleted_count} 張名片"
        )
        
    except Exception as e:
        logger.error(f"刪除所有名片失敗: {str(e)}")
        db.rollback()
        return ResponseHandler.error(
            message="刪除所有名片失敗",
            error=e,
            status_code=400
        )

@router.delete("/{card_id}")
def remove_card(card_id: int, db: Session = Depends(get_db)):
    try:
        card = get_card(db, card_id)
        if not card:
            return ResponseHandler.error(
                message=f"找不到ID為 {card_id} 的名片",
                status_code=404
            )
        
        if not delete_card(db, card_id):
            return ResponseHandler.error(
                message="刪除名片失敗",
                status_code=400
            )
        
        return ResponseHandler.success(
            message="名片刪除成功"
        )
    except Exception as e:
        logger.error(f"刪除名片失敗: {str(e)}")
        return ResponseHandler.error(
            message="刪除名片失敗",
            error=e,
            status_code=400
        )

@router.get("/export/download")
def export_cards(format: str = Query("csv", enum=["csv", "excel", "vcard"]), db: Session = Depends(get_db)):
    """匯出名片數據"""
    try:
        logger.info(f"開始匯出，格式: {format}")
        cards = get_cards(db)
        logger.info(f"找到 {len(cards)} 張名片")
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            # 更新為新的標準化欄位
            writer.writerow([
                "姓名", "公司名稱", "職位", "部門1", "手機", "公司電話", 
                "Email", "Line ID", "備註", "公司地址一", "公司地址二"
            ])
            for card in cards:
                writer.writerow([
                    card.get('name', '') or "",
                    card.get('company_name', '') or "",
                    card.get('position', '') or "",
                    card.get('department1', '') or "",
                    card.get('mobile_phone', '') or "",
                    card.get('company_phone1', '') or "",
                    card.get('email', '') or "",
                    card.get('line_id', '') or "",
                    card.get('note1', '') or "",
                    card.get('company_address1', '') or "",
                    card.get('company_address2', '') or ""
                ])
            output.seek(0)
            content = output.getvalue().encode('utf-8-sig')  # 添加BOM以支持中文
            
            return StreamingResponse(
                io.BytesIO(content),
                media_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=cards.csv",
                    "Content-Type": "text/csv; charset=utf-8"
                }
            )
            
        elif format == "excel":
            try:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "名片資料"
                
                # 設置標題行 - 更新為新的標準化欄位
                headers = [
                    "姓名", "公司名稱", "職位", "部門1", "手機", "公司電話", 
                    "Email", "Line ID", "備註", "公司地址一", "公司地址二"
                ]
                ws.append(headers)
                
                # 添加數據
                for card in cards:
                    ws.append([
                        card.get('name', '') or "",
                        card.get('company_name', '') or "",
                        card.get('position', '') or "",
                        card.get('department1', '') or "",
                        card.get('mobile_phone', '') or "",
                        card.get('company_phone1', '') or "",
                        card.get('email', '') or "",
                        card.get('line_id', '') or "",
                        card.get('note1', '') or "",
                        card.get('company_address1', '') or "",
                        card.get('company_address2', '') or ""
                    ])
                
                # 自動調整列寬
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[column_letter].width = adjusted_width
                
                output = io.BytesIO()
                wb.save(output)
                output.seek(0)
                
                logger.info("EXCEL文件生成成功")
                
                return StreamingResponse(
                    output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": "attachment; filename=cards.xlsx",
                        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    }
                )
                
            except Exception as e:
                logger.error(f"生成EXCEL文件時發生錯誤: {str(e)}")
                raise HTTPException(status_code=500, detail=f"EXCEL生成失敗: {str(e)}")
                
        elif format == "vcard":
            output = io.StringIO()
            for card in cards:
                output.write(f"BEGIN:VCARD\nVERSION:3.0\n")
                if card.get('name'):
                    output.write(f"FN:{card.get('name')}\n")
                if card.get('company_name'):
                    output.write(f"ORG:{card.get('company_name')}\n")
                if card.get('position'):
                    output.write(f"TITLE:{card.get('position')}\n")
                if card.get('company_phone1'):
                    output.write(f"TEL;TYPE=WORK,VOICE:{card.get('company_phone1')}\n")
                if card.get('mobile_phone'):
                    output.write(f"TEL;TYPE=CELL:{card.get('mobile_phone')}\n")
                if card.get('email'):
                    output.write(f"EMAIL;TYPE=INTERNET:{card.get('email')}\n")
                if card.get('company_address1'):
                    address = card.get('company_address1')
                    if card.get('company_address2'):
                        address += f" {card.get('company_address2')}"
                    output.write(f"ADR;TYPE=WORK:;;{address};;;;\n")
                output.write("END:VCARD\n")
            output.seek(0)
            content = output.getvalue().encode('utf-8')
            
            return StreamingResponse(
                io.BytesIO(content),
                media_type="text/vcard",
                headers={
                    "Content-Disposition": "attachment; filename=cards.vcf",
                    "Content-Type": "text/vcard; charset=utf-8"
                }
            )
        else:
            raise HTTPException(status_code=400, detail="不支援的匯出格式")
            
    except Exception as e:
        logger.error(f"匯出過程中發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.post("/batch-import")
async def batch_import_cards(db: Session = Depends(get_db)):
    """
    使用集成到OCRService的批量導入功能 - 整合智能批量處理
    """
    try:
        from backend.services.ocr_service_temp import OCRService
        from backend.services.card_enhancement_service import BatchProcessingService
        
        # 初始化服務
        ocr_service = OCRService()
        batch_service = BatchProcessingService(ocr_service.card_enhancer)
        
        # 批量處理資料夾
        batch_folder = "ocr_card_background/uploads"
        
        if not os.path.exists(batch_folder):
            return ResponseHandler.error(
                message=f"批量導入資料夾不存在: {batch_folder}",
                status_code=404
            )
        
        # 獲取所有圖片文件
        image_files = []
        for ext in ['.jpg', '.jpeg', '.png']:
            image_files.extend(glob.glob(os.path.join(batch_folder, f'*{ext}')))
            image_files.extend(glob.glob(os.path.join(batch_folder, f'*{ext.upper()}')))
        
        if not image_files:
            return ResponseHandler.error(
                message=f"在 {batch_folder} 中未找到任何圖片文件",
                status_code=404
            )
        
        logger.info(f"找到 {len(image_files)} 張圖片準備智能批量處理")
        
        # 記錄開始時的記憶體狀況
        batch_service.log_memory_status("批量導入開始前")
        
        success_count = 0
        error_list = []
        
        # 使用智能批量處理進行OCR和數據庫操作
        try:
            processed_count = 0
            
            # 分批處理圖片
            for image_file in image_files:
                try:
                    processed_count += 1
                    
                    # 記憶體檢查和清理
                    if batch_service.should_cleanup_memory():
                        batch_service.cleanup_memory()
                        logger.info(f"處理第 {processed_count}/{len(image_files)} 張時執行記憶體清理")
                    
                    logger.info(f"處理第 {processed_count}/{len(image_files)} 張圖片: {os.path.basename(image_file)}")
                    
                    # 使用OCRService處理圖片
                    ocr_result = ocr_service.process_single_image(image_file)
                    
                    if not ocr_result or not any(ocr_result.values()):
                        error_list.append(f"{os.path.basename(image_file)}: OCR處理返回空結果")
                        continue
                    
                    # 檢查必要欄位
                    name = ocr_result.get('姓名', '').strip()
                    if not name:
                        # 如果沒有姓名，嘗試使用文件名作為姓名
                        filename = os.path.basename(image_file)
                        name = os.path.splitext(filename)[0]
                        ocr_result['姓名'] = name
                        logger.info(f"使用文件名作為姓名: {name}")
                    
                    # 複製圖片到正式存儲位置
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.basename(image_file)
                    new_filename = f"batch_{timestamp}_{processed_count:03d}_{filename}"
                    new_image_path = os.path.join(UPLOAD_DIR, new_filename)
                    shutil.copy2(image_file, new_image_path)
                
                    # 創建名片記錄，使用OCRService的標準欄位映射
                    card_data = Card(
                        name=ocr_result.get('姓名', name),
                        name_en=ocr_result.get('name_en', ''),
                        company_name=ocr_result.get('公司名稱', ''),
                        company_name_en=ocr_result.get('company_name_en', ''),
                        position=ocr_result.get('職位', '') or ocr_result.get('職位1', ''),
                        position_en=ocr_result.get('position_en', ''),
                        position1=ocr_result.get('職位1', ''),
                        position1_en=ocr_result.get('position1_en', ''),
                        department1=ocr_result.get('部門1', ''),
                        department1_en=ocr_result.get('Department1', ''),
                        department2=ocr_result.get('部門2', ''),
                        department2_en=ocr_result.get('Department2', ''),
                        department3=ocr_result.get('部門3', ''),
                        department3_en=ocr_result.get('Department3', ''),
                        mobile_phone=ocr_result.get('手機', ''),
                        company_phone1=ocr_result.get('公司電話1', ''),
                        company_phone2=ocr_result.get('公司電話2', ''),
                        email=ocr_result.get('Email', ''),
                        line_id=ocr_result.get('Line ID', ''),
                        company_address1=ocr_result.get('公司地址一', ''),
                        company_address1_en=ocr_result.get('company_address1_en', ''),
                        company_address2=ocr_result.get('公司地址二', ''),
                        company_address2_en=ocr_result.get('company_address2_en', ''),
                        note1=ocr_result.get('note1', f'智能批量導入 - {filename}'),
                        note2=ocr_result.get('note2', f'增強處理+OCR識別，字段數: {len(ocr_result)}'),
                        front_image_path=new_image_path,
                        front_ocr_text=json.dumps(ocr_result, ensure_ascii=False)
                    )
                    
                    # 保存到數據庫
                    created_card = create_card(db, card_data)
                    success_count += 1
                    logger.info(f"成功創建名片: {created_card.get('name', '未知')} (ID: {created_card.get('id', '未知')})")
                    
                except Exception as e:
                    error_msg = f"{os.path.basename(image_file)}: {str(e)}"
                    error_list.append(error_msg)
                    logger.error(f"處理圖片失敗: {error_msg}")
                    continue
        
        finally:
            # 記錄結束時的記憶體狀況和最終清理
            batch_service.log_memory_status("批量導入結束後")
            batch_service.cleanup_memory()
        
        # 返回處理結果
        result_message = f"批量導入完成！成功處理 {success_count}/{len(image_files)} 張名片"
        if error_list:
            result_message += f"，失敗 {len(error_list)} 張"
        
        return ResponseHandler.success(
            data={
                "total_files": len(image_files),
                "processed": processed_count,
                "success": success_count,
                "errors": len(error_list),
                "error_details": error_list[:10],  # 只返回前10個錯誤
                "total_processed": success_count
            },
            message=result_message
        )
        
    except Exception as e:
        logger.error(f"批量導入過程中發生錯誤: {str(e)}")
        return ResponseHandler.error(
            message=f"批量導入失敗: {str(e)}",
            status_code=500
        )

@router.post("/text-import")
async def text_import_cards(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    文本導入功能：支持Excel和CSV文件的自動欄位識別和批量導入
    """
    try:
        from backend.services.text_import_service import TextImportService
        
        # 檢查文件格式
        if not file.filename:
            return ResponseHandler.error(
                message="文件名不能為空",
                status_code=400
            )
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        supported_formats = ['.xlsx', '.xls', '.csv']
        
        if file_extension not in supported_formats:
            return ResponseHandler.error(
                message=f"不支持的文件格式 {file_extension}，請使用 {', '.join(supported_formats)} 格式",
                status_code=400
            )
        
        # 檢查文件大小（防止系統崩潰）
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        max_size_mb = 50  # 50MB限制
        
        if len(content) > max_size_mb * 1024 * 1024:
            return ResponseHandler.error(
                message=f"文件過大（{file_size_mb:.1f}MB），請使用小於 {max_size_mb}MB 的文件",
                status_code=413
            )
        
        # 重置文件指針
        await file.seek(0)
        
        # 初始化文本導入服務
        text_import_service = TextImportService()
        
        # 創建臨時文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            # 保存上傳的文件（content已經讀取過了）
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            logger.info(f"開始處理文本導入文件: {file.filename}")
            
            # 處理文件
            processed_records, result_stats = text_import_service.process_file(temp_file_path)
            
            if not processed_records:
                return ResponseHandler.error(
                    message="文件中沒有找到有效的名片數據",
                    status_code=400
                )
            
            # 檢查重要欄位缺失和去重
            def check_required_fields(record_data):
                """檢查重要欄位缺失 - 中英文任一有值即視為完整"""
                missing_fields = []
                
                # 檢查姓名 (中文 OR 英文)
                name_zh = record_data.get('姓名', '').strip()
                name_en = record_data.get('name_en', '').strip()
                if not (name_zh or name_en):
                    missing_fields.append('姓名/name_en')
                
                # 檢查公司名稱 (中文 OR 英文)
                company_zh = record_data.get('公司名稱', '').strip()
                company_en = record_data.get('company_name_en', '').strip()
                if not (company_zh or company_en):
                    missing_fields.append('公司名稱/company_name_en')
                
                # 檢查職位或部門 (職位或部門有其中一個即可)
                # 檢查職位
                position_zh = record_data.get('職位', '').strip()
                position_en = record_data.get('position_en', '').strip()
                position1_zh = record_data.get('職位1', '').strip()
                position1_en = record_data.get('position1_en', '').strip()
                has_position = bool(position_zh or position_en or position1_zh or position1_en)
                
                # 檢查部門
                dept1_zh = record_data.get('部門1', '').strip()
                dept1_en = record_data.get('department1_en', '').strip()
                dept2_zh = record_data.get('部門2', '').strip()
                dept2_en = record_data.get('department2_en', '').strip()
                dept3_zh = record_data.get('部門3', '').strip()
                dept3_en = record_data.get('department3_en', '').strip()
                has_department = bool(dept1_zh or dept1_en or dept2_zh or dept2_en or dept3_zh or dept3_en)
                
                # 職位或部門至少要有一個
                if not (has_position or has_department):
                    missing_fields.append('職位或部門')
                
                # 檢查聯絡方式 (手機 OR 公司電話 OR Email OR Line ID，至少要有一個)
                mobile = record_data.get('手機', '').strip()
                phone1 = record_data.get('公司電話1', '').strip()
                phone2 = record_data.get('公司電話2', '').strip()
                email = record_data.get('email', '').strip()
                line_id = record_data.get('line_id', '').strip()
                if not (mobile or phone1 or phone2 or email or line_id):
                    missing_fields.append('聯絡方式(電話/Email/Line)')
                
                return missing_fields
            
            # 優化重複檢查：預先載入所有現有名片，避免重複查詢
            existing_cards_cache = {}
            all_existing_cards = get_cards(db)
            for existing_card in all_existing_cards:
                # 創建複合鍵用於快速比對
                key = f"{existing_card.get('name', '')}|{existing_card.get('company_name', '')}|{existing_card.get('mobile_phone', '')}"
                existing_cards_cache[key] = existing_card
            
            def is_duplicate_card(record_data):
                """檢查是否為重複名片 - 使用緩存避免重複查詢"""
                key = f"{record_data.get('姓名', '')}|{record_data.get('公司名稱', '')}|{record_data.get('手機', '')}"
                return key in existing_cards_cache

            # 批量創建名片記錄 - 優化版本
            duplicate_count = 0
            problem_count = 0
            cards_to_create = []  # 準備批量創建的名片
            batch_size = 50  # 每批處理數量
            
            # 第一階段：準備所有要創建的名片
            for i, record_data in enumerate(processed_records):
                # 檢查重複
                if is_duplicate_card(record_data):
                    duplicate_count += 1
                    logger.info(f"跳過重複名片: {record_data.get('姓名', '未知')}")
                    continue
                
                # 檢查重要欄位缺失
                missing_fields = check_required_fields(record_data)
                is_problem_card = len(missing_fields) > 0
                
                if is_problem_card:
                    problem_count += 1
                    # 在備註中標記問題
                    note1 = record_data.get('note1', '') + f" [問題名片: 缺少{', '.join(missing_fields)}]"
                else:
                    note1 = record_data.get('note1', f'文本導入 - {file.filename}')
                
                # 創建名片對象
                card_data = Card(
                    name=record_data.get('姓名', ''),
                    name_en=record_data.get('name_en', ''),
                    company_name=record_data.get('公司名稱', ''),
                    company_name_en=record_data.get('company_name_en', ''),
                    position=record_data.get('職位', ''),
                    position_en=record_data.get('position_en', ''),
                    position1=record_data.get('職位1', ''),
                    position1_en=record_data.get('position1_en', ''),
                    department1=record_data.get('部門1', ''),
                    department1_en=record_data.get('department1_en', ''),
                    department2=record_data.get('部門2', ''),
                    department2_en=record_data.get('department2_en', ''),
                    department3=record_data.get('部門3', ''),
                    department3_en=record_data.get('department3_en', ''),
                    mobile_phone=record_data.get('手機', ''),
                    company_phone1=record_data.get('公司電話1', ''),
                    company_phone2=record_data.get('公司電話2', ''),
                    email=record_data.get('email', ''),
                    line_id=record_data.get('line_id', ''),
                    company_address1=record_data.get('公司地址一', ''),
                    company_address1_en=record_data.get('company_address1_en', ''),
                    company_address2=record_data.get('公司地址二', ''),
                    company_address2_en=record_data.get('company_address2_en', ''),
                    note1=note1,
                    note2=record_data.get('note2', f'導入時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                )
                
                cards_to_create.append((card_data, is_problem_card, i))
            
            # 第二階段：批量保存到數據庫
            success_count = 0
            error_list = []
            
            # 分批處理
            for batch_start in range(0, len(cards_to_create), batch_size):
                batch_end = min(batch_start + batch_size, len(cards_to_create))
                batch = cards_to_create[batch_start:batch_end]
                
                # 提取 Card 對象列表
                batch_cards = [card_data for card_data, _, _ in batch]
                
                try:
                    # 批量創建
                    created_cards, batch_errors = bulk_create_cards(db, batch_cards)
                    
                    # 統計成功數量
                    success_count += len(created_cards)
                    
                    # 記錄錯誤
                    for idx, error in enumerate(batch_errors):
                        original_idx = batch[idx][2] if idx < len(batch) else batch_start + idx
                        error_list.append(f"第 {original_idx + 1} 條記錄: {error}")
                    
                    # 記錄日誌
                    for created_card in created_cards:
                        logger.info(f"成功創建名片: {created_card.get('name', '未知')} (批次 {batch_start//batch_size + 1})")
                    
                    logger.info(f"批次 {batch_start//batch_size + 1} 完成: 成功 {len(created_cards)}/{len(batch)} 筆")
                    
                except Exception as e:
                    # 批次失敗，記錄所有該批次的錯誤
                    for _, _, original_idx in batch:
                        error_msg = f"第 {original_idx + 1} 條記錄: 批次處理失敗 - {str(e)}"
                        error_list.append(error_msg)
                    logger.error(f"批次處理失敗: {str(e)}")

            # 統一統計邏輯：計算完整的導入統計
            file_stats = result_stats
            
            # 最終統計數據
            final_stats = {
                # 文件處理階段統計
                "file_total_rows": file_stats.get('total_rows', 0),
                "file_processed_count": file_stats.get('processed_count', 0), 
                "file_error_count": file_stats.get('error_count', 0),
                
                # 數據庫保存階段統計
                "db_total_records": len(processed_records),  # 準備保存的記錄數
                "db_success_count": success_count,  # 成功保存的記錄數
                "db_duplicate_count": duplicate_count,  # 跳過重複的記錄數
                "db_problem_count": problem_count,  # 保存但有問題的記錄數
                "db_error_count": len(error_list),  # 保存失敗的記錄數
                "batch_size": 1,  # 批次大小
                
                # 最終結果統計 (對用戶最重要的數據)
                "final_success_count": success_count,  # 最終成功導入數量
                "final_failed_count": duplicate_count + len(error_list),  # 最終失敗數量 (重複+錯誤)
                "final_total_attempted": len(processed_records),  # 嘗試導入的總數
                
                # 詳細信息
                "column_mapping": file_stats.get('column_mapping', {}),
                "error_details": error_list[:5],
                "imported_file": file.filename
            }
            
            # 組合返回消息 - 使用統一的統計邏輯
            result_message = f"文本導入完成！"
            result_message += f"成功導入 {final_stats['final_success_count']} 張名片"
            
            if duplicate_count > 0:
                result_message += f"，跳過重複 {duplicate_count} 張"
            if problem_count > 0:
                result_message += f"，問題名片 {problem_count} 張"  
            if len(error_list) > 0:
                result_message += f"，失敗 {len(error_list)} 張"
                
            return ResponseHandler.success(
                data=final_stats,
                message=result_message
            )
            
        finally:
            # 清理臨時文件
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"清理臨時文件失敗: {e}")
        
    except Exception as e:
        logger.error(f"文本導入過程中發生錯誤: {str(e)}")
        return ResponseHandler.error(
            message=f"文本導入失敗: {str(e)}",
            status_code=500
        ) 