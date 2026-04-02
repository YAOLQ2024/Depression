"""Persistence for structured scale assessment results and drafts."""

from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Optional

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
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scale_assessment_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            scale_slug TEXT NOT NULL,
            flow_session_id TEXT,
            answers_json TEXT NOT NULL DEFAULT '{}',
            answered_count INTEGER DEFAULT 0,
            current_item_index INTEGER DEFAULT 0,
            started_at INTEGER,
            saved_use_time INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            completed_at DATETIME
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


def get_scale_draft(*, user_id: int, scale_slug: str, flow_session_id: Optional[str] = None):
    if not scale_slug:
        return None

    params: List[Any] = [user_id, str(scale_slug).strip().lower(), "draft"]
    flow_session_id = str(flow_session_id).strip() if flow_session_id not in (None, "") else None
    if flow_session_id:
        sql = """
            SELECT *
            FROM scale_assessment_drafts
            WHERE user_id = ? AND scale_slug = ? AND status = ? AND flow_session_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
        """
        params.append(flow_session_id)
    else:
        sql = """
            SELECT *
            FROM scale_assessment_drafts
            WHERE user_id = ? AND scale_slug = ? AND status = ?
              AND (flow_session_id IS NULL OR flow_session_id = '')
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
        """

    record = db.fetch_one(sql, params)
    return _deserialize_scale_draft(record)


def upsert_scale_draft(
    *,
    user_id: int,
    username: str,
    scale_slug: str,
    answers: Dict[str, Any],
    answered_count: int,
    current_item_index: int,
    started_at: Optional[int],
    saved_use_time: int,
    flow_session_id: Optional[str] = None,
):
    now = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    normalized_scale_slug = str(scale_slug).strip().lower()
    normalized_flow_session_id = (
        str(flow_session_id).strip() if flow_session_id not in (None, "") else None
    )
    existing = get_scale_draft(
        user_id=user_id,
        scale_slug=normalized_scale_slug,
        flow_session_id=normalized_flow_session_id,
    )

    if existing:
        db.update(
            """
            UPDATE scale_assessment_drafts
            SET answers_json = ?, answered_count = ?, current_item_index = ?,
                started_at = ?, saved_use_time = ?, updated_at = ?, status = 'draft'
            WHERE id = ?
            """,
            [
                json.dumps(answers or {}, ensure_ascii=False),
                int(answered_count or 0),
                int(current_item_index or 0),
                int(started_at) if started_at not in (None, "") else None,
                int(saved_use_time or 0),
                now,
                existing["id"],
            ],
        )
        return get_scale_draft(
            user_id=user_id,
            scale_slug=normalized_scale_slug,
            flow_session_id=normalized_flow_session_id,
        )

    draft_id = db.insert(
        """
        INSERT INTO scale_assessment_drafts (
            user_id, username, scale_slug, flow_session_id, answers_json,
            answered_count, current_item_index, started_at, saved_use_time,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            user_id,
            username,
            normalized_scale_slug,
            normalized_flow_session_id,
            json.dumps(answers or {}, ensure_ascii=False),
            int(answered_count or 0),
            int(current_item_index or 0),
            int(started_at) if started_at not in (None, "") else None,
            int(saved_use_time or 0),
            "draft",
            now,
            now,
        ],
    )
    return get_scale_draft_by_id(draft_id)


def clear_scale_draft(*, user_id: int, scale_slug: str, flow_session_id: Optional[str] = None) -> int:
    now = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    normalized_scale_slug = str(scale_slug).strip().lower()
    normalized_flow_session_id = (
        str(flow_session_id).strip() if flow_session_id not in (None, "") else None
    )

    if normalized_flow_session_id:
        return db.update(
            """
            UPDATE scale_assessment_drafts
            SET status = 'completed', updated_at = ?, completed_at = ?
            WHERE user_id = ? AND scale_slug = ? AND status = 'draft' AND flow_session_id = ?
            """,
            [
                now,
                now,
                user_id,
                normalized_scale_slug,
                normalized_flow_session_id,
            ],
        )

    return db.update(
        """
        UPDATE scale_assessment_drafts
        SET status = 'completed', updated_at = ?, completed_at = ?
        WHERE user_id = ? AND scale_slug = ? AND status = 'draft'
          AND (flow_session_id IS NULL OR flow_session_id = '')
        """,
        [
            now,
            now,
            user_id,
            normalized_scale_slug,
        ],
    )


def get_scale_draft_by_id(draft_id: int):
    record = db.fetch_one("SELECT * FROM scale_assessment_drafts WHERE id = ?", [draft_id])
    return _deserialize_scale_draft(record)


def _deserialize_scale_record(record: Optional[Dict]):
    if not record:
        return None

    normalized = dict(record)
    normalized["answers"] = json.loads(normalized.get("answers_json") or "{}")
    normalized["risk_flags"] = json.loads(normalized.get("risk_flags_json") or "[]")
    normalized["highlights"] = json.loads(normalized.get("highlights_json") or "[]")
    return normalized


def _deserialize_scale_draft(record: Optional[Dict]):
    if not record:
        return None

    normalized = dict(record)
    normalized["answers"] = json.loads(normalized.get("answers_json") or "{}")
    normalized["flow_session_id"] = normalized.get("flow_session_id") or None
    return normalized
