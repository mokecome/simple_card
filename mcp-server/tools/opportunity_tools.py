"""MCP tools for viewing business opportunity tenders and CRM matches."""

from __future__ import annotations

import json
from typing import Optional

from api_client import client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_budget(amount: int | float | None) -> str:
    """Convert budget number to human-friendly NTD string."""
    if not amount:
        return "未標示"
    if amount >= 1_0000_0000:
        return f"NT${amount / 1_0000_0000:.1f}億"
    if amount >= 1_0000:
        return f"NT${amount / 1_0000:.0f}萬"
    return f"NT${amount:,.0f}"


def _handle_error(e: Exception) -> str:
    if isinstance(e, Exception) and hasattr(e, "response"):
        resp = getattr(e, "response", None)
        if resp is not None:
            status = resp.status_code
            if status == 404:
                return "Error: 找不到該標案，請確認 tender_id 是否正確。"
            return f"Error: API 回傳 HTTP {status}"
    return f"Error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def get_opportunities_impl(
    bu: Optional[str] = None,
    priority: Optional[str] = None,
    min_budget: Optional[int] = None,
    sort_by: str = "fit_score",
    limit: int = 20,
) -> str:
    """查看商機標案列表，可依 BU、優先級、預算篩選。

    回傳完整標案資料 + 總覽統計。向用戶呈現時預設只顯示：
    標案名稱、機關、預算、評分 (fit_score)、截止日。
    追問再展開技術標籤、類別、URL 等詳情。
    """
    try:
        data = await client.get_no_auth("/spider/api/report")

        summary = data.get("summary", {})
        opportunities = data.get("opportunities", [])

        filtered = opportunities

        if bu:
            bu_key = bu.upper()
            filtered = [
                t for t in filtered
                if (t.get("tag_result") or {}).get("bu_assignment") in (bu_key, "both")
            ]

        if priority:
            filtered = [t for t in filtered if t.get("priority") == priority]

        if min_budget:
            filtered = [t for t in filtered if (t.get("budget") or 0) >= min_budget]

        sort_field = sort_by if sort_by in ("fit_score", "budget", "roi_score") else "fit_score"
        filtered.sort(key=lambda t: t.get(sort_field, 0) or 0, reverse=True)

        total_filtered = len(filtered)
        filtered = filtered[:limit]

        return json.dumps(
            {
                "summary": {
                    **summary,
                    "total_budget_display": _format_budget(summary.get("total_budget")),
                },
                "filters_applied": {
                    "bu": bu,
                    "priority": priority,
                    "min_budget": min_budget,
                    "sort_by": sort_by,
                },
                "total_matched": total_filtered,
                "count": len(filtered),
                "opportunities": filtered,
                "crawl_time": data.get("crawl_time"),
                "keywords_used": data.get("keywords_used", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


async def get_opportunity_matches_impl(tender_id: str) -> str:
    """查詢某標案匹配到的客戶人脈。

    回傳標案基本資訊及匹配到的 CRM 聯絡人列表。
    預設顯示：聯絡人姓名、機關、關係程度、匹配分數。
    追問再展開：匹配原因、備註。
    """
    try:
        data = await client.get_no_auth(f"/spider/api/tender/{tender_id}")

        matched = data.get("matched", {})
        scored = data.get("scored", {})
        crawl = data.get("crawl", {})

        tender_info = matched or scored or crawl
        contacts = tender_info.get("matched_contacts", [])

        result = {
            "tender_id": tender_id,
            "tender_name": tender_info.get("tender_name"),
            "org_name": tender_info.get("org_name"),
            "budget": tender_info.get("budget"),
            "budget_display": _format_budget(tender_info.get("budget")),
            "fit_score": tender_info.get("fit_score"),
            "roi_score": tender_info.get("roi_score"),
            "priority": tender_info.get("priority"),
            "bu_assignment": (tender_info.get("tag_result") or {}).get("bu_assignment"),
            "deadline": tender_info.get("deadline"),
            "url": tender_info.get("url"),
            "matched_contacts_count": len(contacts),
            "matched_contacts": contacts,
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return _handle_error(e)
