"""MCP tools for business card OCR scanning and saving."""

from __future__ import annotations

import base64
import json
from typing import Optional

import httpx

from api_client import client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _handle_error(e: Exception) -> str:
    if isinstance(e, Exception) and hasattr(e, "response"):
        resp = getattr(e, "response", None)
        if resp is not None:
            return f"Error: API 回傳 HTTP {resp.status_code}"
    return f"Error: {type(e).__name__}: {e}"


async def _download_image(url: str) -> bytes:
    """Download an image from a URL and return raw bytes."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        return resp.content


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def scan_card_impl(
    image_base64: Optional[str] = None,
    image_url: Optional[str] = None,
    side: str = "front",
) -> str:
    """掃描名片圖片，執行 OCR 文字辨識並解析為 25 個結構化欄位。

    支援兩種圖片輸入方式（二選一）：
    - image_base64: 圖片的 base64 編碼（用戶直接傳照片時使用）
    - image_url: 圖片的網路 URL

    此工具只做辨識，不會存入資料庫。辨識結果回傳後，
    預設顯示：姓名、公司、職稱、手機、Email。
    用戶確認後再使用 cardocr_save_card 入庫。
    """
    try:
        if image_base64:
            image_bytes = base64.b64decode(image_base64)
            filename = "card.jpg"
        elif image_url:
            image_bytes = await _download_image(image_url)
            ext = image_url.rsplit(".", 1)[-1].lower() if "." in image_url else "jpg"
            if ext not in ("jpg", "jpeg", "png", "webp"):
                ext = "jpg"
            filename = f"card.{ext}"
        else:
            return "Error: 請提供 image_base64 或 image_url 其中一個。"

        # Step 1: OCR text extraction
        ocr_result = await client.post_file("/api/v1/ocr/image", image_bytes, filename)

        if not ocr_result.get("success"):
            return f"Error: OCR 辨識失敗 — {ocr_result.get('message', 'Unknown')}"

        ocr_text = ocr_result["data"]["text"]

        if not ocr_text or len(ocr_text.strip()) < 5:
            return json.dumps(
                {"success": False, "message": "OCR 辨識結果文字過少，可能圖片不清晰或非名片。", "ocr_text": ocr_text},
                ensure_ascii=False,
                indent=2,
            )

        # Step 2: Parse into structured fields
        parse_result = await client.post(
            "/api/v1/ocr/parse-fields",
            json={"ocr_text": ocr_text, "side": side},
        )

        if not parse_result.get("success"):
            return json.dumps(
                {"success": True, "ocr_text": ocr_text, "parsed_fields": None, "message": "OCR 成功但欄位解析失敗，請手動處理。"},
                ensure_ascii=False,
                indent=2,
            )

        parsed_fields = parse_result["data"].get("parsed_fields", {})

        return json.dumps(
            {
                "success": True,
                "ocr_text": ocr_text,
                "parsed_fields": parsed_fields,
                "side": side,
                "message": "辨識完成。請確認資料是否正確，確認後使用 cardocr_save_card 存入資料庫。",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


async def save_card_impl(
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
    用戶可能會修改部分欄位後再入庫。只有 name_zh（中文姓名）為必填。
    """
    try:
        # Collect all non-None fields into form data
        all_fields = {
            "name_zh": name_zh,
            "name_en": name_en,
            "company_name_zh": company_name_zh,
            "company_name_en": company_name_en,
            "position_zh": position_zh,
            "position_en": position_en,
            "position1_zh": position1_zh,
            "position1_en": position1_en,
            "department1_zh": department1_zh,
            "department1_en": department1_en,
            "department2_zh": department2_zh,
            "department2_en": department2_en,
            "department3_zh": department3_zh,
            "department3_en": department3_en,
            "mobile_phone": mobile_phone,
            "company_phone1": company_phone1,
            "company_phone2": company_phone2,
            "fax": fax,
            "email": email,
            "line_id": line_id,
            "wechat_id": wechat_id,
            "company_address1_zh": company_address1_zh,
            "company_address1_en": company_address1_en,
            "company_address2_zh": company_address2_zh,
            "company_address2_en": company_address2_en,
            "note1": note1,
            "note2": note2,
        }
        form_data = {k: v for k, v in all_fields.items() if v is not None}

        result = await client.post_form("/api/v1/cards", data=form_data)

        if not result.get("success"):
            return f"Error: 入庫失敗 — {result.get('message', 'Unknown')}"

        card = result["data"]
        return json.dumps(
            {
                "success": True,
                "card_id": card.get("id"),
                "name_zh": card.get("name_zh"),
                "company_name_zh": card.get("company_name_zh"),
                "message": f"名片已成功存入資料庫 (ID: {card.get('id')})",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)
