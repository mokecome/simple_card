"""APScheduler-based task scheduler for ace-spider."""

from __future__ import annotations

import logging
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from utils.config_loader import load_config

log = logging.getLogger(__name__)


def execute_pipeline(config_path: str | None = None, keywords: list[str] | None = None):
    """Execute the full crawl -> tag -> score -> match -> report pipeline.

    All stages share a single run_id to ensure file consistency.
    """
    from utils.run_tracker import generate_run_id

    run_start = datetime.now()
    run_id = generate_run_id()
    log.info("=" * 60)
    log.info(f"排程任務啟動 - {run_start.strftime('%Y-%m-%d %H:%M:%S')} (run_id={run_id})")
    log.info("=" * 60)

    # Step 1: Crawl
    try:
        from crawlers.ace_crawler import run_ace_crawl
        log.info("[1/4] 爬取招標公告...")
        crawl_file = run_ace_crawl(config_path, keywords_override=keywords, run_id=run_id)
        if not crawl_file:
            log.info("無新標案，結束本次排程")
            return
    except Exception as e:
        log.error(f"爬蟲失敗: {e}")
        return

    # Step 2: Tag
    try:
        from crawlers.tagger import run_tagging
        log.info("[2/4] AI 標籤分析...")
        tagged_file = run_tagging(config_path, crawl_file, run_id=run_id)
    except Exception as e:
        log.error(f"標籤分析失敗: {e}")
        return

    # Step 3: Score + Match
    try:
        from crawlers.scorer import run_scoring
        from crawlers.matcher import run_matching
        log.info("[3/4] 評分 + CRM 匹配...")
        scored_file = run_scoring(config_path, tagged_file, run_id=run_id)
        matched_file = run_matching(config_path, scored_file, run_id=run_id)
    except Exception as e:
        log.error(f"評分匹配失敗: {e}")
        return

    # Step 4: Report
    try:
        from crawlers.reporter import run_report
        log.info("[4/4] 產生報告...")
        run_report(config_path, matched_file)
    except Exception as e:
        log.error(f"報告產生失敗: {e}")
        return

    duration = (datetime.now() - run_start).total_seconds()
    log.info(f"全流程完成！耗時 {duration:.0f}s (run_id={run_id})")

    log.info("=" * 60)


def start_scheduler(config_path: str | None = None, override_interval: int | None = None):
    """Start the blocking scheduler."""
    cfg = load_config(config_path)
    schedule_cfg = cfg.get("schedule", {})
    mode = schedule_cfg.get("mode", "cron")

    scheduler = BlockingScheduler()

    if override_interval:
        trigger = IntervalTrigger(hours=override_interval)
        log.info(f"排程模式: 每 {override_interval} 小時執行一次")
    elif mode == "interval":
        hours = schedule_cfg.get("interval_hours", 24)
        trigger = IntervalTrigger(hours=hours)
        log.info(f"排程模式: 每 {hours} 小時執行一次")
    elif mode == "cron":
        cron_expr = schedule_cfg.get("cron", "0 9 * * 1-5")
        parts = cron_expr.split()
        trigger = CronTrigger(
            minute=parts[0] if len(parts) > 0 else "0",
            hour=parts[1] if len(parts) > 1 else "9",
            day=parts[2] if len(parts) > 2 else "*",
            month=parts[3] if len(parts) > 3 else "*",
            day_of_week=parts[4] if len(parts) > 4 else "*",
        )
        log.info(f"排程模式: cron ({cron_expr})")
    else:
        log.error(f"未知排程模式: {mode}")
        return

    scheduler.add_job(
        execute_pipeline,
        trigger=trigger,
        kwargs={"config_path": config_path},
        id="ace_spider_pipeline",
        name="Ace-Spider Pipeline",
        max_instances=1,
        coalesce=True,
    )

    # Run immediately on start if configured
    if schedule_cfg.get("run_on_start", True):
        log.info("首次立即執行...")
        execute_pipeline(config_path)

    # Graceful shutdown
    def shutdown(signum, frame):
        log.info("收到停止信號，正在關閉排程器...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    log.info("排程器已啟動，按 Ctrl+C 停止")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("排程器已停止")
