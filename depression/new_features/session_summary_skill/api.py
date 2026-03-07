#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session summary skill API blueprint.

All new endpoints are isolated in this folder and do not change existing
chat/RAG endpoint behavior.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, jsonify, request, session

from .service import SessionSummarySkill

logger = logging.getLogger(__name__)

session_summary_bp = Blueprint("session_summary_skill", __name__)
skill = SessionSummarySkill()


@session_summary_bp.route("/api/skills/session-summary", methods=["GET"])
def session_summary_skill_info():
    """Return skill metadata for discovery."""
    return jsonify({"status": "success", "skill": skill.metadata()})


@session_summary_bp.route("/api/skills/session-summary/health", methods=["GET"])
def session_summary_skill_health():
    """Health endpoint for this feature only."""
    return jsonify({"status": "ok", "skill": "session-summary"})


@session_summary_bp.route("/api/skills/session-summary", methods=["POST"])
def session_summary_skill_run():
    """Generate a summary from request history or DB records."""
    try:
        userinfo = session.get("userinfo", {})
        username = userinfo.get("username", "")
        if not username:
            return jsonify({"status": "error", "message": "未登录"}), 401

        payload: Dict[str, Any] = request.get_json(silent=True) or {}

        result = skill.run(
            username=username,
            history=payload.get("history"),
            limit=payload.get("limit", 30),
            style=payload.get("style", "structured"),
            max_points=payload.get("max_points", 8),
            include_risk=payload.get("include_risk", True),
            timeout=payload.get("timeout", 90),
            max_tokens=payload.get("max_tokens", 1200),
        )

        return jsonify(
            {
                "status": "success",
                "skill": result.get("skill", {}),
                "data": {
                    "summary": result.get("summary", ""),
                    "conversation_rounds": result.get("conversation_rounds", 0),
                    "source": result.get("source", "db"),
                    "style": result.get("style", "structured"),
                    "generated_at": result.get("generated_at", ""),
                },
            }
        )
    except Exception as exc:
        logger.error("session summary skill failed: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500