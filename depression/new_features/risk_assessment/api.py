"""Blueprint for the risk assessment module."""

from __future__ import annotations

import logging

from flask import Blueprint, request, session

from new_features.api_common import api_error, api_health, api_meta, api_notice, api_success
from .engine import RiskAssessmentValidationError, evaluate_risk_assessment
from .rules import threshold_snapshot

risk_assessment_bp = Blueprint("risk_assessment", __name__)
logger = logging.getLogger(__name__)


def _get_current_identity():
    userinfo = session.get("userinfo", {})
    user_id = userinfo.get("id")
    username = userinfo.get("name") or userinfo.get("username") or "unknown"
    return userinfo, user_id, username


@risk_assessment_bp.route("/api/v1/risk-assessment/risk-stratification/score", methods=["POST"])
def risk_stratification_score():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error(
            4001,
            "请求体必须为 JSON 对象",
            status_code=400,
            data={"module": "risk-assessment", "capability": "risk-stratification"},
        )

    _, session_user_id, session_username = _get_current_identity()
    if not session_user_id:
        return api_error(
            4003,
            "用户未登录或鉴权失败",
            status_code=401,
            data={
                "module": "risk-assessment",
                "capability": "risk-stratification",
                "reason": "login required before risk assessment",
            },
        )

    payload["user_id"] = session_user_id
    payload.setdefault("session_username", session_username)

    try:
        result = evaluate_risk_assessment(payload)
    except RiskAssessmentValidationError as exc:
        return api_error(
            exc.code,
            str(exc),
            status_code=400 if 4000 <= exc.code < 5000 else 500,
            data={
                "module": "risk-assessment",
                "capability": "risk-stratification",
                **exc.data,
            },
        )
    except Exception as exc:  # pragma: no cover - defensive API boundary
        logger.exception("risk assessment score failed")
        return api_error(
            5001,
            "risk stratification engine failed",
            status_code=500,
            data={
                "module": "risk-assessment",
                "capability": "risk-stratification",
                "stage": "rule_evaluation",
                "error": str(exc),
            },
        )

    body = {
        "result": result.to_result_dict(),
    }
    if result.advisory_code:
        return api_notice(result.advisory_code, result.advisory_message, data=body)
    return api_success(body)


@risk_assessment_bp.route("/api/v1/risk-assessment/risk-stratification/health", methods=["GET"])
def risk_stratification_health():
    return api_health(
        mode="rule_based_v1",
        model_loaded=True,
        extra={
            "engine_type": "rule_engine_v1_scale_first",
            "threshold_policy": threshold_snapshot(),
            "supports_mock": True,
        },
    )


@risk_assessment_bp.route("/api/v1/risk-assessment/risk-stratification/meta", methods=["GET"])
def risk_stratification_meta():
    return api_meta(
        module="risk-assessment",
        capability="risk-stratification",
        module_zh="风险评估与安全建议模块",
        capability_zh="初步风险分层与安全建议能力",
        owner="team-risk",
        supports_mock=True,
        extra={
            "engine_type": "rule_engine_v1_scale_first",
            "primary_signal": "assessment",
            "secondary_signals": ["text", "speech", "emotion", "eeg"],
            "risk_levels_supported": ["low", "medium", "high", "urgent"],
            "advisory_codes": [1001],
            "threshold_policy": threshold_snapshot(),
            "implemented_actions": ["score", "health", "meta"],
            "output_contract": {
                "required_fields": [
                    "risk_level",
                    "risk_score",
                    "referral_recommended",
                    "emergency_notice",
                    "allow_continue",
                    "recommended_next_step",
                ]
            },
        },
    )
