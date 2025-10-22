from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, ForeignKey, Float
from sqlalchemy.orm import relationship
from backend.models.db import Base
import datetime

class CardORM(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, index=True)
    
    # 基本資訊欄位（中英文）
    name_zh = Column(String(100), index=True)                 # 姓名(中文)
    name_en = Column(String(100))                             # 英文姓名
    company_name_zh = Column(String(200), index=True)        # 公司名稱(中文)
    company_name_en = Column(String(200))                     # 英文公司名稱
    position_zh = Column(String(100))                        # 職位(中文)
    position_en = Column(String(100))                        # 英文職位
    position1_zh = Column(String(255))                       # 職位1(中文)
    position1_en = Column(String(255))                       # 職位1(英文)
    
    # 部門組織架構（中英文，三層）
    department1_zh = Column(String(100))                     # 部門1(中文)
    department1_en = Column(String(100))                     # 部門1(英文)
    department2_zh = Column(String(100))                     # 部門2(中文)
    department2_en = Column(String(100))                     # 部門2(英文)
    department3_zh = Column(String(100))                     # 部門3(中文)
    department3_en = Column(String(100))                     # 部門3(英文)
    
    # 聯絡資訊
    mobile_phone = Column(String(50), index=True)            # 手機
    company_phone1 = Column(String(50))                      # 公司電話1
    company_phone2 = Column(String(50))                      # 公司電話2
    fax = Column(String(50))                                  # 傳真號碼
    email = Column(String(200))                              # Email
    line_id = Column(String(100))                            # Line ID
    wechat_id = Column(String(100))                          # WeChat ID
    
    # 地址資訊（中英文）
    company_address1_zh = Column(String(300))                # 公司地址一(中文)
    company_address1_en = Column(String(300))                # 公司地址一(英文)
    company_address2_zh = Column(String(300))                # 公司地址二(中文)
    company_address2_en = Column(String(300))                # 公司地址二(英文)
    
    # 備註資訊
    note1 = Column(Text)                          # 備註1
    note2 = Column(Text)                          # 備註2
    
    # 系統管理欄位
    front_image_path = Column(String(500))        # 正面圖片路径
    back_image_path = Column(String(500))         # 反面圖片路径
    front_ocr_text = Column(Text)                 # 正面OCR原始文字
    back_ocr_text = Column(Text)                  # 反面OCR原始文字
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # AI 产业分类字段
    industry_category = Column(String(50), index=True)           # 产业分类：防詐/旅宿/工業應用/食品業/其他
    classification_confidence = Column(Float)                    # 分类信心度 (0-100)
    classification_reason = Column(Text)                         # 分类理由
    classified_at = Column(DateTime, index=True)                 # 分类时间

    # 複合索引，優化常見查詢
    __table_args__ = (
        Index('idx_name_company', 'name_zh', 'company_name_zh'),  # 姓名+公司複合索引
        Index('idx_name_phone', 'name_zh', 'mobile_phone'),       # 姓名+手機複合索引
    )

class Card(BaseModel):
    id: Optional[int] = None
    
    # 基本資訊欄位（中英文）
    name_zh: Optional[str] = None                 # 姓名(中文)
    name_en: Optional[str] = None                 # 英文姓名
    company_name_zh: Optional[str] = None         # 公司名稱(中文)
    company_name_en: Optional[str] = None         # 英文公司名稱
    position_zh: Optional[str] = None             # 職位(中文)
    position_en: Optional[str] = None             # 英文職位
    position1_zh: Optional[str] = None            # 職位1(中文)
    position1_en: Optional[str] = None            # 職位1(英文)
    
    # 部門組織架構（中英文，三層）
    department1_zh: Optional[str] = None          # 部門1(中文)
    department1_en: Optional[str] = None          # 部門1(英文)
    department2_zh: Optional[str] = None          # 部門2(中文)
    department2_en: Optional[str] = None          # 部門2(英文)
    department3_zh: Optional[str] = None          # 部門3(中文)
    department3_en: Optional[str] = None          # 部門3(英文)
    
    # 聯絡資訊
    mobile_phone: Optional[str] = None            # 手機
    company_phone1: Optional[str] = None          # 公司電話1
    company_phone2: Optional[str] = None          # 公司電話2
    fax: Optional[str] = None                     # 傳真號碼
    email: Optional[str] = None                   # Email
    line_id: Optional[str] = None                 # Line ID
    wechat_id: Optional[str] = None               # WeChat ID
    
    # 地址資訊（中英文）
    company_address1_zh: Optional[str] = None     # 公司地址一(中文)
    company_address1_en: Optional[str] = None     # 公司地址一(英文)
    company_address2_zh: Optional[str] = None     # 公司地址二(中文)
    company_address2_en: Optional[str] = None     # 公司地址二(英文)
    
    # 備註資訊
    note1: Optional[str] = None                   # 備註1
    note2: Optional[str] = None                   # 備註2
    
    # 系統管理欄位
    front_image_path: Optional[str] = None        # 正面圖片路径
    back_image_path: Optional[str] = None         # 反面圖片路径
    front_ocr_text: Optional[str] = None          # 正面OCR原始文字
    back_ocr_text: Optional[str] = None           # 反面OCR原始文字
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    # AI 产业分类字段
    industry_category: Optional[str] = None       # 产业分类
    classification_confidence: Optional[float] = None  # 分类信心度
    classification_reason: Optional[str] = None   # 分类理由
    classified_at: Optional[datetime.datetime] = None  # 分类时间

    model_config = {"from_attributes": True} 