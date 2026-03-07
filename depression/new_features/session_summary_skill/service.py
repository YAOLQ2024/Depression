#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session summary skill service.

This module is isolated under new_features/session_summary_skill and does not
change existing chat or RAG behavior.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional

from utils import db
from utils.emollm_client import get_emollm_client

logger = logging.getLogger(__name__)

SKILL_NAME = "session-summary"
SKILL_VERSION = "1.0.0"
DEFAULT_STYLE = "structured"
ALLOWED_STYLES = {"brief", "structured", "clinical"}
MAX_ROUNDS = 100


class SessionSummarySkill:
    """Generate a session summary from existing counseling records."""

    def metadata(self) -> Dict[str, Any]:
        return {
            "name": SKILL_NAME,
            "version": SKILL_VERSION,
            "description": "Summarize multi-turn counseling dialogs into an actionable brief.",
            "input": {
                "history": "optional list; if omitted, load records from DB by username",
                "limit": "optional int, default 30, max 100",
                "style": "brief | structured | clinical",
                "max_points": "optional int, default 8",
                "include_risk": "optional bool, default true",
            },
            "output": {
                "summary": "string",
                "conversation_rounds": "int",
                "source": "db | request_history",
                "generated_at": "ISO datetime",
            },
        }

    def run(
        self,
        *,
        username: str,
        history: Optional[List[Any]] = None,
        limit: int = 30,
        style: str = DEFAULT_STYLE,
        max_points: int = 8,
        include_risk: bool = True,
        timeout: int = 90,
        max_tokens: int = 1200,
    ) -> Dict[str, Any]:
        style = _normalize_style(style)
        max_points = max(3, min(int(max_points), 20))
        timeout = max(20, min(int(timeout), 300))
        max_tokens = max(256, min(int(max_tokens), 2048))

        if history:
            rounds = normalize_history_records(history)
            source = "request_history"
        else:
            rounds = load_history_from_db(username, limit)
            source = "db"

        if not rounds:
            return {
                "summary": "暂无可总结的会话记录。",
                "conversation_rounds": 0,
                "source": source,
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "skill": {"name": SKILL_NAME, "version": SKILL_VERSION},
            }

        prompt = build_summary_prompt(
            rounds=rounds,
            style=style,
            max_points=max_points,
            include_risk=include_risk,
        )

        summary = call_summary_llm(
            prompt=prompt,
            timeout=timeout,
            max_tokens=max_tokens,
        )
        if not summary:
            summary = fallback_summary(rounds, style, max_points)

        return {
            "summary": summary,
            "conversation_rounds": len(rounds),
            "source": source,
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "skill": {"name": SKILL_NAME, "version": SKILL_VERSION},
            "style": style,
        }


def ensure_counseling_records_table() -> None:
    """Create table if missing, matching existing project schema."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS counseling_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            emotion_context TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def load_history_from_db(username: str, limit: int = 30) -> List[Dict[str, str]]:
    """Load recent counseling rounds for one user."""
    if not username:
        return []

    safe_limit = max(1, min(int(limit), MAX_ROUNDS))
    ensure_counseling_records_table()

    sql = """
        SELECT user_message, ai_response, timestamp
        FROM counseling_records
        WHERE username = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    rows = db.fetch_all(sql, [username, safe_limit]) or []

    records: List[Dict[str, str]] = []
    for row in rows:
        user_message = str(row.get("user_message", "") or "").strip()
        ai_response = str(row.get("ai_response", "") or "").strip()
        timestamp = str(row.get("timestamp", "") or "").strip()
        if user_message or ai_response:
            records.append(
                {
                    "user_message": user_message,
                    "ai_response": ai_response,
                    "timestamp": timestamp,
                }
            )

    # Query used DESC for speed; reverse back to chronological order.
    records.reverse()
    return records


