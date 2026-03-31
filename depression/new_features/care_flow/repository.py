"""Persistence helpers for the refactored care journey flow."""

from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Optional

from utils import db


def _now() -> str:
    return datetime.datetime.now().isoformat(sep=" ", timespec="seconds")


def ensure_care_flow_tables() -> None:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS patient_profiles (
            user_id INTEGER PRIMARY KEY,
            display_name TEXT,
            age_band TEXT,
            gender TEXT,
            first_visit INTEGER DEFAULT 1,
            emotional_history TEXT,
            support_focus TEXT,
            updated_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS care_preferences (
            user_id INTEGER PRIMARY KEY,
            doctor_slug TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            interaction_style TEXT NOT NULL,
            voice_enabled INTEGER DEFAULT 1,
            greeting_script TEXT,
            avatar_video TEXT,
            updated_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_system_settings (
            user_id INTEGER PRIMARY KEY,
            voice_broadcast INTEGER DEFAULT 1,
            capture_audio INTEGER DEFAULT 1,
            capture_camera INTEGER DEFAULT 1,
            capture_eeg INTEGER DEFAULT 0,
            privacy_ack INTEGER DEFAULT 0,
            debug_mode INTEGER DEFAULT 0,
            updated_at DATETIME NOT NULL,
            created_at DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS regulation_plan_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            phq_record_id INTEGER,
            gad_record_id INTEGER,
            risk_level TEXT NOT NULL,
            plan_title TEXT NOT NULL,
            plan_summary TEXT NOT NULL,
            recommendation_json TEXT NOT NULL DEFAULT '[]',
            execution_mode TEXT NOT NULL,
            media_type TEXT NOT NULL DEFAULT 'video',
            media_url TEXT,
            engine_name TEXT NOT NULL DEFAULT 'rule-engine-placeholder',
            status TEXT NOT NULL DEFAULT 'draft',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );

        CREATE TABLE IF NOT EXISTS regulation_execution_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            feedback_score INTEGER DEFAULT 0,
            feedback_text TEXT,
            duration_seconds INTEGER DEFAULT 0,
            completed_at DATETIME NOT NULL
        );
        """
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_patient_profile(user_id: int) -> Optional[Dict[str, Any]]:
    return db.fetch_one("SELECT * FROM patient_profiles WHERE user_id = ?", [user_id])


def save_patient_profile(user_id: int, payload: Dict[str, Any]) -> None:
    now = _now()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO patient_profiles (
            user_id, display_name, age_band, gender, first_visit,
            emotional_history, support_focus, updated_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            display_name = excluded.display_name,
            age_band = excluded.age_band,
            gender = excluded.gender,
            first_visit = excluded.first_visit,
            emotional_history = excluded.emotional_history,
            support_focus = excluded.support_focus,
            updated_at = excluded.updated_at
        """,
        [
            user_id,
            payload.get("display_name", ""),
            payload.get("age_band", ""),
            payload.get("gender", ""),
            1 if payload.get("first_visit", True) else 0,
            payload.get("emotional_history", ""),
            payload.get("support_focus", ""),
            now,
            now,
        ],
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_care_preference(user_id: int) -> Optional[Dict[str, Any]]:
    return db.fetch_one("SELECT * FROM care_preferences WHERE user_id = ?", [user_id])


def save_care_preference(user_id: int, payload: Dict[str, Any]) -> None:
    now = _now()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO care_preferences (
            user_id, doctor_slug, doctor_name, interaction_style, voice_enabled,
            greeting_script, avatar_video, updated_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            doctor_slug = excluded.doctor_slug,
            doctor_name = excluded.doctor_name,
            interaction_style = excluded.interaction_style,
            voice_enabled = excluded.voice_enabled,
            greeting_script = excluded.greeting_script,
            avatar_video = excluded.avatar_video,
            updated_at = excluded.updated_at
        """,
        [
            user_id,
            payload.get("doctor_slug", ""),
            payload.get("doctor_name", ""),
            payload.get("interaction_style", ""),
            1 if payload.get("voice_enabled", True) else 0,
            payload.get("greeting_script", ""),
            payload.get("avatar_video", ""),
            now,
            now,
        ],
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_user_settings(user_id: int) -> Optional[Dict[str, Any]]:
    return db.fetch_one("SELECT * FROM user_system_settings WHERE user_id = ?", [user_id])


def save_user_settings(user_id: int, payload: Dict[str, Any]) -> None:
    now = _now()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_system_settings (
            user_id, voice_broadcast, capture_audio, capture_camera, capture_eeg,
            privacy_ack, debug_mode, updated_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            voice_broadcast = excluded.voice_broadcast,
            capture_audio = excluded.capture_audio,
            capture_camera = excluded.capture_camera,
            capture_eeg = excluded.capture_eeg,
            privacy_ack = excluded.privacy_ack,
            debug_mode = excluded.debug_mode,
            updated_at = excluded.updated_at
        """,
        [
            user_id,
            1 if payload.get("voice_broadcast", True) else 0,
            1 if payload.get("capture_audio", True) else 0,
            1 if payload.get("capture_camera", True) else 0,
            1 if payload.get("capture_eeg", False) else 0,
            1 if payload.get("privacy_ack", False) else 0,
            1 if payload.get("debug_mode", False) else 0,
            now,
            now,
        ],
    )
    conn.commit()
    cursor.close()
    conn.close()


def create_regulation_plan(user_id: int, payload: Dict[str, Any]) -> int:
    now = _now()
    return db.insert(
        """
        INSERT INTO regulation_plan_records (
            user_id, phq_record_id, gad_record_id, risk_level, plan_title, plan_summary,
            recommendation_json, execution_mode, media_type, media_url, engine_name,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            user_id,
            payload.get("phq_record_id"),
            payload.get("gad_record_id"),
            payload.get("risk_level", ""),
            payload.get("plan_title", ""),
            payload.get("plan_summary", ""),
            json.dumps(payload.get("recommendations", []), ensure_ascii=False),
            payload.get("execution_mode", ""),
            payload.get("media_type", "video"),
            payload.get("media_url", ""),
            payload.get("engine_name", "rule-engine-placeholder"),
            payload.get("status", "draft"),
            now,
            now,
        ],
    )


def get_regulation_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    record = db.fetch_one("SELECT * FROM regulation_plan_records WHERE id = ?", [plan_id])
    return _deserialize_plan(record)


def get_latest_regulation_plan(user_id: int) -> Optional[Dict[str, Any]]:
    record = db.fetch_one(
        """
        SELECT * FROM regulation_plan_records
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        [user_id],
    )
    return _deserialize_plan(record)


def list_regulation_plans(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    rows = db.fetch_all(
        """
        SELECT * FROM regulation_plan_records
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        [user_id, int(limit)],
    ) or []
    return [_deserialize_plan(row) for row in rows]


def create_execution_record(
    *,
    plan_id: int,
    user_id: int,
    feedback_score: int = 0,
    feedback_text: str = "",
    duration_seconds: int = 0,
) -> int:
    return db.insert(
        """
        INSERT INTO regulation_execution_records (
            plan_id, user_id, feedback_score, feedback_text, duration_seconds, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            plan_id,
            user_id,
            int(feedback_score or 0),
            feedback_text or "",
            int(duration_seconds or 0),
            _now(),
        ],
    )


def list_execution_records(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    return db.fetch_all(
        """
        SELECT * FROM regulation_execution_records
        WHERE user_id = ?
        ORDER BY completed_at DESC, id DESC
        LIMIT ?
        """,
        [user_id, int(limit)],
    ) or []


def get_admin_snapshot(limit: int = 20) -> Dict[str, Any]:
    limit = int(limit)
    return {
        "users": db.fetch_all(
            "SELECT id, name, mobile, role FROM userinfo ORDER BY id DESC LIMIT ?",
            [limit],
        )
        or [],
        "scale_records": db.fetch_all(
            """
            SELECT id, username, scale_code, total_score, severity_label, completed_at
            FROM scale_assessment_records
            ORDER BY completed_at DESC, id DESC
            LIMIT ?
            """,
            [limit],
        )
        or [],
        "plans": db.fetch_all(
            """
            SELECT id, user_id, risk_level, plan_title, execution_mode, status, created_at
            FROM regulation_plan_records
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            [limit],
        )
        or [],
        "executions": db.fetch_all(
            """
            SELECT id, plan_id, user_id, feedback_score, duration_seconds, completed_at
            FROM regulation_execution_records
            ORDER BY completed_at DESC, id DESC
            LIMIT ?
            """,
            [limit],
        )
        or [],
    }


def _deserialize_plan(record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not record:
        return None

    normalized = dict(record)
    normalized["recommendations"] = json.loads(normalized.get("recommendation_json") or "[]")
    return normalized

