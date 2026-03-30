"""Crawl acebidx.com for tender announcements by keyword."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.config_loader import load_config
from utils.dedup import DedupTracker
from crawlers.parser import parse_listing_page, parse_detail_page, TenderSummary

log = logging.getLogger(__name__)


def _create_session(cfg: dict) -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=cfg.get("max_retries", 3),
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": cfg.get("user_agent", "ace-spider/1.0"),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    })
    return session


def crawl_keyword_listings(session: requests.Session, base_url: str, keyword: str,
                           max_pages: int, delay: float, timeout: int,
                           dedup: DedupTracker) -> list[TenderSummary]:
    """Crawl listing pages for a given keyword. Returns new (unseen) tenders."""
    all_tenders = []
    # URL encode the keyword for the path
    encoded_keyword = quote(keyword, safe='')
    url = f"{base_url}/by-keyword/{encoded_keyword}"

    for page in range(1, max_pages + 1):
        page_url = url if page == 1 else f"{url}/{page}"
        log.info(f"  [{keyword}] 頁面 {page}: {page_url}")

        try:
            r = session.get(page_url, timeout=timeout)
            r.raise_for_status()
            html = r.content.decode('utf-8')
        except Exception as e:
            log.error(f"  [{keyword}] 頁面 {page} 請求失敗: {e}")
            break

        tenders, next_page = parse_listing_page(html)

        if not tenders:
            log.info(f"  [{keyword}] 頁面 {page} 無標案，停止翻頁")
            break

        # Filter out already-seen tenders
        new_tenders = [t for t in tenders if not dedup.is_seen(t.tender_id)]
        all_tenders.extend(new_tenders)

        # Mark as seen
        for t in new_tenders:
            dedup.mark_seen(t.tender_id)

        log.info(f"  [{keyword}] 頁面 {page}: {len(tenders)} 筆, {len(new_tenders)} 筆新標案")

        if not next_page:
            break

        time.sleep(delay)

    return all_tenders


def crawl_detail_pages(session: requests.Session, detail_base_url: str,
                       tenders: list[TenderSummary], delay: float, timeout: int) -> list[dict]:
    """Crawl detail pages for each tender and extract structured data."""
    results = []
    total = len(tenders)

    for i, tender in enumerate(tenders, 1):
        detail_url = f"{detail_base_url}/{tender.tender_id}"
        log.info(f"  詳情 [{i}/{total}]: {tender.title[:40]}...")

        try:
            r = session.get(f"https://acebidx.com{detail_url}", timeout=timeout)
            r.raise_for_status()
            html = r.content.decode('utf-8')
        except Exception as e:
            log.warning(f"  詳情頁請求失敗 ({tender.tender_id}): {e}")
            # Still save what we have from the listing
            results.append({
                "tender_id": tender.tender_id,
                "tender_name": tender.title,
                "org_name": tender.org_name,
                "url": f"https://acebidx.com{tender.url}",
                "crawled_at": datetime.now().isoformat(),
                "parse_error": str(e),
            })
            time.sleep(delay)
            continue

        detail = parse_detail_page(html, tender.tender_id)
        detail.url = f"https://acebidx.com{tender.url}"
        detail.crawled_at = datetime.now().isoformat()

        # Use listing title as fallback
        if not detail.tender_name and tender.title:
            detail.tender_name = tender.title

        results.append(detail.to_dict())
        time.sleep(delay)

    return results


def run_ace_crawl(config_path: str | None = None, keywords_override: list[str] | None = None,
                   run_id: str | None = None) -> str | None:
    """Main crawl entry point. Returns the output file path."""
    from utils.run_tracker import generate_run_id, save_run_state

    cfg = load_config(config_path)
    crawler_cfg = cfg["crawler"]
    keywords_cfg = cfg["keywords"]
    output_cfg = cfg["output"]

    if not run_id:
        run_id = generate_run_id()

    # Determine keywords to crawl
    if keywords_override:
        keywords = keywords_override
    else:
        keywords = keywords_cfg.get("primary", [])

    if not keywords:
        log.error("未設定關鍵字")
        return None

    log.info(f"開始爬取 {len(keywords)} 個關鍵字: {', '.join(keywords)}")

    # Initialize
    session = _create_session(crawler_cfg)
    dedup = DedupTracker(output_cfg["dedup_file"])
    base_url = crawler_cfg["base_url"]
    detail_base_url = crawler_cfg.get("detail_base_url", "/zh-TW/docs/tender/id")
    delay = crawler_cfg.get("request_delay_sec", 2.5)
    timeout = crawler_cfg.get("request_timeout_sec", 30)
    max_pages = crawler_cfg.get("max_pages_per_keyword", 3)

    # Phase 1: Crawl listings
    all_new_tenders = []
    for keyword in keywords:
        log.info(f"關鍵字: [{keyword}]")
        new_tenders = crawl_keyword_listings(
            session, base_url, keyword, max_pages, delay, timeout, dedup
        )
        all_new_tenders.extend(new_tenders)
        log.info(f"  [{keyword}] 共 {len(new_tenders)} 筆新標案")

    if not all_new_tenders:
        log.info("本次無新標案")
        dedup.save()
        return None

    # Deduplicate across keywords (same tender may appear in multiple keyword searches)
    seen_ids = set()
    unique_tenders = []
    for t in all_new_tenders:
        if t.tender_id not in seen_ids:
            seen_ids.add(t.tender_id)
            unique_tenders.append(t)

    log.info(f"去重後共 {len(unique_tenders)} 筆新標案，開始爬取詳情頁...")

    # Phase 2: Crawl detail pages
    results = crawl_detail_pages(session, detail_base_url, unique_tenders, delay, timeout)

    # Save results
    output_dir = Path(output_cfg["data_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"ace_crawl_{run_id}.json"

    output_data = {
        "crawl_time": datetime.now().isoformat(),
        "keywords_used": keywords,
        "total_found": len(unique_tenders),
        "tenders": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    dedup.save()
    save_run_state(str(output_dir), run_id, "crawl", str(output_file))
    log.info(f"爬取完成: {len(results)} 筆標案 -> {output_file} (run_id={run_id})")
    return str(output_file)
