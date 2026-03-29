"""Persistence for structured scale assessment results."""

from __future__ import annotations

import datetime
import json
from typing import Dict, List, Optional

from utils import db


def ensure_scale_tables():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scale_assessment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            scale_slug TEXT NOT NULL,
            scale_code TEXT NOT NULL,
            scale_name TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            total_score INTEGER NOT NULL,
            severity_key TEXT NOT NULL,
            severity_label TEXT NOT NULL,
            risk_flags_json TEXT DEFAULT '[]',
            highlights_json TEXT DEFAULT '[]',
            summary TEXT NOT NULL,
            interpretation TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            completed_at DATETIME NOT NULL,
            use_time INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    cursor.close()
    conn.close()


def create_scale_record(*, user_id, username, result, use_time=0):
    now = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    return db.insert(
        """
        INSERT INTO scale_assessment_records (
            user_id, username, scale_slug, scale_code, scale_name,
            answers_json, total_score, severity_key, severity_label,
            risk_flags_json, highlights_json,
            summary, interpretation, recommended_action,
            created_at, completed_at, use_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            user_id,
            username,
            result["scale_slug"],
            result["scale_code"],
            result["scale_name"],
            json.dumps(result["answers"], ensure_ascii=False),
            result["total_score"],
            result["severity_key"],
            result["severity_label"],
            json.dumps(result["risk_flags"], ensure_ascii=False),
            json.dumps(result["highlights"], ensure_ascii=False),
            result["summary"],
            result["interpretation"],
            result["recommended_action"],
            now,
            now,
            int(use_time or 0),
        ],
    )


def get_scale_record(record_id: int):
    record = db.fetch_one("SELECT * FROM scale_assessment_records WHERE id = ?", [record_id])
    return _deserialize_scale_record(record)


def list_scale_records(*, user_id: Optional[int] = None, username: Optional[str] = None, limit: int = 50):
    where_clauses = []
    params = []

    if user_id is not None:
        where_clauses.append("user_id = ?")
        params.append(user_id)
    elif username:
        where_clauses.append("username = ?")
        params.append(username)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    params.append(int(limit or 50))

    records = db.fetch_all(
        f"""
        SELECT *
        FROM scale_assessment_records
        {where_sql}
        ORDER BY completed_at DESC, id DESC
        LIMIT ?
        """,
        params,
    ) or []
    return [_deserialize_scale_record(record) for record in records]


def get_latest_scale_records(*, user_id: Optional[int] = None, username: Optional[str] = None) -> List[Dict]:
    latest_by_slug = {}
    records = list_scale_records(user_id=user_id, username=username, limit=100)
    for record in records:
        scale_slug = record.get("scale_slug")
        if scale_slug and scale_slug not in latest_by_slug:
            latest_by_slug[scale_slug] = record

    return sorted(
        latest_by_slug.values(),
        key=lambda row: row.get("completed_at") or row.get("created_at") or "",
        reverse=True,
    )


def _deserialize_scale_record(record: Optional[Dict]):
    if not record:
        return None

    normalized = dict(record)
    normalized["answers"] = json.loads(normalized.get("answers_json") or "{}")
    normalized["risk_flags"] = json.loads(normalized.get("risk_flags_json") or "[]")
    normalized["highlights"] = json.loads(normalized.get("highlights_json") or "[]")
    return normalized
