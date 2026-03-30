"""Report generator - terminal output and JSON summary."""

import io
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows cp950 encoding issues with Unicode characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from utils.config_loader import load_config

log = logging.getLogger(__name__)


def _format_budget(budget: int | None) -> str:
    """Format budget for display."""
    if not budget:
        return "N/A"
    if budget >= 100_000_000:
        return f"{budget / 100_000_000:.1f} 億"
    if budget >= 10_000:
        return f"{budget / 10_000:.0f} 萬"
    return f"{budget:,}"


def _truncate(text: str, max_len: int = 35) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 2] + ".."


def generate_terminal_report(data: dict) -> None:
    """Print a formatted report to the terminal."""
    tenders = data.get("tenders", [])
    keywords = data.get("keywords_used", [])

    # Separate passed and failed
    passed = [t for t in tenders if t.get("passes_filter")]
    failed = [t for t in tenders if not t.get("passes_filter")]

    # Sort passed by fit_score descending
    passed.sort(key=lambda t: t.get("fit_score", 0), reverse=True)

    # Summary stats
    total = len(tenders)
    total_passed = len(passed)

    bu1_count = sum(1 for t in passed if (t.get("tag_result") or {}).get("bu_assignment") in ("BU1", "both"))
    bu2_count = sum(1 for t in passed if (t.get("tag_result") or {}).get("bu_assignment") in ("BU2", "both"))

    high_count = sum(1 for t in passed if t.get("priority") == "high")
    medium_count = sum(1 for t in passed if t.get("priority") == "medium")
    low_count = sum(1 for t in passed if t.get("priority") == "low")

    avg_fit = sum(t.get("fit_score", 0) for t in passed) / max(total_passed, 1)
    total_budget = sum(t.get("budget", 0) or 0 for t in passed)

    # Print report
    print()
    print("=" * 90)
    print("  ACE-SPIDER  |  AI/Blockchain Procurement Opportunity Report")
    print("=" * 90)
    print(f"  Time: {data.get('crawl_time', 'N/A')[:19]}")
    print(f"  Keywords: {', '.join(keywords)}")
    print(f"  Total crawled: {total}  |  Passed filter: {total_passed}")
    print(f"  BU1 (Blockchain): {bu1_count}  |  BU2 (AI): {bu2_count}")
    print(f"  Priority: High={high_count} Medium={medium_count} Low={low_count}")
    print(f"  Avg Fit Score: {avg_fit:.1f}  |  Total Budget: {_format_budget(total_budget)}")
    print("-" * 90)

    if not passed:
        print("  (No opportunities passed the filter)")
        print("=" * 90)
        return

    # Table header
    print(f"  {'#':>3}  {'Tender Name':<36} {'Org':<16} {'Budget':>10} {'Fit':>5} {'ROI':>5} {'Pri':>4} {'BU':>4}")
    print("-" * 90)

    for i, t in enumerate(passed, 1):
        tag = t.get("tag_result") or {}
        name = _truncate(t.get("tender_name", "?"), 35)
        org = _truncate(t.get("org_name", "?"), 15)
        budget = _format_budget(t.get("budget"))
        fit = f"{t.get('fit_score', 0):.0f}"
        roi = f"{t.get('roi_score', 0):.1f}"
        pri = t.get("priority", "?")[:1].upper()
        bu = tag.get("bu_assignment", "?")

        print(f"  {i:>3}  {name:<36} {org:<16} {budget:>10} {fit:>5} {roi:>5} {pri:>4} {bu:>4}")

    print("-" * 90)

    # Top opportunities detail
    print()
    print("  TOP OPPORTUNITIES")
    print("-" * 90)

    for i, t in enumerate(passed[:5], 1):
        tag = t.get("tag_result") or {}
        contacts = t.get("matched_contacts", [])
        print(f"\n  [{i}] {t.get('tender_name', '?')}")
        print(f"      Org: {t.get('org_name', '?')}  |  Budget: {_format_budget(t.get('budget'))}")
        print(f"      Fit: {t.get('fit_score', 0):.0f}  |  ROI: {t.get('roi_score', 0):.1f}  |  Priority: {t.get('priority', '?')}")
        print(f"      BU: {tag.get('bu_assignment', '?')}  |  Tags: {', '.join(tag.get('tech_tags', []))}")
        print(f"      Summary: {tag.get('relevance_summary', 'N/A')}")
        if contacts:
            contact_strs = [f"{c['name']}({c.get('company', '')}, {c.get('position', '')})" for c in contacts[:2]]
            print(f"      Contacts: {', '.join(contact_strs)}")
        print(f"      URL: {t.get('url', 'N/A')}")

    print()
    print("=" * 90)


def generate_json_summary(data: dict, output_path: Path) -> str:
    """Generate a JSON summary file with only passed tenders."""
    tenders = data.get("tenders", [])
    passed = [t for t in tenders if t.get("passes_filter")]
    passed.sort(key=lambda t: t.get("fit_score", 0), reverse=True)

    summary = {
        "report_time": datetime.now().isoformat(),
        "crawl_time": data.get("crawl_time"),
        "keywords_used": data.get("keywords_used", []),
        "total_crawled": len(tenders),
        "total_passed": len(passed),
        "summary": {
            "by_bu": {
                "BU1": sum(1 for t in passed if (t.get("tag_result") or {}).get("bu_assignment") in ("BU1", "both")),
                "BU2": sum(1 for t in passed if (t.get("tag_result") or {}).get("bu_assignment") in ("BU2", "both")),
            },
            "by_priority": {
                "high": sum(1 for t in passed if t.get("priority") == "high"),
                "medium": sum(1 for t in passed if t.get("priority") == "medium"),
                "low": sum(1 for t in passed if t.get("priority") == "low"),
            },
            "avg_fit_score": round(sum(t.get("fit_score", 0) for t in passed) / max(len(passed), 1), 1),
            "total_budget": sum(t.get("budget", 0) or 0 for t in passed),
        },
        "opportunities": [
            {
                "tender_name": t.get("tender_name"),
                "org_name": t.get("org_name"),
                "budget": t.get("budget"),
                "category": t.get("category"),
                "fit_score": t.get("fit_score"),
                "roi_score": t.get("roi_score"),
                "priority": t.get("priority"),
                "bu_assignment": (t.get("tag_result") or {}).get("bu_assignment"),
                "tech_tags": (t.get("tag_result") or {}).get("tech_tags", []),
                "relevance_summary": (t.get("tag_result") or {}).get("relevance_summary"),
                "matched_contacts": t.get("matched_contacts", []),
                "url": t.get("url"),
                "deadline": t.get("deadline"),
            }
            for t in passed
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return str(output_path)


def run_report(config_path: str | None = None, matched_file: str | None = None) -> None:
    """Generate report from matched/scored data."""
    from utils.run_tracker import get_latest_file

    cfg = load_config(config_path)
    data_dir = cfg["output"]["data_dir"]

    # Find data file: explicit param > run tracker > fallback
    if not matched_file:
        # Try matched first, then scored, then tagged
        for stage in ["matched", "scored", "tagged"]:
            matched_file = get_latest_file(data_dir, stage)
            if matched_file:
                break
        if not matched_file:
            log.error("找不到分析資料")
            return

    log.info(f"讀取資料: {matched_file}")
    with open(matched_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Terminal report
    generate_terminal_report(data)

    # JSON summary
    reports_dir = Path(cfg["output"]["reports_dir"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = reports_dir / f"opportunity_report_{timestamp}.json"
    result = generate_json_summary(data, summary_path)
    log.info(f"JSON 報告已存: {result}")
