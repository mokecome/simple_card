"""MCP tools for searching and viewing business card contacts."""

from __future__ import annotations

import json
from typing import Optional

from api_client import client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _handle_error(e: Exception) -> str:
    if isinstance(e, Exception) and hasattr(e, "response"):
        resp = getattr(e, "response", None)
        if resp is not None:
            status = resp.status_code
            if status == 404:
                return "Error: 找不到該名片，請確認 ID 是否正確。"
            if status == 401:
                return "Error: 認證失敗，請檢查帳密設定。"
            return f"Error: API 回傳 HTTP {status}"
    return f"Error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def search_contacts_impl(
    query: str,
    industry: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
) -> str:
    """搜尋客戶資料池。依姓名、公司、電話、Email 等模糊搜尋名片資料庫。

    回傳完整 25 欄位，但向用戶呈現時預設只顯示：
    姓名 (name_zh)、公司 (company_name_zh)、職稱 (position_zh)、手機 (mobile_phone)、Email (email)。
    用戶追問其他資訊時，直接從已回傳的資料中取用，不需重新查詢。
    """
    try:
        query_params: dict = {
            "search": query,
            "limit": limit,
            "skip": skip,
            "use_pagination": True,
        }
        if industry:
            query_params["industry"] = industry

        data = await client.get("/api/v1/cards", params=query_params)

        if not data.get("success"):
            return f"Error: {data.get('message', 'Unknown error')}"

        payload = data["data"]
        items = payload.get("items", [])
        total = payload.get("total", 0)

        return json.dumps(
            {
                "total": total,
                "count": len(items),
                "skip": skip,
                "has_more": total > skip + len(items),
                "next_skip": skip + len(items) if total > skip + len(items) else None,
                "contacts": items,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


async def get_contact_detail_impl(card_id: int) -> str:
    """查詢單一客戶的完整名片資訊（25 個欄位）。

    回傳完整資料。向用戶呈現時預設只顯示：姓名、公司、職稱、手機、Email。
    用戶追問部門、地址、LINE、英文名等時直接從資料中取用。
    """
    try:
        data = await client.get(f"/api/v1/cards/{card_id}")

        if not data.get("success"):
            return f"Error: {data.get('message', 'Unknown error')}"

        return json.dumps(
            {"contact": data["data"]},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


async def find_contacts_for_org_impl(
    org_name: str,
    limit: int = 50,
) -> str:
    """查詢某機關或公司在名片池中的所有聯絡人。

    用於回答「我們認識這間公司/機關的誰？」之類的問題。
    回傳完整欄位，預設顯示：姓名、公司、職稱、手機、Email。
    """
    try:
        data = await client.get(
            "/api/v1/cards",
            params={
                "company": org_name,
                "limit": limit,
                "skip": 0,
                "use_pagination": True,
            },
        )

        if not data.get("success"):
            return f"Error: {data.get('message', 'Unknown error')}"

        payload = data["data"]
        items = payload.get("items", [])
        total = payload.get("total", 0)

        return json.dumps(
            {
                "org_name": org_name,
                "total": total,
                "contacts": items,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)
