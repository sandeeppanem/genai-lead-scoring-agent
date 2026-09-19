from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class InquiryService:
    """SQLite persistence for inquiries, decisions, semantic cache, and status history."""

    DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "leadflow.db"
    STATUSES = {"new", "in_review", "reviewed", "resolved"}

    def __init__(self, database_path: Optional[Path] = None) -> None:
        configured = os.getenv("LEADFLOW_DB_PATH", "").strip()
        self.database_path = Path(database_path or configured or self.DEFAULT_PATH)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @property
    def is_ready(self) -> bool:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def create_inquiry(
        self,
        *,
        record_id: int,
        opportunity_number: str,
        dataset_version: str,
        dataset_checksum: str,
        inquiry_text: str,
        semantic_decision: Dict[str, Any],
        workflow_decision: Dict[str, Any],
        ml_score: Dict[str, Any],
    ) -> int:
        now = self._now()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO inquiries (
                    record_id, opportunity_number, dataset_version, dataset_checksum,
                    inquiry_text, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'new', ?, ?)
                """,
                (
                    record_id,
                    opportunity_number,
                    dataset_version,
                    dataset_checksum,
                    inquiry_text.strip(),
                    now,
                    now,
                ),
            )
            inquiry_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO decisions (
                    inquiry_id, semantic_json, workflow_json, ml_score_json,
                    provider_mode, model, question_version, policy_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inquiry_id,
                    self._dump(semantic_decision),
                    self._dump(workflow_decision),
                    self._dump(ml_score),
                    semantic_decision["provider_mode"],
                    semantic_decision["model"],
                    semantic_decision["question_version"],
                    workflow_decision["policy_version"],
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO status_history (inquiry_id, previous_status, new_status, created_at)
                VALUES (?, NULL, 'new', ?)
                """,
                (inquiry_id, now),
            )
            connection.commit()
        return inquiry_id

    def get_inquiry_payload(self, inquiry_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT i.*, d.semantic_json, d.workflow_json, d.ml_score_json
                FROM inquiries i
                JOIN decisions d ON d.id = (
                    SELECT id FROM decisions
                    WHERE inquiry_id = i.id ORDER BY id DESC LIMIT 1
                )
                WHERE i.id = ?
                """,
                (inquiry_id,),
            ).fetchone()
        return self._row_payload(row) if row else None

    def list_inquiry_payloads(
        self,
        *,
        action: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        clauses: List[str] = []
        parameters: List[Any] = []
        if status:
            clauses.append("i.status = ?")
            parameters.append(status)
        if action:
            clauses.append("json_extract(d.workflow_json, '$.action') = ?")
            parameters.append(action)
        if priority:
            clauses.append("json_extract(d.workflow_json, '$.priority') = ?")
            parameters.append(priority)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT i.*, d.semantic_json, d.workflow_json, d.ml_score_json
                FROM inquiries i
                JOIN decisions d ON d.id = (
                    SELECT id FROM decisions
                    WHERE inquiry_id = i.id ORDER BY id DESC LIMIT 1
                )
                {where}
                ORDER BY
                    CASE json_extract(d.workflow_json, '$.priority')
                        WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2 ELSE 3 END,
                    i.created_at DESC
                LIMIT ?
                """,
                (*parameters, limit),
            ).fetchall()
            total = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*) AS count
                    FROM inquiries i
                    JOIN decisions d ON d.id = (
                        SELECT id FROM decisions
                        WHERE inquiry_id = i.id ORDER BY id DESC LIMIT 1
                    )
                    {where}
                    """,
                    parameters,
                ).fetchone()["count"]
            )
            count_rows = connection.execute(
                """
                SELECT json_extract(d.workflow_json, '$.action') AS action, COUNT(*) AS count
                FROM inquiries i
                JOIN decisions d ON d.id = (
                    SELECT id FROM decisions
                    WHERE inquiry_id = i.id ORDER BY id DESC LIMIT 1
                )
                GROUP BY action
                """
            ).fetchall()
        payloads = [self._row_payload(row) for row in rows]
        return {
            "items": payloads,
            "total": total,
            "counts": {str(row["action"]): int(row["count"]) for row in count_rows},
        }

    def update_status(self, inquiry_ids: List[int], new_status: str) -> List[int]:
        if new_status not in self.STATUSES:
            raise ValueError(f"Unsupported workflow status: {new_status}")
        if not inquiry_ids:
            return []
        placeholders = ",".join("?" for _ in inquiry_ids)
        now = self._now()
        with self._lock, self._connect() as connection:
            current = connection.execute(
                f"SELECT id, status FROM inquiries WHERE id IN ({placeholders})",
                inquiry_ids,
            ).fetchall()
            found = {int(row["id"]): str(row["status"]) for row in current}
            missing = sorted(set(inquiry_ids) - set(found))
            if missing:
                raise KeyError(f"Inquiry IDs not found: {missing}")
            for inquiry_id in inquiry_ids:
                connection.execute(
                    "UPDATE inquiries SET status = ?, updated_at = ? WHERE id = ?",
                    (new_status, now, inquiry_id),
                )
                connection.execute(
                    """
                    INSERT INTO status_history (
                        inquiry_id, previous_status, new_status, created_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (inquiry_id, found[inquiry_id], new_status, now),
                )
            connection.commit()
        return inquiry_ids

    def create_pending_status_change(
        self, inquiry_ids: List[int], new_status: str
    ) -> str:
        if new_status not in self.STATUSES:
            raise ValueError(f"Unsupported workflow status: {new_status}")
        existing = [
            self.get_inquiry_payload(inquiry_id) for inquiry_id in inquiry_ids
        ]
        if any(item is None for item in existing):
            missing = [
                inquiry_id
                for inquiry_id, item in zip(inquiry_ids, existing)
                if item is None
            ]
            raise KeyError(f"Inquiry IDs not found: {missing}")
        confirmation_id = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pending_changes (
                    confirmation_id, inquiry_ids_json, new_status, created_at, applied_at
                ) VALUES (?, ?, ?, ?, NULL)
                """,
                (confirmation_id, self._dump(inquiry_ids), new_status, self._now()),
            )
            connection.commit()
        return confirmation_id

    def apply_pending_status_change(self, confirmation_id: str) -> Dict[str, Any]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM pending_changes
                WHERE confirmation_id = ?
                """,
                (confirmation_id,),
            ).fetchone()
            if not row:
                raise KeyError("Confirmation not found")
            if row["applied_at"]:
                raise ValueError("This status change has already been applied")
            inquiry_ids = [int(value) for value in json.loads(row["inquiry_ids_json"])]
            new_status = str(row["new_status"])
            self.update_status(inquiry_ids, new_status)
            applied_at = self._now()
            connection.execute(
                "UPDATE pending_changes SET applied_at = ? WHERE confirmation_id = ?",
                (applied_at, confirmation_id),
            )
            connection.commit()
        return {
            "inquiry_ids": inquiry_ids,
            "status": new_status,
            "applied_at": applied_at,
        }

    def get_cached_semantic(self, cache_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT response_json FROM semantic_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        return json.loads(row["response_json"]) if row else None

    def store_cached_semantic(
        self,
        cache_key: str,
        content_hash: str,
        model: str,
        question_version: str,
        response: Dict[str, Any],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO semantic_cache (
                    cache_key, content_hash, model, question_version,
                    response_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    content_hash,
                    model,
                    question_version,
                    self._dump(response),
                    self._now(),
                ),
            )
            connection.commit()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS inquiries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL,
                    opportunity_number TEXT NOT NULL,
                    dataset_version TEXT NOT NULL,
                    dataset_checksum TEXT NOT NULL,
                    inquiry_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inquiry_id INTEGER NOT NULL REFERENCES inquiries(id),
                    semantic_json TEXT NOT NULL,
                    workflow_json TEXT NOT NULL,
                    ml_score_json TEXT NOT NULL,
                    provider_mode TEXT NOT NULL,
                    model TEXT NOT NULL,
                    question_version TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inquiry_id INTEGER NOT NULL REFERENCES inquiries(id),
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    cache_key TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    model TEXT NOT NULL,
                    question_version TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pending_changes (
                    confirmation_id TEXT PRIMARY KEY,
                    inquiry_ids_json TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    applied_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status);
                CREATE INDEX IF NOT EXISTS idx_decisions_inquiry ON decisions(inquiry_id, id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @staticmethod
    def _row_payload(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": int(row["id"]),
            "record_id": int(row["record_id"]),
            "opportunity_number": str(row["opportunity_number"]),
            "dataset_version": str(row["dataset_version"]),
            "dataset_checksum": str(row["dataset_checksum"]),
            "inquiry_text": str(row["inquiry_text"]),
            "status": str(row["status"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "semantic_decision": json.loads(row["semantic_json"]),
            "workflow_decision": json.loads(row["workflow_json"]),
            "ml_score": json.loads(row["ml_score_json"]),
        }

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
