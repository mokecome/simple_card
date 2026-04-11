#!/usr/bin/env python3
"""
MCP Server for the Business Card OCR Management System (名片 OCR 管理系統).

Exposes 7 tools for AI agents to:
1. Scan business cards via OCR and save them to the database
2. Search and view the customer contact pool
3. View business opportunity tenders and their CRM contact matches

Transport: Streamable HTTP on port 8007 (configurable via MCP_PORT env var).
"""

from typing import Optional

from mcp.server.fastmcp import FastMCP

from config import MCP_PORT
from tools.contact_tools import (
    search_contacts_impl,
    get_contact_detail_impl,
    find_contacts_for_org_impl,
)
from tools.opportunity_tools import (
    get_opportunities_impl,
    get_opportunity_matches_impl,
)
from tools.ocr_tools import (
    scan_card_impl,
    save_card_impl,
)

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "cardocr_mcp",
    host="0.0.0.0",
    port=MCP_PORT,
    stateless_http=True,
    json_response=True,
)


# ---------------------------------------------------------------------------
# Contact tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="cardocr_search_contacts",
    annotations={
        "title": "搜尋客戶資料池",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cardocr_search_contacts(
    query: str,
    industry: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
) -> str:
    """搜尋客戶資料池。依姓名、公司、電話、Email 等模糊搜尋名片資料庫。

    回傳完整 25 欄位，但向用戶呈現時預設只顯示：
    姓名 (name_zh)、公司 (company_name_zh)、職稱 (position_zh)、手機 (mobile_phone)、Email (email)。
    用戶追問其他資訊時，直接從已回傳的資料中取用，不需重新查詢。

    Args:
        query: 搜尋關鍵字 — 姓名/公司/電話/Email (e.g. '國泰', '王大明', '0912')
        industry: 產業篩選 (e.g. '科技', '防詐', '旅宿')
        limit: 最大回傳筆數 (1-100, 預設 20)
        skip: 分頁偏移量 (預設 0)

    Returns:
        JSON: {total, count, has_more, next_skip, contacts: [{完整名片欄位}]}
    """
    return await search_contacts_impl(query, industry, limit, skip)


@mcp.tool(
    name="cardocr_get_contact_detail",
    annotations={
        "title": "查詢客戶詳細資訊",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cardocr_get_contact_detail(card_id: int) -> str:
    """查詢單一客戶的完整名片資訊（25 個欄位）。

    預設顯示：姓名、公司、職稱、手機、Email。
    用戶追問部門、地址、LINE、英文名等時直接從資料中取用。

    Args:
        card_id: 名片 ID (e.g. 42)

    Returns:
        JSON: {contact: {完整 25 欄位 + 產業分類 + 時間戳}}
    """
    return await get_contact_detail_impl(card_id)


@mcp.tool(
    name="cardocr_find_contacts_for_org",
    annotations={
        "title": "查詢某機關/公司的聯絡人",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cardocr_find_contacts_for_org(
    org_name: str,
    limit: int = 50,
) -> str:
    """查詢某機關或公司在名片池中的所有聯絡人。

    用於回答「我們認識這間公司/機關的誰？」之類的問題。
    預設顯示：姓名、公司、職稱、手機、Email。

    Args:
        org_name: 機關或公司名稱 (e.g. '內政部', '國泰金控')
        limit: 最大回傳筆數 (1-200, 預設 50)

    Returns:
        JSON: {org_name, total, contacts: [{完整名片欄位}]}
    """
    return await find_contacts_for_org_impl(org_name, limit)


# ---------------------------------------------------------------------------
# Opportunity tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="cardocr_get_opportunities",
    annotations={
        "title": "查看商機標案",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cardocr_get_opportunities(
    bu: Optional[str] = None,
    priority: Optional[str] = None,
    min_budget: Optional[int] = None,
    sort_by: str = "fit_score",
    limit: int = 20,
) -> str:
    """查看商機標案列表，可依 BU、優先級、預算篩選。

    預設顯示：標案名稱、機關、預算、評分 (fit_score)、截止日。
    追問再展開技術標籤、類別、URL 等詳情。

    Args:
        bu: 篩選 BU ('BU1' 或 'BU2')
        priority: 篩選優先級 ('high', 'medium', 'low')
        min_budget: 最低預算 NTD (e.g. 5000000 = NT$500萬)
        sort_by: 排序欄位 ('fit_score', 'budget', 'roi_score')
        limit: 最大回傳筆數 (1-100, 預設 20)

    Returns:
        JSON: {summary, filters_applied, total_matched, opportunities: [{標案完整資料}]}
    """
    return await get_opportunities_impl(bu, priority, min_budget, sort_by, limit)


@mcp.tool(
    name="cardocr_get_opportunity_matches",
    annotations={
        "title": "查詢標案匹配的人脈",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def cardocr_get_opportunity_matches(tender_id: str) -> str:
    """查詢某標案匹配到的客戶人脈。

    預設顯示：聯絡人姓名、機關、關係程度、匹配分數。
    追問再展開：匹配原因、備註。

    Args:
        tender_id: 標案 ID (e.g. 'T-12345678')

    Returns:
        JSON: {tender_id, tender_name, org_name, budget, matched_contacts: [{人脈資料}]}
    """
    return await get_opportunity_matches_impl(tender_id)


# ---------------------------------------------------------------------------
# OCR tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="cardocr_scan_card",
    annotations={
        "title": "掃描名片 OCR",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def cardocr_scan_card(
    image_base64: Optional[str] = None,
    image_url: Optional[str] = None,
    side: str = "front",
) -> str:
    """掃描名片圖片，執行 OCR 文字辨識並解析為 25 個結構化欄位。

    支援兩種圖片輸入（二選一）：
    - image_base64: 圖片的 base64 編碼（用戶直接傳照片時使用）
    - image_url: 圖片的網路 URL

    只做辨識不入庫。預設顯示：姓名、公司、職稱、手機、Email。
    用戶確認後再使用 cardocr_save_card 入庫。

    Args:
        image_base64: Base64 圖片資料 (JPEG/PNG)
        image_url: 圖片網址
        side: 名片面 ('front' 或 'back')

    Returns:
        JSON: {success, ocr_text, parsed_fields: {25 欄位}, message}
    """
    return await scan_card_impl(image_base64, image_url, side)


@mcp.tool(
    name="cardocr_save_card",
    annotations={
        "title": "名片入庫",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def cardocr_save_card(
    name_zh: str,
    name_en: Optional[str] = None,
    company_name_zh: Optional[str] = None,
    company_name_en: Optional[str] = None,
    position_zh: Optional[str] = None,
    position_en: Optional[str] = None,
    position1_zh: Optional[str] = None,
    position1_en: Optional[str] = None,
    department1_zh: Optional[str] = None,
    department1_en: Optional[str] = None,
    department2_zh: Optional[str] = None,
    department2_en: Optional[str] = None,
    department3_zh: Optional[str] = None,
    department3_en: Optional[str] = None,
    mobile_phone: Optional[str] = None,
    company_phone1: Optional[str] = None,
    company_phone2: Optional[str] = None,
    fax: Optional[str] = None,
    email: Optional[str] = None,
    line_id: Optional[str] = None,
    wechat_id: Optional[str] = None,
    company_address1_zh: Optional[str] = None,
    company_address1_en: Optional[str] = None,
    company_address2_zh: Optional[str] = None,
    company_address2_en: Optional[str] = None,
    note1: Optional[str] = None,
    note2: Optional[str] = None,
) -> str:
    """將名片資料存入資料庫。

    通常在 cardocr_scan_card 辨識完成、用戶確認資料正確後使用。
    只有 name_zh（中文姓名）為必填，其餘 26 個欄位皆為選填。

    Args:
        name_zh: 中文姓名（必填）
        其餘欄位皆為選填，詳見參數列表

    Returns:
        JSON: {success, card_id, name_zh, company_name_zh, message}
    """
    return await save_card_impl(
        name_zh=name_zh, name_en=name_en,
        company_name_zh=company_name_zh, company_name_en=company_name_en,
        position_zh=position_zh, position_en=position_en,
        position1_zh=position1_zh, position1_en=position1_en,
        department1_zh=department1_zh, department1_en=department1_en,
        department2_zh=department2_zh, department2_en=department2_en,
        department3_zh=department3_zh, department3_en=department3_en,
        mobile_phone=mobile_phone,
        company_phone1=company_phone1, company_phone2=company_phone2,
        fax=fax, email=email, line_id=line_id, wechat_id=wechat_id,
        company_address1_zh=company_address1_zh, company_address1_en=company_address1_en,
        company_address2_zh=company_address2_zh, company_address2_en=company_address2_en,
        note1=note1, note2=note2,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
