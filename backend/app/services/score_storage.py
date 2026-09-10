from __future__ import annotations

import json
import os
import tempfile
import threading
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional


class ScoreStorage:
    """Small local cache with atomic replacement and process-local locking."""

    DEFAULT_PATH = Path(__file__).resolve().parents[2] / "scores.json"

    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = Path(storage_file or self.DEFAULT_PATH)
        self._lock = threading.RLock()
        self.scores: Dict[str, Dict] = {}
        self.load_scores()

    def load_scores(self) -> None:
        with self._lock:
            if not self.storage_file.exists():
                self.scores = {}
                return
            try:
                content = json.loads(self.storage_file.read_text(encoding="utf-8"))
                self.scores = content if isinstance(content, dict) else {}
            except (OSError, json.JSONDecodeError):
                self.scores = {}

    def save_scores(self) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.storage_file.name}.",
                suffix=".tmp",
                dir=str(self.storage_file.parent),
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
                    json.dump(self.scores, temporary_file, indent=2, default=str)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())
                os.replace(temporary_name, self.storage_file)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)

    def get_score(self, record_id: int) -> Optional[Dict]:
        with self._lock:
            score = self.scores.get(str(record_id))
            return deepcopy(score) if score else None

    def store_scores(self, scores: List[Dict]) -> None:
        with self._lock:
            for score in scores:
                record_id = score.get("record_id")
                if record_id is not None:
                    self.scores[str(record_id)] = deepcopy(score)
            self.save_scores()

    def get_all_scores(self) -> Dict[str, Dict]:
        with self._lock:
            return deepcopy(self.scores)

    def clear_scores(self) -> None:
        with self._lock:
            self.scores = {}
            self.save_scores()
