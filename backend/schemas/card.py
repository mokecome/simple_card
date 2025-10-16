from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
import re

class CardBase(BaseModel):
    """名片基礎模型"""
    # 基本資訊（中英文）
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="姓名")
    name_en: Optional[str] = Field(None, max_length=100, description="英文姓名")
    company_name: Optional[str] = Field(None, max_length=200, description="公司名稱")
    company_name_en: Optional[str] = Field(None, max_length=200, description="英文公司名稱")
    
    # 職位資訊
    position: Optional[str] = Field(None, max_length=100, description="職位1")
    position_en: Optional[str] = Field(None, max_length=100, description="職位1英文")
    position1: Optional[str] = Field(None, max_length=100, description="職位2")
    position1_en: Optional[str] = Field(None, max_length=100, description="職位2英文")
    
    # 部門資訊
    department1: Optional[str] = Field(None, max_length=100, description="部門1")
    department1_en: Optional[str] = Field(None, max_length=100, description="部門1英文")
    department2: Optional[str] = Field(None, max_length=100, description="部門2")
    department2_en: Optional[str] = Field(None, max_length=100, description="部門2英文")
    department3: Optional[str] = Field(None, max_length=100, description="部門3")
    department3_en: Optional[str] = Field(None, max_length=100, description="部門3英文")
    
    # 聯絡資訊
    mobile_phone: Optional[str] = Field(None, max_length=50, description="手機號碼")
    company_phone1: Optional[str] = Field(None, max_length=50, description="公司電話1")
    company_phone2: Optional[str] = Field(None, max_length=50, description="公司電話2")
    email: Optional[EmailStr] = Field(None, description="電子郵件")
    line_id: Optional[str] = Field(None, max_length=50, description="Line ID")
    
    # 地址資訊
    company_address1: Optional[str] = Field(None, max_length=200, description="公司地址1")
    company_address1_en: Optional[str] = Field(None, max_length=200, description="公司地址1英文")
    company_address2: Optional[str] = Field(None, max_length=200, description="公司地址2")
    company_address2_en: Optional[str] = Field(None, max_length=200, description="公司地址2英文")
    
    # 備註
    note1: Optional[str] = Field(None, max_length=500, description="備註1")
    note2: Optional[str] = Field(None, max_length=500, description="備註2")
    
    @field_validator('mobile_phone', 'company_phone1', 'company_phone2')
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r'^[\d\s\-\+\(\)]+$', v):
            raise ValueError('電話號碼格式不正確')
        return v
    
    @field_validator('line_id')
    @classmethod
    def validate_line_id(cls, v):
        if v and len(v) > 50:
            raise ValueError('Line ID 不能超過50個字符')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "陳曉華",
                "name_en": "Chen Xiaohua",
                "company_name": "創新科技股份有限公司",
                "company_name_en": "Innovation Technology Co., Ltd.",
                "position": "工程師",
                "position_en": "Engineer",
                "mobile_phone": "0912-345-678",
                "email": "chen@example.com"
            }
        }

class CardCreate(CardBase):
    """創建名片的請求模型"""
    pass

class CardUpdate(BaseModel):
    """更新名片的請求模型 - 所有欄位都是可選的"""
    # 基本資訊（中英文）
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    company_name_en: Optional[str] = Field(None, max_length=200)
    
    # 職位資訊
    position: Optional[str] = Field(None, max_length=100)
    position_en: Optional[str] = Field(None, max_length=100)
    position1: Optional[str] = Field(None, max_length=100)
    position1_en: Optional[str] = Field(None, max_length=100)
    
    # 部門資訊
    department1: Optional[str] = Field(None, max_length=100)
    department1_en: Optional[str] = Field(None, max_length=100)
    department2: Optional[str] = Field(None, max_length=100)
    department2_en: Optional[str] = Field(None, max_length=100)
    department3: Optional[str] = Field(None, max_length=100)
    department3_en: Optional[str] = Field(None, max_length=100)
    
    # 聯絡資訊
    mobile_phone: Optional[str] = Field(None, max_length=50)
    company_phone1: Optional[str] = Field(None, max_length=50)
    company_phone2: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    line_id: Optional[str] = Field(None, max_length=50)
    
    # 地址資訊
    company_address1: Optional[str] = Field(None, max_length=200)
    company_address1_en: Optional[str] = Field(None, max_length=200)
    company_address2: Optional[str] = Field(None, max_length=200)
    company_address2_en: Optional[str] = Field(None, max_length=200)
    
    # 備註
    note1: Optional[str] = Field(None, max_length=500)
    note2: Optional[str] = Field(None, max_length=500)

class CardResponse(CardBase):
    """名片響應模型"""
    id: int
    front_image_url: Optional[str] = None
    back_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tags: Optional[List['TagResponse']] = []

    class Config:
        from_attributes = True


# Tag Schemas
class TagBase(BaseModel):
    """標籤基礎模型"""
    tag_name: str = Field(..., min_length=1, max_length=50, description="標籤名稱")
    tag_type: str = Field(default='user', description="標籤類型: user(用戶標籤) or system(系統標籤)")

    @field_validator('tag_type')
    @classmethod
    def validate_tag_type(cls, v):
        if v not in ['user', 'system']:
            raise ValueError('標籤類型必須是 user 或 system')
        return v


class TagCreate(TagBase):
    """創建標籤的請求模型"""
    pass


class TagResponse(TagBase):
    """標籤響應模型"""
    id: int
    card_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TagBatchCreate(BaseModel):
    """批量創建標籤的請求模型"""
    tags: List[str] = Field(..., min_length=1, max_length=10, description="標籤名稱列表(最多10個)")
    tag_type: str = Field(default='user', description="標籤類型")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError('一次最多添加10個標籤')
        for tag in v:
            if not tag or len(tag) > 50:
                raise ValueError('標籤名稱必須在1-50個字符之間')
        return v


class TagListResponse(BaseModel):
    """標籤列表響應模型"""
    tag_name: str
    tag_type: str
    count: int  # 使用該標籤的名片數量

    class Config:
        from_attributes = True