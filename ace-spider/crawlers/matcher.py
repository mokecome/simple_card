"""CRM contact matcher - match tenders to contacts from cards.db."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from utils.config_loader import load_config

log = logging.getLogger(__name__)

# cards.db industry_category → ace-spider industry_tags 映射
INDUSTRY_MAP = {
    "金融保險": ["金融", "保險", "金融/保險"],
    "製造業／工業應用": ["製造業", "工業監控"],
    "政府／公部門／非營利": ["政府專案"],
    "餐飲／零售／通路": ["飯店", "旅宿", "飯店/旅宿"],
    "醫療健康／生技": ["醫療"],
    "教育／學研": ["教育"],
    "交通運輸／物流": ["交通"],
    "資訊科技": ["AI", "區塊鏈", "資安", "SaaS", "CRM", "IoT", "數據分析"],
    "建築不動產": [],
    "廣告／媒體／行銷": [],
    "專業服務（顧問／法務／會計等）": [],
}

SENIOR_KEYWORDS = [
    "處長", "主管", "局長", "副總", "CTO", "CEO", "COO", "CFO",
    "總經理", "主任", "科長", "董事長", "執行長", "營運長",
    "協理", "經理", "創辦人", "理事長", "院長",
    "Director", "Chief", "VP", "President", "Founder", "Head", "Manager",
]


def _load_contacts_from_db(db_path: str) -> list[dict]:
    """Load contacts from cards.db SQLite database."""
    if not Path(db_path).exists():
        log.warning(f"cards.db 不存在: {db_path}")
        return []

    generic_names = {"有限公司", "股份有限公司", "公司", "集團", "基金會", "協會", "科技", "科學"}
    suffixes = ["股份有限公司", "有限公司", "公司", "集團", "基金會", "協會"]
    contacts = []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name_zh, name, company_name_zh, company_name,
                   position_zh, position, position1_zh, position1,
                   department1_zh, department1,
                   industry_category, email, mobile_phone, note1
            FROM cards
            WHERE (name_zh IS NOT NULL AND name_zh != '')
               OR (name IS NOT NULL AND name != '')
        """)

        for row in cur.fetchall():
            name = row["name_zh"] or row["name"] or ""
            company = row["company_name_zh"] or row["company_name"] or ""
            position = row["position_zh"] or row["position"] or ""
            position1 = row["position1_zh"] or row["position1"] or ""
            dept = row["department1_zh"] or row["department1"] or ""
            industry = row["industry_category"] or ""

            mapped_industries = frozenset(INDUSTRY_MAP.get(industry, []))

            org_keywords = []
            if company and len(company) >= 4 and company not in generic_names:
                org_keywords.append(company)
                short = company
                for suffix in suffixes:
                    short = short.replace(suffix, "")
                if short and short != company and len(short) >= 3 and short not in generic_names:
                    org_keywords.append(short)

            # Pre-build searchable text for tech keyword matching
            searchable = f"{company} {dept} {row['note1'] or ''}".lower()

            contacts.append({
                "id": f"card_{row['id']}",
                "card_id": row["id"],
                "name": name,
                "company": company,
                "position": position,
                "position1": position1,
                "department": dept,
                "industry_category": industry,
                "industries": mapped_industries,
                "org_keywords": org_keywords,
                "email": row["email"] or "",
                "mobile": row["mobile_phone"] or "",
                "notes": row["note1"] or "",
                "_searchable": searchable,
            })

    conn.close()
    return contacts


