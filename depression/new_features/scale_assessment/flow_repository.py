"""Persistence helpers for screening flow sessions."""

from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from utils import db


def ensure_flow_tables():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scale_screening_flow_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_session_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'in_progress',
            recommended_order_json TEXT DEFAULT '[]',
            completed_scales_json TEXT DEFAULT '[]',
            draft_scales_json TEXT DEFAULT '[]',
            draft_state_json TEXT DEFAULT '{}',
            scale_record_links_json TEXT DEFAULT '{}',
            last_risk_result_json TEXT,
            risk_assessment_generated INTEGER DEFAULT 0,
            latest_trigger_reason TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            finished_at DATETIME
        )
        """
    )
    conn.commit()
    cursor.close()
    conn.close()


def create_flow_session(
    *,
    user_id: int,
    username: str,
    recommended_order: Optional[List[str]] = None,
) -> str:
    now = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    flow_session_id = f"flow-{uuid4()}"
    db.insert(
        """
        INSERT INTO scale_screening_flow_sessions (
            flow_session_id, user_id, username, status,
            recommended_order_json, completed_scales_json, draft_scales_json,
            draft_state_json, scale_record_links_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            flow_session_id,
            user_id,
            username,
            "in_progress",
            _to_json(recommended_order or []),
            _to_json([]),
            _to_json([]),
            _to_json({}),
            _to_json({}),
            now,
            now,
        ],
    )
    return flow_session_id


def get_flow_session(flow_session_id: str, *, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if not flow_session_id:
        return None

    sql = "SELECT * FROM scale_screening_flow_sessions WHERE flow_session_id = ?"
    params: List[Any] = [flow_session_id]
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    return _deserialize(db.fetch_one(sql, params))


def get_active_flow_session(*, user_id: int) -> Optional[Dict[str, Any]]:
    row = db.fetch_one(
        """
        SELECT *
        FROM scale_screening_flow_sessions
        WHERE user_id = ? AND status = 'in_progress'
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        [user_id],
    )
    return _deserialize(row)


def update_flow_session(
    flow_session_id: str,
    *,
    user_id: int,
    status: Optional[str] = None,
    recommended_order: Optional[List[str]] = None,
    completed_scales: Optional[List[str]] = None,
    draft_scales: Optional[List[str]] = None,
    draft_state: Optional[Dict[str, Any]] = None,
    scale_record_links: Optional[Dict[str, Any]] = None,
    last_risk_result: Optional[Dict[str, Any]] = None,
    risk_assessment_generated: Optional[bool] = None,
    latest_trigger_reason: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> int:
    existing = get_flow_session(flow_session_id, user_id=user_id)
    if not existing:
        return 0

    now = datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
    next_status = status or existing["status"]
    next_recommended_order = recommended_order if recommended_order is not None else existing["recommended_order"]
    next_completed_scales = completed_scales if completed_scales is not None else existing["completed_scales"]
    next_draft_scales = draft_scales if draft_scales is not None else existing["draft_scales"]
    next_draft_state = draft_state if draft_state is not None else existing["draft_state"]
    next_scale_record_links = (
        scale_record_links if scale_record_links is not None else existing["scale_record_links"]
    )
    next_last_risk_result = (
        last_risk_result if last_risk_result is not None else existing.get("last_risk_result")
    )
    next_risk_assessment_generated = (
        int(bool(risk_assessment_generated))
        if risk_assessment_generated is not None
        else int(bool(existing.get("risk_assessment_generated")))
    )
    next_latest_trigger_reason = (
        latest_trigger_reason
        if latest_trigger_reason is not None
        else existing.get("latest_trigger_reason")
    )
    next_finished_at = finished_at if finished_at is not None else existing.get("finished_at")

    return db.update(
        """
        UPDATE scale_screening_flow_sessions
        SET status = ?, recommended_order_json = ?, completed_scales_json = ?,
            draft_scales_json = ?, draft_state_json = ?, scale_record_links_json = ?,
            last_risk_result_json = ?, risk_assessment_generated = ?, latest_trigger_reason = ?,
            updated_at = ?, finished_at = ?
        WHERE flow_session_id = ? AND user_id = ?
        """,
        [
            next_status,
            _to_json(next_recommended_order),
            _to_json(next_completed_scales),
            _to_json(next_draft_scales),
            _to_json(next_draft_state),
            _to_json(next_scale_record_links),
            _to_json(next_last_risk_result) if next_last_risk_result is not None else None,
            next_risk_assessment_generated,
            next_latest_trigger_reason,
            now,
            next_finished_at,
            flow_session_id,
            user_id,
        ],
    )


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _deserialize(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None

    normalized = dict(row)
    normalized["recommended_order"] = _from_json(normalized.get("recommended_order_json"), [])
    normalized["completed_scales"] = _from_json(normalized.get("completed_scales_json"), [])
    normalized["draft_scales"] = _from_json(normalized.get("draft_scales_json"), [])
    normalized["draft_state"] = _from_json(normalized.get("draft_state_json"), {})
    normalized["scale_record_links"] = _from_json(normalized.get("scale_record_links_json"), {})
    normalized["last_risk_result"] = _from_json(normalized.get("last_risk_result_json"), None)
    normalized["risk_assessment_generated"] = bool(normalized.get("risk_assessment_generated"))
    return normalized


def _from_json(value: Any, default: Any):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default
