"""GPT-4o tagging module for tender analysis."""

import json
import logging
from datetime import datetime
from pathlib import Path

from utils.config_loader import load_config
from utils.openai_client import OpenAIClient

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位採購商機分析助手，服務一家專精於以下兩個業務的科技公司：

BU1 - 區塊鏈金流追蹤：虛擬貨幣追蹤、錢包分析、AML反洗錢、交易監控、智能合約、詐騙防制
BU2 - AI應用客製：電腦視覺、NLP語言模型、推薦系統、預測分析、RPA自動化、IoT、智慧監控、CRM、SaaS、數據分析

請分析以下政府採購標案，回傳 JSON 格式：
{
  "tech_tags": ["從以下選擇: AI, 區塊鏈, 資安, 電腦視覺, NLP, 推薦系統, 預測分析, RPA, 金流追蹤, 錢包分析, AML, 交易監控, 智能合約, SaaS, CRM, IoT, 數據分析, 智慧監控"],
  "industry_tags": ["從以下選擇: 飯店/旅宿, 製造業, 工業監控, 環保/廢棄物, 金融/保險, 政府專案, 醫療, 教育, 交通, 國防"],
  "bu_assignment": "BU1 或 BU2 或 both 或 none",
  "relevance_summary": "1-2句中文說明此標案與公司業務的相關性",
  "estimated_effort_days": 整數(預估所需人天),
  "customization_level": "low(現有產品可用) 或 medium(需中度客製) 或 high(需從頭開發)"
}

規則：
- 如果標案明顯與 AI 或區塊鏈無關，tech_tags 設為空陣列，bu_assignment 設為 "none"
- estimated_effort_days 請保守估算
- 只回傳 JSON，不要其他文字"""


def _build_user_prompt(tender: dict) -> str:
    """Build the user prompt for a single tender."""
    budget_str = f"{tender.get('budget', '未公開'):,}" if tender.get('budget') else "未公開"
    return f"""標案名稱: {tender.get('tender_name', '')}
機關名稱: {tender.get('org_name', '')}
標的分類: {tender.get('category', '')}
預算金額: {budget_str} TWD
招標方式: {tender.get('bid_method', '')}
履約地點: {tender.get('location', '')}
履約期限: {tender.get('duration', '')}"""


def tag_tender(client: OpenAIClient, tender: dict) -> dict | None:
    """Tag a single tender using GPT-4o. Returns tag result dict or None."""
    user_prompt = _build_user_prompt(tender)
    result = client.call_json(SYSTEM_PROMPT, user_prompt)

    if not result:
        return None

    # Validate and normalize the response
    tag_result = {
        "tech_tags": result.get("tech_tags", []),
        "industry_tags": result.get("industry_tags", []),
        "bu_assignment": result.get("bu_assignment", "none"),
        "relevance_summary": result.get("relevance_summary", ""),
        "estimated_effort_days": result.get("estimated_effort_days", 0),
        "customization_level": result.get("customization_level", "high"),
    }

    # Ensure lists are lists
    if isinstance(tag_result["tech_tags"], str):
        tag_result["tech_tags"] = [tag_result["tech_tags"]]
    if isinstance(tag_result["industry_tags"], str):
        tag_result["industry_tags"] = [tag_result["industry_tags"]]

    return tag_result


def run_tagging(config_path: str | None = None, crawl_file: str | None = None,
                run_id: str | None = None) -> str | None:
    """Run GPT-4o tagging on crawled data. Returns output file path."""
    from utils.run_tracker import get_latest_file, save_run_state, resolve_run_id

    cfg = load_config(config_path)
    api_cfg = cfg["api"]["openai"]
    data_dir = cfg["output"]["data_dir"]

    if not crawl_file:
        crawl_file = get_latest_file(data_dir, "crawl")
        if not crawl_file:
            log.error("找不到爬蟲資料檔案")
            return None

    run_id = resolve_run_id(crawl_file, run_id)

    log.info(f"讀取爬蟲資料: {crawl_file}")
    with open(crawl_file, "r", encoding="utf-8") as f:
        crawl_data = json.load(f)

    tenders = crawl_data.get("tenders", [])
    if not tenders:
        log.warning("無標案資料可分析")
        return None

    # Initialize OpenAI client
    client = OpenAIClient(
        api_key=api_cfg["api_key"],
        model=api_cfg.get("model", "gpt-4o"),
        max_tokens=api_cfg.get("max_tokens", 1000),
        temperature=api_cfg.get("temperature", 0.2),
    )

    log.info(f"開始 AI 標籤分析: {len(tenders)} 筆標案")

    # Tag each tender
    for i, tender in enumerate(tenders, 1):
        if tender.get("parse_error"):
            log.warning(f"  [{i}/{len(tenders)}] 跳過解析失敗的標案: {tender.get('tender_name', 'unknown')}")
            tender["tag_result"] = None
            continue

        log.info(f"  [{i}/{len(tenders)}] 分析: {tender.get('tender_name', '')[:40]}...")
        tag_result = tag_tender(client, tender)
        tender["tag_result"] = tag_result

        if tag_result:
            bu = tag_result["bu_assignment"]
            tags = ", ".join(tag_result["tech_tags"][:3]) or "none"
            log.info(f"    -> BU={bu}, tags=[{tags}], effort={tag_result['estimated_effort_days']}d")

    log.info(f"AI 標籤分析完成 (總 tokens: {client.total_tokens_used})")

    # Save tagged results
    output_dir = Path(data_dir)
    output_file = output_dir / f"ace_tagged_{run_id}.json"

    tagged_data = {
        **crawl_data,
        "tag_time": datetime.now().isoformat(),
        "total_tokens_used": client.total_tokens_used,
        "tenders": tenders,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(tagged_data, f, ensure_ascii=False, indent=2)

    save_run_state(data_dir, run_id, "tagged", str(output_file))
    log.info(f"標籤結果已存: {output_file} (run_id={run_id})")
    return str(output_file)
