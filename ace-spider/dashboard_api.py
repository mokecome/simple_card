"""FastAPI backend for Ace-Spider pipeline dashboard."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from utils.config_loader import load_config
from utils.run_tracker import get_run_summary

app = FastAPI(title="Ace-Spider Dashboard")
ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config.yaml"
_pipeline_lock = Lock()
_pipeline_process: subprocess.Popen | None = None
_pipeline_started_at: str | None = None


class ScheduleUpdateRequest(BaseModel):
    time: str


def _validate_time_text(time_text: str) -> str:
    """Validate and normalize HH:MM time text."""
    parts = time_text.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise HTTPException(400, "Time must be in HH:MM format")

    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise HTTPException(400, "Invalid time value")

    return f"{hour:02d}:{minute:02d}"


def _cron_to_time(cron_expr: str) -> str:
    """Convert cron expression to HH:MM."""
    parts = cron_expr.split()
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return "09:00"
    return f"{int(parts[1]):02d}:{int(parts[0]):02d}"


def _update_cron_time(cron_expr: str, time_text: str) -> str:
    """Replace hour/minute while preserving the remaining cron fields."""
    hour_text, minute_text = time_text.split(":")
    parts = cron_expr.split()
    defaults = ["0", "9", "*", "*", "1-5"]
    while len(parts) < 5:
        parts.append(defaults[len(parts)])
    parts[0] = str(int(minute_text))
    parts[1] = str(int(hour_text))
    return " ".join(parts[:5])


def _read_raw_config() -> dict:
    """Load config.yaml without env substitution."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_raw_config(config: dict) -> None:
    """Persist config.yaml."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)


def _pipeline_is_running() -> bool:
    """Check whether a run-now pipeline process is still active."""
    global _pipeline_process, _pipeline_started_at
    if _pipeline_process is None:
        return False
    if _pipeline_process.poll() is None:
        return True
    _pipeline_process = None
    _pipeline_started_at = None
    return False


def _get_control_state() -> dict:
    """Return dashboard control state for sidebar actions."""
    cfg = load_config()
    schedule_cfg = cfg.get("schedule", {})
    cron_expr = schedule_cfg.get("cron", "0 9 * * 1-5")
    running = _pipeline_is_running()
    return {
        "running": running,
        "pid": _pipeline_process.pid if running else None,
        "started_at": _pipeline_started_at if running else None,
        "schedule_mode": schedule_cfg.get("mode", "cron"),
        "schedule_cron": cron_expr,
        "schedule_time": _cron_to_time(cron_expr),
        "run_on_start": bool(schedule_cfg.get("run_on_start", True)),
    }


def _resolve_path(file_path: str) -> Path:
    """Resolve a possibly-relative path against ace-spider ROOT_DIR."""
    p = Path(file_path)
    if p.is_absolute():
        return p
    return ROOT_DIR / p


def _load_stage_data(stage: str) -> dict | None:
    """Load JSON data for a pipeline stage from the latest run."""
    cfg = load_config()
    data_dir = str(_resolve_path(cfg["output"]["data_dir"]))
    summary = get_run_summary(data_dir)
    file_path = summary.get("stages", {}).get(stage)
    if not file_path:
        return None
    resolved = _resolve_path(file_path)
    if not resolved.exists():
        return None
    with open(resolved, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/run-state")
def get_run_state():
    """Get current pipeline run state and summary stats."""
    cfg = load_config()
    data_dir = str(_resolve_path(cfg["output"]["data_dir"]))
    summary = get_run_summary(data_dir)

    stages_info = {}
    for stage in ["crawl", "tagged", "scored", "matched"]:
        file_path = summary.get("stages", {}).get(stage)
        resolved = _resolve_path(file_path) if file_path else None
        if resolved and resolved.exists():
            with open(resolved, "r", encoding="utf-8") as f:
                data = json.load(f)
            tenders = data.get("tenders", [])
            info = {"file": file_path, "count": len(tenders)}

            if stage == "tagged":
                info["tagged_count"] = sum(1 for t in tenders if t.get("tag_result"))
            elif stage == "scored":
                info["passed_count"] = sum(1 for t in tenders if t.get("passes_filter"))
                info["avg_fit"] = round(
                    sum(t.get("fit_score", 0) for t in tenders) / max(len(tenders), 1), 1
                )
            elif stage == "matched":
                info["with_contacts"] = sum(1 for t in tenders if t.get("matched_contacts"))

            stages_info[stage] = info
        else:
            stages_info[stage] = None

    return {
        "run_id": summary.get("run_id"),
        "updated_at": summary.get("updated_at"),
        "stages": stages_info,
    }


@app.get("/api/control")
def get_control():
    """Get sidebar control state."""
    return _get_control_state()


@app.post("/api/control/run-now")
def run_now():
    """Start the full pipeline in a background subprocess."""
    global _pipeline_process, _pipeline_started_at

    with _pipeline_lock:
        if _pipeline_is_running():
            return {
                "ok": False,
                "message": "Pipeline is already running",
                **_get_control_state(),
            }

        log_path = ROOT_DIR / "reports" / "pipeline_manual_run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "a", encoding="utf-8")
        _pipeline_process = subprocess.Popen(
            [sys.executable, "main.py", "--all"],
            cwd=ROOT_DIR,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log_file.close()  # fd is duplicated into child process
        _pipeline_started_at = datetime.now().isoformat()

    return {
        "ok": True,
        "message": "Pipeline started",
        **_get_control_state(),
    }


@app.post("/api/control/schedule")
def update_schedule(payload: ScheduleUpdateRequest):
    """Update the configured cron time used by main.py scheduler."""
    time_text = _validate_time_text(payload.time)
    config = _read_raw_config()
    schedule_cfg = config.setdefault("schedule", {})
    schedule_cfg["mode"] = "cron"
    schedule_cfg["cron"] = _update_cron_time(
        schedule_cfg.get("cron", "0 9 * * 1-5"),
        time_text,
    )
    _write_raw_config(config)
    return {
        "ok": True,
        "message": "Schedule updated",
        **_get_control_state(),
    }


@app.get("/api/stage/{stage}")
def get_stage_data(stage: str, page: int = 1, page_size: int = 50,
                   filter_passed: bool = False, search: str = ""):
    """Get paginated tender data for a pipeline stage."""
    if stage not in ("crawl", "tagged", "scored", "matched"):
        raise HTTPException(400, f"Unknown stage: {stage}")

    data = _load_stage_data(stage)
    if not data:
        raise HTTPException(404, f"No data for stage: {stage}")

    tenders = data.get("tenders", [])

    if filter_passed and stage in ("scored", "matched"):
        tenders = [t for t in tenders if t.get("passes_filter")]

    if search:
        q = search.lower()
        tenders = [
            t for t in tenders
            if q in (t.get("tender_name") or "").lower()
            or q in (t.get("org_name") or "").lower()
        ]

    total = len(tenders)
    start = (page - 1) * page_size
    page_tenders = tenders[start:start + page_size]

    return {
        "stage": stage,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "meta": {k: v for k, v in data.items() if k != "tenders"},
        "tenders": page_tenders,
    }


@app.get("/api/tender/{tender_id}")
def get_tender_detail(tender_id: str):
    """Get full detail for a single tender across all stages."""
    result = {}
    for stage in ["crawl", "tagged", "scored", "matched"]:
        data = _load_stage_data(stage)
        if not data:
            continue
        for t in data.get("tenders", []):
            if t.get("tender_id") == tender_id:
                result[stage] = t
                break
    if not result:
        raise HTTPException(404, f"Tender not found: {tender_id}")
    return result


@app.get("/api/report")
def get_report():
    """Get final report data (equivalent to Excel output)."""
    data = _load_stage_data("matched")
    if not data:
        raise HTTPException(404, "No matched data available")

    tenders = data.get("tenders", [])
    passed = [t for t in tenders if t.get("passes_filter")]
    passed.sort(key=lambda t: t.get("fit_score", 0), reverse=True)

    bu1 = [t for t in passed if (t.get("tag_result") or {}).get("bu_assignment") in ("BU1", "both")]
    bu2 = [t for t in passed if (t.get("tag_result") or {}).get("bu_assignment") in ("BU2", "both")]

    top_roi = sorted(passed, key=lambda t: t.get("roi_score", 0), reverse=True)[:10]

    return {
        "summary": {
            "total_crawled": len(tenders),
            "total_passed": len(passed),
            "bu1_count": len(bu1),
            "bu2_count": len(bu2),
            "high_count": sum(1 for t in passed if t.get("priority") == "high"),
            "medium_count": sum(1 for t in passed if t.get("priority") == "medium"),
            "low_count": sum(1 for t in passed if t.get("priority") == "low"),
            "avg_fit": round(sum(t.get("fit_score", 0) for t in passed) / max(len(passed), 1), 1),
            "total_budget": sum(t.get("budget", 0) or 0 for t in passed),
            "with_contacts": sum(1 for t in passed if t.get("matched_contacts")),
        },
        "opportunities": passed,
        "bu1_opportunities": bu1,
        "bu2_opportunities": bu2,
        "top_roi": top_roi,
        "crawl_time": data.get("crawl_time"),
        "keywords_used": data.get("keywords_used", []),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Serve the dashboard HTML."""
    html_path = ROOT_DIR / "dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
