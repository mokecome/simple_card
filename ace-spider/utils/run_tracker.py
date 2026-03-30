"""Run tracker - manages run_id to bind all pipeline stages together.

Instead of each stage independently generating a timestamp and using glob
to find "the latest" upstream file (which can pick files from a different
pipeline run), this module provides:

1. A single run_id shared across all stages in one pipeline execution
2. A latest_run.json file that records the current run's file paths
3. Lookup functions that find the correct upstream file by run_id
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

TRACKER_FILE = "latest_run.json"

_RUN_ID_RE = re.compile(r'ace_\w+_(\d{8}_\d{6})\.json')

PREFIX_MAP = {
    "crawl": "ace_crawl_",
    "tagged": "ace_tagged_",
    "scored": "ace_scored_",
    "matched": "ace_matched_",
}


def generate_run_id() -> str:
    """Generate a new run_id based on current timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def extract_run_id(file_path: str) -> str | None:
    """Extract run_id from an ace-spider output filename.

    Works for any stage: ace_crawl_YYYYMMDD_HHMMSS.json, ace_tagged_*, etc.
    Returns None if the filename doesn't match the expected pattern.
    """
    m = _RUN_ID_RE.search(file_path)
    return m.group(1) if m else None


def resolve_run_id(file_path: str, run_id: str | None) -> str:
    """Determine run_id: use explicit value, extract from filename, or generate new."""
    if run_id:
        return run_id
    return extract_run_id(file_path) or generate_run_id()


def save_run_state(data_dir: str, run_id: str, stage: str, file_path: str) -> None:
    """Record a stage's output file in the run tracker."""
    tracker_path = Path(data_dir) / TRACKER_FILE
    state = _load_state(tracker_path)

    state["run_id"] = run_id
    state["updated_at"] = datetime.now().isoformat()
    state.setdefault("stages", {})[stage] = file_path

    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    log.debug(f"Run tracker 更新: {stage} -> {file_path}")


def get_latest_file(data_dir: str, stage: str) -> str | None:
    """Get the file path for a stage from the latest run.

    Priority: run tracker record > glob fallback.
    """
    tracker_path = Path(data_dir) / TRACKER_FILE
    state = _load_state(tracker_path)

    file_path = state.get("stages", {}).get(stage)
    if file_path:
        run_id = state.get("run_id", "unknown")
        log.info(f"從 run tracker 讀取 {stage}: {file_path} (run_id={run_id})")
        return file_path

    # Fallback: glob for backward compatibility
    prefix = PREFIX_MAP.get(stage)
    if not prefix:
        return None

    files = sorted(Path(data_dir).glob(f"{prefix}*.json"), reverse=True)
    if files:
        log.warning(f"run tracker 無 {stage} 記錄，fallback 使用 glob: {files[0]}")
        return str(files[0])

    return None


def get_run_summary(data_dir: str) -> dict:
    """Get the current run state summary."""
    tracker_path = Path(data_dir) / TRACKER_FILE
    return _load_state(tracker_path)


def _load_state(tracker_path: Path) -> dict:
    """Load the tracker state file."""
    if tracker_path.exists():
        try:
            with open(tracker_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}
