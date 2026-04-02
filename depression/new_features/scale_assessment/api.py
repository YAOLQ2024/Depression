"""Blueprint for PHQ-9 / GAD-7 structured assessment."""

from __future__ import annotations

import logging
import time

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from new_features.api_common import api_error, api_health, api_meta, api_notice, api_success
from new_features.risk_assessment.engine import RiskAssessmentValidationError
from utils import db
from .definitions import get_scale_definition, list_scale_definitions
from .engine import ScaleValidationError, evaluate_scale
from .flow_service import (
    FlowSessionError,
    attach_sds_completion,
    build_flow_risk_payload,
    finalize_flow_risk_assessment,
    get_current_flow_session,
    get_flow_session_for_user,
    save_flow_draft,
    serialize_flow_session,
    start_or_resume_flow_session,
    mark_structured_scale_completed,
)
from .repository import (
    clear_scale_draft,
    create_scale_record,
    ensure_scale_tables,
    get_scale_draft,
    get_latest_scale_records,
    get_scale_record,
    upsert_scale_draft,
)

scale_assessment_bp = Blueprint(
    "scale_assessment",
    __name__,
    template_folder="templates",
)
logger = logging.getLogger(__name__)

ensure_scale_tables()


def _get_current_identity():
    userinfo = session.get("userinfo", {})
    user_id = userinfo.get("id")
    username = userinfo.get("name") or userinfo.get("username") or "unknown"
    return userinfo, user_id, username


def _normalize_scale_slug(raw_value):
    if not raw_value:
        return None

    normalized = str(raw_value).strip().lower().replace("-", "")
    alias_map = {
        "phq9": "phq9",
        "gad7": "gad7",
    }
    return alias_map.get(normalized, normalized)


def _extract_answers(raw_answers):
    if isinstance(raw_answers, dict):
        return raw_answers

    if isinstance(raw_answers, list):
        answers = {}
        for item in raw_answers:
            if not isinstance(item, dict):
                raise ScaleValidationError("answers 列表中的元素必须是对象")

            question_id = item.get("question_id") or item.get("item_id") or item.get("id")
            if not question_id:
                raise ScaleValidationError("answers 列表中缺少 question_id")

            if "answer_value" in item:
                answer_value = item.get("answer_value")
            else:
                answer_value = item.get("value")

            answers[str(question_id)] = answer_value
        return answers

    raise ScaleValidationError("answers 格式无效，应为对象或数组")


def _calculate_use_time(payload):
    explicit_use_time = payload.get("use_time")
    if explicit_use_time not in (None, ""):
        try:
            return max(0, int(explicit_use_time))
        except (TypeError, ValueError):
            pass

    started_at = payload.get("started_at")
    if str(started_at).isdigit():
        return max(0, int(time.time()) - int(str(started_at)))

    return 0


def _extract_flow_session_id(payload):
    if not isinstance(payload, dict):
        return None

    raw_flow_session_id = payload.get("flow_session_id")
    if raw_flow_session_id in (None, ""):
        return None
    return str(raw_flow_session_id).strip() or None


def _serialize_scale_definition(scale_def, *, include_items=True):
    if not scale_def:
        return None

    payload = {
        "scale_slug": scale_def["slug"],
        "scale_code": scale_def["code"],
        "scale_name": scale_def["name"],
        "short_name": scale_def["short_name"],
        "description": scale_def["description"],
        "intro": scale_def["intro"],
        "mode": scale_def["mode"],
        "item_count": len(scale_def["items"]),
        "options": scale_def["options"],
    }

    if include_items:
        payload["items"] = scale_def["items"]

    return payload


def _serialize_scale_record(record):
    if not record:
        return None

    return {
        "record_id": record["id"],
        "user_id": record["user_id"],
        "username": record["username"],
        "scale_slug": record["scale_slug"],
        "scale_code": record["scale_code"],
        "scale_name": record["scale_name"],
        "answers": record["answers"],
        "total_score": record["total_score"],
        "severity_key": record["severity_key"],
        "severity_label": record["severity_label"],
        "risk_flags": record["risk_flags"],
        "highlights": record["highlights"],
        "summary": record["summary"],
        "interpretation": record["interpretation"],
        "recommended_action": record["recommended_action"],
        "created_at": record["created_at"],
        "completed_at": record["completed_at"],
        "use_time": record.get("use_time", 0),
    }