def match_tender_to_contacts(tender: dict, contacts: list[dict],
                             max_matches: int = 5) -> list[dict]:
    """Match a tender to relevant contacts from cards.db.

    Matching logic:
    1. Org name match (highest weight) - tender org contains contact's org keywords
    2. Industry match - tender industry tags overlap with contact's mapped industries
    3. Role relevance - senior/decision-maker roles score higher
    4. Tech keyword match - contact company/notes contain tender tech tags
    """
    tag_result = tender.get("tag_result") or {}
    tender_org = tender.get("org_name", "")
    tender_industries = frozenset(tag_result.get("industry_tags", []))
    tender_tags_lower = [tag.lower() for tag in tag_result.get("tech_tags", [])]
    tender_tags_orig = tag_result.get("tech_tags", [])
    bu = tag_result.get("bu_assignment", "none")

    matched = []

    for contact in contacts:
        score = 0
        reasons = []

        # 1. Org name match (50 pts)
        for kw in contact["org_keywords"]:
            if kw in tender_org:
                score += 50
                reasons.append(f"機關名稱匹配: {kw}")
                break

        # 2. Industry match (30 pts) — industries is already a frozenset
        industry_overlap = tender_industries & contact["industries"]
        if industry_overlap:
            score += 30
            reasons.append(f"產業匹配: {', '.join(industry_overlap)}")

        # 3. Role relevance (15 pts)
        role_text = f"{contact['position']} {contact['position1']}"
        if any(kw in role_text for kw in SENIOR_KEYWORDS):
            score += 15
            reasons.append(f"決策者: {contact['position']}")

        # 4. Tech keyword match in company/notes (20 pts)
        searchable = contact["_searchable"]
        tag_matches = [orig for orig, low in zip(tender_tags_orig, tender_tags_lower) if low in searchable]
        if tag_matches:
            score += 20
            reasons.append(f"技術關聯: {', '.join(tag_matches[:3])}")

        # 5. BU-specific industry boost (10 pts)
        if bu in ("BU1", "both") and contact["industry_category"] == "金融保險":
            score += 10
            reasons.append("BU1 金融產業加分")
        if bu in ("BU2", "both") and contact["industry_category"] == "資訊科技":
            score += 10
            reasons.append("BU2 資訊科技加分")

        if score >= 20:
            matched.append({
                "contact_id": contact["id"],
                "card_id": contact["card_id"],
                "name": contact["name"],
                "position": contact["position"],
                "company": contact["company"],
                "department": contact["department"],
                "industry_category": contact["industry_category"],
                "email": contact["email"],
                "mobile": contact["mobile"],
                "match_score": score,
                "reasons": reasons,
                "notes": contact["notes"],
            })

    matched.sort(key=lambda x: x["match_score"], reverse=True)
    return matched[:max_matches]


def run_matching(config_path: str | None = None, scored_file: str | None = None,
                 run_id: str | None = None) -> str | None:
    """Run CRM matching on scored data. Returns output file path."""
    from utils.run_tracker import get_latest_file, save_run_state, resolve_run_id

    cfg = load_config(config_path)
    crm_cfg = cfg.get("crm", {})
    db_path = crm_cfg.get("cards_db", "/data1/165/ocr_v2/manage_card/cards.db")
    max_matches = crm_cfg.get("max_matches_per_tender", 5)
    data_dir = cfg["output"]["data_dir"]

    if not scored_file:
        scored_file = get_latest_file(data_dir, "scored")
        if not scored_file:
            log.error("找不到評分資料")
            return None

    run_id = resolve_run_id(scored_file, run_id)

    log.info(f"讀取評分資料: {scored_file}")
    with open(scored_file, "r", encoding="utf-8") as f:
        scored_data = json.load(f)

    contacts = _load_contacts_from_db(db_path)
    log.info(f"從 cards.db 載入 {len(contacts)} 筆名片資料")

    tenders = scored_data.get("tenders", [])
    matched_count = 0

    for tender in tenders:
        matches = match_tender_to_contacts(tender, contacts, max_matches)
        tender["matched_contacts"] = matches
        if matches:
            matched_count += 1
            top = matches[0]
            log.info(f"  {tender.get('tender_name', '')[:30]}... -> {len(matches)} 位聯繫人 (最佳: {top['name']} @ {top['company']})")

    log.info(f"CRM 匹配完成: {matched_count} 筆標案有匹配的聯繫人")

    # Save matched results
    output_dir = Path(data_dir)
    output_file = output_dir / f"ace_matched_{run_id}.json"

    matched_data = {
        **scored_data,
        "match_time": datetime.now().isoformat(),
        "total_with_contacts": matched_count,
        "cards_db_total": len(contacts),
        "tenders": tenders,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(matched_data, f, ensure_ascii=False, indent=2)

    save_run_state(data_dir, run_id, "matched", str(output_file))
    log.info(f"匹配結果已存: {output_file} (run_id={run_id})")
    return str(output_file)
