"""Fit Score and ROI calculator for tagged tenders."""

import json
import logging
from datetime import datetime
from pathlib import Path

from utils.config_loader import load_config

log = logging.getLogger(__name__)


def _correct_bu(tag_result: dict, bu_mapping: dict) -> str:
    """Correct bu_assignment based on tech_tags matching bu_mapping keywords.

    GPT sometimes swaps BU1/BU2. This uses config's bu_mapping as ground truth.
    """
    tech_tags = set(t.lower() for t in tag_result.get("tech_tags", []))
    if not tech_tags:
        return tag_result.get("bu_assignment", "none")

    scores = {}
    for bu_id, bu_data in bu_mapping.items():
        bu_keywords = set(kw.lower() for kw in bu_data.get("keywords", []))
        scores[bu_id] = len(tech_tags & bu_keywords)

    bu1_score = scores.get("BU1", 0)
    bu2_score = scores.get("BU2", 0)

    if bu1_score > 0 and bu2_score > 0:
        return "both"
    if bu1_score > 0:
        return "BU1"
    if bu2_score > 0:
        return "BU2"
    return "none"


def calculate_fit_score(tender: dict, tag_result: dict, cfg: dict) -> dict:
    """Calculate Fit Score (0-100) based on weighted dimensions.

    Returns dict with fit_score and breakdown.
    """
    weights = cfg["scoring"]["fit_weights"]
    bu_mapping = cfg["bu_mapping"]
    budget_range = cfg["scoring"]["budget_sweet_spot"]

    tech_tags = tag_result.get("tech_tags", [])
    industry_tags = tag_result.get("industry_tags", [])
    bu = tag_result.get("bu_assignment", "none")
    custom_level = tag_result.get("customization_level", "high")

    # 1. Tech match (0-100) - does it match our capabilities?
    all_bu_keywords = set()
    for bu_data in bu_mapping.values():
        all_bu_keywords.update(kw.lower() for kw in bu_data.get("keywords", []))

    if tech_tags:
        matched = sum(1 for tag in tech_tags if tag.lower() in all_bu_keywords or tag in ("AI", "區塊鏈"))
        tech_score = min(100, (matched / max(len(tech_tags), 1)) * 100)
    else:
        tech_score = 0

    # Boost if BU assignment is specific
    if bu in ("BU1", "BU2", "both"):
        tech_score = max(tech_score, 60)

    # 2. Industry match (0-100)
    known_industries = {"飯店", "旅宿", "製造業", "工業監控", "環保", "廢棄物", "金融", "保險", "政府專案"}
    if industry_tags:
        matched = sum(1 for tag in industry_tags if any(ki in tag for ki in known_industries))
        industry_score = min(100, (matched / max(len(industry_tags), 1)) * 100)
    else:
        industry_score = 20  # Default neutral score

    # 3. Solution maturity (0-100) - do we have a ready product?
    high_maturity_tags = {"AI", "智慧監控", "數據分析", "金流追蹤", "AML", "交易監控", "區塊鏈"}
    if tech_tags:
        mature_count = sum(1 for tag in tech_tags if tag in high_maturity_tags)
        maturity_score = min(100, (mature_count / max(len(tech_tags), 1)) * 100)
    else:
        maturity_score = 0

    # 4. Customization penalty (0-100, higher = more penalty)
    custom_penalties = {"low": 0, "medium": 40, "high": 80}
    custom_penalty = custom_penalties.get(custom_level, 50)

    # 5. Budget score (0-100)
    budget = tender.get("budget")
    if budget and budget > 0:
        min_budget = budget_range["min"]
        max_budget = budget_range["max"]
        if min_budget <= budget <= max_budget:
            budget_score = 100
        elif budget < min_budget:
            budget_score = max(0, (budget / min_budget) * 60)
        else:
            budget_score = max(40, 100 - ((budget - max_budget) / max_budget) * 30)
    else:
        budget_score = 30  # Unknown budget = neutral-low

    # Weighted total
    fit_score = (
        tech_score * weights["tech_match"]
        + industry_score * weights["industry_match"]
        + maturity_score * weights["solution_maturity"]
        - custom_penalty * weights["customization_penalty"]
        + budget_score * weights["budget_score"]
    )
    fit_score = max(0, min(100, fit_score))

    return {
        "fit_score": round(fit_score, 1),
        "fit_breakdown": {
            "tech_match": round(tech_score, 1),
            "industry_match": round(industry_score, 1),
            "solution_maturity": round(maturity_score, 1),
            "customization_penalty": round(custom_penalty, 1),
            "budget_score": round(budget_score, 1),
        },
    }