def normalize_history_records(history: List[Any]) -> List[Dict[str, str]]:
    """Normalize mixed history payload formats into round records."""
    rounds: List[Dict[str, str]] = []
    if not isinstance(history, list):
        return rounds

    # Format A: [{user_message, ai_response, ...}, ...]
    if history and isinstance(history[0], dict) and (
        "user_message" in history[0] or "ai_response" in history[0]
    ):
        for item in history[:MAX_ROUNDS]:
            user_message = str(item.get("user_message", "") or "").strip()
            ai_response = str(item.get("ai_response", "") or "").strip()
            if user_message or ai_response:
                rounds.append({"user_message": user_message, "ai_response": ai_response})
        return rounds

    # Format B: OpenAI-like [{role, content}, ...]
    if history and isinstance(history[0], dict) and "role" in history[0]:
        pending_user = ""
        for item in history:
            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "") or "").strip()
            if not content:
                continue
            if role == "user":
                if pending_user:
                    rounds.append({"user_message": pending_user, "ai_response": ""})
                pending_user = content
            elif role in {"assistant", "ai", "system"}:
                rounds.append({"user_message": pending_user, "ai_response": content})
                pending_user = ""
        if pending_user:
            rounds.append({"user_message": pending_user, "ai_response": ""})
        return rounds[:MAX_ROUNDS]

    # Format C: [(user, ai), ...]
    for item in history[:MAX_ROUNDS]:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            user_message = str(item[0] or "").strip()
            ai_response = str(item[1] or "").strip()
            if user_message or ai_response:
                rounds.append({"user_message": user_message, "ai_response": ai_response})
    return rounds


def build_summary_prompt(
    *,
    rounds: List[Dict[str, str]],
    style: str,
    max_points: int,
    include_risk: bool,
) -> str:
    """Compose compact summary prompt for LLM."""
    lines: List[str] = []
    for idx, record in enumerate(rounds, 1):
        user_text = record.get("user_message", "")
        ai_text = record.get("ai_response", "")
        lines.append(f"[第{idx}轮]")
        lines.append(f"用户: {user_text}")
        lines.append(f"助手: {ai_text}")

    style_hint = {
        "brief": "请输出精简摘要，重点写核心问题与建议，不超过6条。",
        "structured": "请按结构化小标题输出：主诉、情绪变化、关键事件、建议。",
        "clinical": "请采用临床风格，包含风险信号、保护因素、后续建议。",
    }[style]

    risk_requirement = (
        "若对话中存在自伤/绝望/失眠恶化等风险信号，请单独列出“风险提示”。"
        if include_risk
        else "无需单列风险提示。"
    )

    return (
        "你是心理健康会话总结助手。请对以下多轮会话做高质量中文总结。\n"
        f"要求1: {style_hint}\n"
        f"要求2: 仅输出总结正文，最多{max_points}个要点。\n"
        f"要求3: {risk_requirement}\n\n"
        "会话记录如下:\n"
        + "\n".join(lines)
    )


def call_summary_llm(*, prompt: str, timeout: int, max_tokens: int) -> str:
    """Call current LLM endpoint directly to avoid changing legacy chat flow."""
    try:
        client = get_emollm_client()
        payload = {
            "model": client.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是会话总结助手。输出中文总结，不要输出无关说明。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "top_p": 0.8,
            "max_tokens": max_tokens,
            "stream": False,
        }

        resp = client.session.post(client.api_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""

        content = choices[0].get("message", {}).get("content", "")
        return str(content or "").strip()
    except Exception as exc:
        logger.warning("[session-summary] llm summary failed: %s", exc)
        return ""


def fallback_summary(rounds: List[Dict[str, str]], style: str, max_points: int) -> str:
    """Deterministic fallback when LLM is unavailable."""
    latest = rounds[-1]
    recent_users = [r.get("user_message", "") for r in rounds[-min(3, len(rounds)) :]]
    head = "；".join([x for x in recent_users if x][:2])

    lines = [
        "### 会话概览",
        f"- 共{len(rounds)}轮对话，最近主诉：{(latest.get('user_message') or '未提供')[:120]}",
    ]

    if head:
        lines.append(f"- 近期关键表达：{head[:180]}")

    if style in {"structured", "clinical"}:
        lines.append("- 建议继续完成量表评估并结合历史会话进行阶段性复盘。")
        lines.append("- 建议记录睡眠、食欲、活动意愿等情绪相关指标以便持续观察。")

    return "\n".join(lines[: max(2, max_points)])


def _normalize_style(style: str) -> str:
    normalized = str(style or DEFAULT_STYLE).strip().lower()
    if normalized not in ALLOWED_STYLES:
        return DEFAULT_STYLE
    return normalized