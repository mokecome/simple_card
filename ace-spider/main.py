"""
Ace-Spider 採購商機爬蟲系統
============================
從台灣政府採購網 (acebidx.com) 爬取招標公告，
用 GPT-4o 分析相關性，評估 Fit Score 和 ROI，匹配 CRM 名片池。

用法:
    python main.py                  # 完整流程（爬蟲 + 分析 + 報告）
    python main.py --crawl          # 只爬取標案
    python main.py --analyze        # 只分析已爬資料
    python main.py --report         # 只產生報告
    python main.py --all            # 完整流程
    python main.py --schedule       # 啟動定時排程
    python main.py --keywords AI,區塊鏈  # 指定關鍵字
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ace-spider")


def run_crawl(config_path: str | None = None, keywords: list[str] | None = None,
              run_id: str | None = None) -> str | None:
    """Run the crawler and return the output file path."""
    from crawlers.ace_crawler import run_ace_crawl
    return run_ace_crawl(config_path, keywords_override=keywords, run_id=run_id)


def run_analyze(config_path: str | None = None, crawl_file: str | None = None,
                run_id: str | None = None) -> str | None:
    """Run AI analysis on crawled data and return the output file path."""
    from crawlers.tagger import run_tagging
    from crawlers.scorer import run_scoring
    from crawlers.matcher import run_matching
    tagged = run_tagging(config_path, crawl_file, run_id=run_id)
    scored = run_scoring(config_path, tagged, run_id=run_id)
    return run_matching(config_path, scored, run_id=run_id)


def run_report(config_path: str | None = None, scored_file: str | None = None) -> None:
    """Generate terminal report and JSON output."""
    from crawlers.reporter import run_report as _run_report
    _run_report(config_path, scored_file)


def run_full_pipeline(config_path: str | None = None, keywords: list[str] | None = None) -> None:
    """Execute the full pipeline: crawl -> analyze -> report."""
    from crawlers.scheduler import execute_pipeline
    execute_pipeline(config_path, keywords)


def main():
    parser = argparse.ArgumentParser(
        description="Ace-Spider 採購商機爬蟲系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--crawl", action="store_true", help="只爬取標案")
    parser.add_argument("--analyze", action="store_true", help="只分析已爬資料")
    parser.add_argument("--report", action="store_true", help="只產生報告")
    parser.add_argument("--all", action="store_true", help="完整流程")
    parser.add_argument("--schedule", action="store_true", help="啟動定時排程")
    parser.add_argument("--once", action="store_true", help="配合 --schedule 跑一次就退出")
    parser.add_argument("--keywords", type=str, default=None, help="指定關鍵字（逗號分隔）")
    parser.add_argument("--config", type=str, default=None, help="配置文件路徑")
    args = parser.parse_args()

    keywords = args.keywords.split(",") if args.keywords else None

    # Schedule mode
    if args.schedule:
        from crawlers.scheduler import start_scheduler, execute_pipeline
        if args.once:
            log.info("單次完整流程模式")
            execute_pipeline(args.config, keywords)
        else:
            start_scheduler(args.config)
        return

    # Manual mode
    has_specific = args.crawl or args.analyze or args.report
    run_all = args.all or not has_specific

    if run_all:
        run_full_pipeline(args.config, keywords)
        return

    if args.crawl:
        log.info("=" * 60)
        log.info("爬取招標公告...")
        log.info("=" * 60)
        try:
            result = run_crawl(args.config, keywords)
            log.info(f"完成: {result}")
        except Exception as e:
            log.error(f"爬蟲失敗: {e}")
            sys.exit(1)

    if args.analyze:
        log.info("=" * 60)
        log.info("分析已爬資料...")
        log.info("=" * 60)
        try:
            result = run_analyze(args.config)
            log.info(f"完成: {result}")
        except Exception as e:
            log.error(f"分析失敗: {e}")
            sys.exit(1)

    if args.report:
        log.info("=" * 60)
        log.info("產生報告...")
        log.info("=" * 60)
        try:
            run_report(args.config)
        except Exception as e:
            log.error(f"報告失敗: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