def _serialize_scale_draft(draft):
    if not draft:
        return None

    return {
        "draft_id": draft["id"],
        "user_id": draft["user_id"],
        "username": draft["username"],
        "scale_slug": draft["scale_slug"],
        "flow_session_id": draft.get("flow_session_id"),
        "answers": draft.get("answers") or {},
        "answered_count": int(draft.get("answered_count") or 0),
        "current_item_index": int(draft.get("current_item_index") or 0),
        "started_at": draft.get("started_at"),
        "saved_use_time": int(draft.get("saved_use_time") or 0),
        "status": draft.get("status") or "draft",
        "created_at": draft.get("created_at"),
        "updated_at": draft.get("updated_at"),
    }


def _extract_optional_preview_body():
    if request.method == "GET":
        return {}

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise ScaleValidationError("请求体必须为 JSON 对象")
    return payload


@scale_assessment_bp.route("/scales", methods=["GET"])
def scale_home():
    return render_template("scale_assessment/index.html")


@scale_assessment_bp.route("/scales/<scale_slug>", methods=["GET"])
def scale_form(scale_slug):
    scale_def = get_scale_definition(scale_slug)
    if not scale_def:
        flash("暂不支持该量表。", "error")
        return redirect(url_for("scale_assessment.scale_home"))

    return render_template(
        "scale_assessment/fill.html",
        scale_slug=scale_def["slug"],
        scale_short_name=scale_def["short_name"],
        started_at=int(time.time()),
        flow_session_id=str(request.args.get("flow_session_id") or "").strip(),
    )


@scale_assessment_bp.route("/scales/<scale_slug>/submit", methods=["POST"])
def scale_submit(scale_slug):
    scale_def = get_scale_definition(scale_slug)
    if not scale_def:
        flash("暂不支持该量表。", "error")
        return redirect(url_for("scale_assessment.scale_home"))

    userinfo = session.get("userinfo", {})
    username = userinfo.get("name") or userinfo.get("username") or "unknown"
    user_id = userinfo.get("id")
    if not user_id:
        flash("登录信息失效，请重新登录。", "error")
        return redirect("/login")

    raw_answers = {}
    for item in scale_def["items"]:
        raw_answers[item["id"]] = request.form.get(item["id"])

    started_at = request.form.get("started_at", "")
    use_time = 0
    if started_at.isdigit():
        use_time = max(0, int(time.time()) - int(started_at))

    try:
        result = evaluate_scale(scale_slug, raw_answers).to_dict()
    except ScaleValidationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("scale_assessment.scale_form", scale_slug=scale_slug))

    record_id = create_scale_record(
        user_id=user_id,
        username=username,
        result=result,
        use_time=use_time,
    )
    return redirect(url_for("scale_assessment.scale_result", record_id=record_id))


@scale_assessment_bp.route("/scales/result/<int:record_id>", methods=["GET"])
def scale_result(record_id):
    return render_template(
        "scale_assessment/result.html",
        record_id=record_id,
        flow_session_id=str(request.args.get("flow_session_id") or "").strip(),
    )