def calculate_roi(tender: dict, tag_result: dict, cfg: dict) -> dict:
    """Calculate ROI estimation.

    Returns dict with roi_score, estimated_cost, estimated_revenue, priority.
    """
    roi_cfg = cfg["scoring"]["roi"]
    daily_rate = roi_cfg["daily_rate"]
    win_rate = roi_cfg["win_rate"]
    margin = roi_cfg["margin"]

    effort_days = tag_result.get("estimated_effort_days", 0)
    budget = tender.get("budget", 0) or 0

    if effort_days <= 0 or budget <= 0:
        return {
            "roi_score": 0,
            "estimated_cost": 0,
            "estimated_revenue": 0,
            "priority": "low",
        }

    estimated_cost = effort_days * daily_rate
    estimated_revenue = budget * win_rate * margin
    roi_score = estimated_revenue / estimated_cost if estimated_cost > 0 else 0

    if roi_score >= 2.0:
        priority = "high"
    elif roi_score >= 1.5:
        priority = "medium"
    else:
        priority = "low"

    return {
        "roi_score": round(roi_score, 2),
        "estimated_cost": int(estimated_cost),
        "estimated_revenue": int(estimated_revenue),
        "priority": priority,
    }


def apply_filters(tender: dict, cfg: dict) -> bool:
    """Check if a scored tender passes the filter thresholds."""
    filters = cfg["filters"]
    budget = tender.get("budget", 0) or 0
    fit_score = tender.get("fit_score", 0)
    roi_score = tender.get("roi_score", 0)

    # Must have minimum budget
    if budget < filters["min_budget"]:
        return False

    # Must pass fit score OR roi threshold
    passes_fit = fit_score >= filters["min_fit_score"]
    passes_roi = roi_score >= filters["min_roi"]

    return passes_fit or passes_roi


def run_scoring(config_path: str | None = None, tagged_file: str | None = None,
                run_id: str | None = None) -> str | None:
    """Run Fit Score + ROI scoring on tagged data. Returns output file path."""
    from utils.run_tracker import get_latest_file, save_run_state, resolve_run_id

    cfg = load_config(config_path)
    data_dir = cfg["output"]["data_dir"]

    if not tagged_file:
        tagged_file = get_latest_file(data_dir, "tagged")
        if not tagged_file:
            log.error("找不到標籤分析資料")
            return None

    run_id = resolve_run_id(tagged_file, run_id)

    log.info(f"讀取標籤資料: {tagged_file}")
    with open(tagged_file, "r", encoding="utf-8") as f:
        tagged_data = json.load(f)

    tenders = tagged_data.get("tenders", [])
    scored_count = 0
    passed_count = 0

    bu_mapping = cfg["bu_mapping"]

    for tender in tenders:
        tag_result = tender.get("tag_result")
        if not tag_result:
            tender["fit_score"] = 0
            tender["fit_breakdown"] = {}
            tender["roi_score"] = 0
            tender["estimated_cost"] = 0
            tender["estimated_revenue"] = 0
            tender["priority"] = "low"
            tender["passes_filter"] = False
            continue

        # Correct bu_assignment based on tech_tags and bu_mapping
        tag_result["bu_assignment"] = _correct_bu(tag_result, bu_mapping)

        fit = calculate_fit_score(tender, tag_result, cfg)
        roi = calculate_roi(tender, tag_result, cfg)

        tender.update(fit)
        tender.update(roi)

        # Apply filters
        tender["passes_filter"] = apply_filters(tender, cfg)

        scored_count += 1
        if tender["passes_filter"]:
            passed_count += 1

    log.info(f"評分完成: {scored_count} 筆已評分, {passed_count} 筆通過篩選")

    # Save scored results
    output_dir = Path(data_dir)
    output_file = output_dir / f"ace_scored_{run_id}.json"

    scored_data = {
        **tagged_data,
        "score_time": datetime.now().isoformat(),
        "total_scored": scored_count,
        "total_passed": passed_count,
        "tenders": tenders,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scored_data, f, ensure_ascii=False, indent=2)

    save_run_state(data_dir, run_id, "scored", str(output_file))
    log.info(f"評分結果已存: {output_file} (run_id={run_id})")
    return str(output_file)
