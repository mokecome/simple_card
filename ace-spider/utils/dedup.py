"""Track seen tender IDs to avoid re-processing."""

import json
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


class DedupTracker:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._seen: dict[str, str] = {}
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self._seen = json.load(f)
                log.info(f"已載入 {len(self._seen)} 筆已見標案")
            except (json.JSONDecodeError, IOError):
                self._seen = {}

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._seen, f, ensure_ascii=False, indent=2)

    def is_seen(self, tender_id: str) -> bool:
        return tender_id in self._seen

    def mark_seen(self, tender_id: str):
        if tender_id not in self._seen:
            self._seen[tender_id] = datetime.now().strftime("%Y-%m-%d")

    @property
    def count(self) -> int:
        return len(self._seen)