@scale_assessment_bp.route("/scales/flow-result/<flow_session_id>", methods=["GET"])
def scale_flow_result(flow_session_id):
    return render_template(
        "scale_assessment/flow_result.html",
        flow_session_id=flow_session_id,
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/list", methods=["GET"])
def scale_api_list():
    requested_scale_slug = _normalize_scale_slug(request.args.get("scale_slug"))
    include_items = str(request.args.get("include_items", "true")).lower() == "true"
    scale_definitions = list_scale_definitions()
    if requested_scale_slug:
        scale_definitions = [
            scale_def
            for scale_def in scale_definitions
            if scale_def["slug"] == requested_scale_slug
        ]

    items = [
        _serialize_scale_definition(scale_def, include_items=include_items)
        for scale_def in scale_definitions
    ]

    return api_success(
        {
            "items": items,
            "pagination": {
                "page": 1,
                "page_size": len(items),
                "total": len(items),
                "has_more": False,
            },
        }
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/submit", methods=["POST"])
def scale_api_submit():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error(4001, "请求体必须为 JSON 对象", status_code=400)

    _, user_id, username = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    scale_slug = _normalize_scale_slug(payload.get("scale_slug") or payload.get("scale_type"))
    if not scale_slug:
        return api_error(4001, "缺少必填字段: scale_type", status_code=400)

    scale_def = get_scale_definition(scale_slug)
    if not scale_def:
        return api_error(4004, "暂不支持该量表类型", status_code=404)

    flow_session_id = _extract_flow_session_id(payload)
    if flow_session_id:
        try:
            get_flow_session_for_user(flow_session_id, user_id=user_id)
        except FlowSessionError as exc:
            return api_error(4004, str(exc), status_code=404)

    try:
        raw_answers = _extract_answers(payload.get("answers"))
        result = evaluate_scale(scale_slug, raw_answers).to_dict()
        use_time = _calculate_use_time(payload)
        record_id = create_scale_record(
            user_id=user_id,
            username=username,
            result=result,
            use_time=use_time,
        )
        clear_scale_draft(
            user_id=user_id,
            scale_slug=scale_slug,
            flow_session_id=flow_session_id,
        )
        flow_session = None
        if flow_session_id:
            flow_session = mark_structured_scale_completed(
                flow_session_id,
                user_id=user_id,
                scale_slug=scale_slug,
                record_id=record_id,
            )
    except ScaleValidationError as exc:
        return api_error(4002, str(exc), status_code=400)
    except FlowSessionError as exc:
        return api_error(4004, str(exc), status_code=404)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        logger.exception("scale api submit failed")
        return api_error(5001, f"量表评估服务内部异常: {exc}", status_code=500)

    return api_success(
        {
            "record_id": record_id,
            "session_id": payload.get("session_id"),
            "flow_session_id": flow_session.get("flow_session_id") if flow_session else flow_session_id,
            "use_time": use_time,
            "scale": _serialize_scale_definition(scale_def, include_items=False),
            "result": result,
            "flow_session": flow_session,
        }
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/result/<int:record_id>", methods=["GET"])
def scale_api_result(record_id):
    record = get_scale_record(record_id)
    if not record:
        return api_error(4004, "未找到该量表结果", status_code=404)

    userinfo, _, current_name = _get_current_identity()
    is_admin = str(userinfo.get("role", "")) in {"1", "2"}
    if not is_admin and record["username"] != current_name:
        return api_error(4003, "你无权查看该量表结果", status_code=401)

    scale_def = get_scale_definition(record["scale_slug"])
    if not scale_def:
        return api_error(5001, "量表定义不存在，无法返回结果", status_code=500)

    return api_success(
        {
            "record": _serialize_scale_record(record),
            "scale": _serialize_scale_definition(scale_def, include_items=True),
        }
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/latest", methods=["GET"])
def scale_api_latest():
    _, user_id, username = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    items = [
        _serialize_scale_record(record)
        for record in get_latest_scale_records(user_id=user_id, username=username)
    ]
    return api_success(
        {
            "items": items,
            "pagination": {
                "page": 1,
                "page_size": len(items),
                "total": len(items),
                "has_more": False,
            },
        }
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/draft/<scale_slug>", methods=["GET"])
def scale_api_draft_detail(scale_slug):
    _, user_id, _ = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    normalized_scale_slug = _normalize_scale_slug(scale_slug)
    if not normalized_scale_slug:
        return api_error(4001, "缺少有效的 scale_slug", status_code=400)

    flow_session_id = _extract_flow_session_id(request.args.to_dict())
    if flow_session_id:
        try:
            get_flow_session_for_user(flow_session_id, user_id=user_id)
        except FlowSessionError as exc:
            return api_error(4004, str(exc), status_code=404)

    draft = get_scale_draft(
        user_id=user_id,
        scale_slug=normalized_scale_slug,
        flow_session_id=flow_session_id,
    )
    return api_success({"draft": _serialize_scale_draft(draft)})


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/draft/save", methods=["POST"])
def scale_api_save_draft():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error(4001, "请求体必须为 JSON 对象", status_code=400)

    _, user_id, username = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    scale_slug = _normalize_scale_slug(payload.get("scale_slug") or payload.get("scale_type"))
    if not scale_slug:
        return api_error(4001, "缺少必填字段: scale_slug", status_code=400)

    scale_def = get_scale_definition(scale_slug)
    if not scale_def:
        return api_error(4004, "暂不支持该量表类型", status_code=404)

    flow_session_id = _extract_flow_session_id(payload)
    if flow_session_id:
        try:
            get_flow_session_for_user(flow_session_id, user_id=user_id)
        except FlowSessionError as exc:
            return api_error(4004, str(exc), status_code=404)

    try:
        raw_answers = _extract_answers(payload.get("answers") or {})
        normalized_answers = {
            str(question_id): int(answer_value)
            for question_id, answer_value in raw_answers.items()
            if answer_value not in (None, "")
        }
    except (ScaleValidationError, TypeError, ValueError) as exc:
        return api_error(4002, f"草稿答案格式无效: {exc}", status_code=400)

    answered_count = sum(
        1 for item in scale_def["items"] if str(item["id"]) in normalized_answers
    )

    try:
        normalized_current_item_index = max(0, int(payload.get("current_item_index") or 0))
    except (TypeError, ValueError):
        normalized_current_item_index = 0

    try:
        normalized_started_at = (
            int(payload.get("started_at"))
            if payload.get("started_at") not in (None, "")
            else None
        )
    except (TypeError, ValueError):
        normalized_started_at = None

    try:
        normalized_use_time = max(0, int(payload.get("use_time") or 0))
    except (TypeError, ValueError):
        normalized_use_time = 0

    draft = upsert_scale_draft(
        user_id=user_id,
        username=username,
        scale_slug=scale_slug,
        flow_session_id=flow_session_id,
        answers=normalized_answers,
        answered_count=answered_count,
        current_item_index=normalized_current_item_index,
        started_at=normalized_started_at,
        saved_use_time=normalized_use_time,
    )

    flow_session = None
    if flow_session_id:
        try:
            flow_session = save_flow_draft(
                flow_session_id,
                user_id=user_id,
                scale_slug=scale_slug,
                draft_payload={
                    "answered_count": answered_count,
                    "current_item_index": normalized_current_item_index,
                    "started_at": normalized_started_at,
                    "saved_use_time": normalized_use_time,
                },
            )
        except FlowSessionError as exc:
            return api_error(4004, str(exc), status_code=404)

    return api_success(
        {
            "draft": _serialize_scale_draft(draft),
            "flow_session": flow_session,
        }
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/health", methods=["GET"])
def scale_api_health():
    return api_health(
        mode="prod",
        model_loaded=True,
        extra={
            "storage_ready": True,
            "available_scales": [scale["slug"] for scale in list_scale_definitions()],
        },
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/meta", methods=["GET"])
def scale_api_meta():
    return api_meta(
        module="assessment",
        capability="scale-screening",
        module_zh="量表评估模块",
        capability_zh="结构化量表筛查能力",
        owner="team-assessment",
        supports_mock=True,
        extra={
            "available_scales": [
                _serialize_scale_definition(scale_def, include_items=False)
                for scale_def in list_scale_definitions()
            ],
            "implemented_actions": [
                "list",
                "submit",
                "result",
                "latest",
                "draft.get",
                "draft.save",
                "flow_session.start",
                "flow_session.current",
                "flow_session.detail",
                "flow_session.risk_payload_preview",
                "flow_session.draft",
                "flow_session.attach_sds",
                "flow_session.finalize_risk",
                "health",
                "meta",
            ],
        },
    )


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/flow-session/start", methods=["POST"])
def scale_flow_start():
    payload = request.get_json(silent=True) or {}
    if payload and not isinstance(payload, dict):
        return api_error(4001, "请求体必须为 JSON 对象", status_code=400)

    _, user_id, username = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    recommended_order = payload.get("recommended_order")
    if recommended_order is not None and not isinstance(recommended_order, list):
        return api_error(4002, "recommended_order 必须是数组", status_code=400)

    try:
        flow_session = start_or_resume_flow_session(
            user_id=user_id,
            username=username,
            recommended_order=recommended_order,
        )
    except FlowSessionError as exc:
        return api_error(5001, str(exc), status_code=500)

    return api_success({"flow_session": flow_session})


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/flow-session/current", methods=["GET"])
def scale_flow_current():
    _, user_id, _ = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    flow_session = get_current_flow_session(user_id=user_id)
    return api_success({"flow_session": flow_session})


@scale_assessment_bp.route("/api/v1/assessment/scale-screening/flow-session/<flow_session_id>", methods=["GET"])
def scale_flow_detail(flow_session_id):
    _, user_id, _ = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    try:
        flow_session = serialize_flow_session(
            get_flow_session_for_user(flow_session_id, user_id=user_id)
        )
    except FlowSessionError as exc:
        return api_error(4004, str(exc), status_code=404)

    return api_success({"flow_session": flow_session})


@scale_assessment_bp.route(
    "/api/v1/assessment/scale-screening/flow-session/<flow_session_id>/risk-payload-preview",
    methods=["GET", "POST"],
)
def scale_flow_risk_payload_preview(flow_session_id):
    _, user_id, _ = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    try:
        payload = _extract_optional_preview_body()
        flow = get_flow_session_for_user(flow_session_id, user_id=user_id)
        risk_payload = build_flow_risk_payload(
            flow,
            trigger_reason=str(payload.get("trigger_reason") or "debug_preview").strip(),
            text_summary=payload.get("text_summary"),
            speech_summary=payload.get("speech_summary"),
            emotion_summary=payload.get("emotion_summary"),
            eeg_summary=payload.get("eeg_summary"),
        )
        flow_session = serialize_flow_session(flow)
    except FlowSessionError as exc:
        return api_error(4004, str(exc), status_code=404)
    except ScaleValidationError as exc:
        return api_error(4001, str(exc), status_code=400)

    return api_success(
        {
            "flow_session": flow_session,
            "risk_payload": risk_payload,
            "preview_notes": {
                "readonly": True,
                "evaluation_executed": False,
                "supports_modal_overrides": True,
                "description": "该接口仅预览送入 risk-assessment 的输入体，不会真正执行风险评估。",
            },
        }
    )


@scale_assessment_bp.route(
    "/api/v1/assessment/scale-screening/flow-session/<flow_session_id>/draft",
    methods=["POST"],
)
def scale_flow_save_draft(flow_session_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error(4001, "请求体必须为 JSON 对象", status_code=400)

    _, user_id, _ = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    scale_slug = _normalize_scale_slug(payload.get("scale_slug"))
    if not scale_slug:
        return api_error(4001, "缺少必填字段: scale_slug", status_code=400)

    try:
        flow_session = save_flow_draft(
            flow_session_id,
            user_id=user_id,
            scale_slug=scale_slug,
            draft_payload=payload.get("draft_payload") or {},
        )
    except FlowSessionError as exc:
        return api_error(4004, str(exc), status_code=404)

    return api_success({"flow_session": flow_session})


@scale_assessment_bp.route(
    "/api/v1/assessment/scale-screening/flow-session/<flow_session_id>/attach-sds",
    methods=["POST"],
)
def scale_flow_attach_sds(flow_session_id):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return api_error(4001, "请求体必须为 JSON 对象", status_code=400)

    _, user_id, _ = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    sds_record_id = payload.get("sds_record_id") or payload.get("record_id")
    if sds_record_id in (None, ""):
        latest_sds = session.get("test_id")
        if latest_sds in (None, ""):
            latest_row = db.fetch_one(
                """
                SELECT id
                FROM test
                WHERE user_id = ? AND status = '已完成'
                ORDER BY finish_time DESC, id DESC
                LIMIT 1
                """,
                [user_id],
            )
            latest_sds = latest_row.get("id") if latest_row else None
        sds_record_id = latest_sds
    if sds_record_id in (None, ""):
        return api_error(4001, "缺少必填字段: sds_record_id", status_code=400)

    try:
        flow_session = attach_sds_completion(
            flow_session_id,
            user_id=user_id,
            sds_record_id=int(sds_record_id),
        )
    except (FlowSessionError, ValueError) as exc:
        return api_error(4004, str(exc), status_code=404)

    return api_success({"flow_session": flow_session})


@scale_assessment_bp.route(
    "/api/v1/assessment/scale-screening/flow-session/<flow_session_id>/finalize-risk",
    methods=["POST"],
)
def scale_flow_finalize_risk(flow_session_id):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return api_error(4001, "请求体必须为 JSON 对象", status_code=400)

    _, user_id, _ = _get_current_identity()
    if not user_id:
        return api_error(4003, "用户未登录或鉴权失败", status_code=401)

    trigger_reason = str(payload.get("trigger_reason") or "manual_finalize").strip()
    try:
        result = finalize_flow_risk_assessment(
            flow_session_id,
            user_id=user_id,
            trigger_reason=trigger_reason,
            text_summary=payload.get("text_summary"),
            speech_summary=payload.get("speech_summary"),
            emotion_summary=payload.get("emotion_summary"),
            eeg_summary=payload.get("eeg_summary"),
        )
    except FlowSessionError as exc:
        return api_error(4002, str(exc), status_code=400)
    except RiskAssessmentValidationError as exc:
        return api_error(exc.code, str(exc), status_code=400, data=exc.data)
    except Exception as exc:  # pragma: no cover - defensive boundary
        logger.exception("finalize flow risk assessment failed")
        return api_error(5001, f"风险评估流程服务内部异常: {exc}", status_code=500)

    body = {
        "flow_session": result["flow_session"],
        "result": result["result"],
    }
    if result["advisory_code"]:
        return api_notice(result["advisory_code"], result["advisory_message"], data=body)
    return api_success(body)
