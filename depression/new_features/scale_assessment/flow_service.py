"""Service helpers for unified scale screening flow sessions."""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from utils import db

from new_features.assessment_context.service import serialize_sds_record
from new_features.risk_assessment.engine import evaluate_risk_assessment

from .flow_repository import (
    create_flow_session,
    ensure_flow_tables,
    get_active_flow_session,
    get_flow_session,
    update_flow_session,
)
from .repository import get_scale_record

DEFAULT_RECOMMENDED_ORDER = ["phq9", "gad7", "sds"]
SUPPORTED_FLOW_SCALES = set(DEFAULT_RECOMMENDED_ORDER)

ensure_flow_tables()


class FlowSessionError(ValueError):
    """Raised when flow session actions cannot be completed."""


def start_or_resume_flow_session(
    *,
    user_id: int,
    username: str,
    recommended_order: Optional[List[str]] = None,
) -> Dict[str, Any]:
    active = get_active_flow_session(user_id=user_id)
    if active:
        return serialize_flow_session(active)

    normalized_recommended_order = _normalize_recommended_order(recommended_order)
    flow_session_id = create_flow_session(
        user_id=user_id,
        username=username,
        recommended_order=normalized_recommended_order,
    )
    created = get_flow_session(flow_session_id, user_id=user_id)
    if not created:
        raise FlowSessionError("创建量表流程会话失败")
    return serialize_flow_session(created)


def get_current_flow_session(*, user_id: int) -> Optional[Dict[str, Any]]:
    active = get_active_flow_session(user_id=user_id)
    if not active:
        return None
    return serialize_flow_session(active)


def get_flow_session_for_user(flow_session_id: str, *, user_id: int) -> Dict[str, Any]:
    flow = get_flow_session(flow_session_id, user_id=user_id)
    if not flow:
        raise FlowSessionError("未找到对应的量表流程会话")
    return flow


def save_flow_draft(
    flow_session_id: str,
    *,
    user_id: int,
    scale_slug: str,
    draft_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    flow = get_flow_session_for_user(flow_session_id, user_id=user_id)
    draft_scales = _append_unique(flow["draft_scales"], scale_slug)
    draft_state = dict(flow["draft_state"] or {})
    draft_state[scale_slug] = {
        "saved_at": _now_iso(),
        **(draft_payload or {}),
    }
    update_flow_session(
        flow_session_id,
        user_id=user_id,
        draft_scales=draft_scales,
        draft_state=draft_state,
    )
    return serialize_flow_session(get_flow_session_for_user(flow_session_id, user_id=user_id))


def mark_structured_scale_completed(
    flow_session_id: str,
    *,
    user_id: int,
    scale_slug: str,
    record_id: int,
) -> Dict[str, Any]:
    flow = get_flow_session_for_user(flow_session_id, user_id=user_id)
    completed_scales = _append_unique(flow["completed_scales"], scale_slug)
    draft_scales = [item for item in flow["draft_scales"] if item != scale_slug]
    draft_state = dict(flow["draft_state"] or {})
    draft_state.pop(scale_slug, None)
    links = dict(flow["scale_record_links"] or {})
    links[scale_slug] = {
        "record_id": int(record_id),
        "source": "scale_assessment_records",
        "attached_at": _now_iso(),
    }
    update_flow_session(
        flow_session_id,
        user_id=user_id,
        completed_scales=completed_scales,
        draft_scales=draft_scales,
        draft_state=draft_state,
        scale_record_links=links,
    )
    return serialize_flow_session(get_flow_session_for_user(flow_session_id, user_id=user_id))


def attach_sds_completion(
    flow_session_id: str,
    *,
    user_id: int,
    sds_record_id: int,
) -> Dict[str, Any]:
    flow = get_flow_session_for_user(flow_session_id, user_id=user_id)
    sds_record = db.fetch_one(
        """
        SELECT *
        FROM test
        WHERE id = ? AND user_id = ? AND status = '已完成'
        """,
        [sds_record_id, user_id],
    )
    if not sds_record:
        raise FlowSessionError("未找到可挂接的 SDS 已完成记录")

    completed_scales = _append_unique(flow["completed_scales"], "sds")
    draft_scales = [item for item in flow["draft_scales"] if item != "sds"]
    draft_state = dict(flow["draft_state"] or {})
    draft_state.pop("sds", None)
    links = dict(flow["scale_record_links"] or {})
    links["sds"] = {
        "record_id": int(sds_record_id),
        "source": "legacy_sds_test",
        "attached_at": _now_iso(),
    }
    update_flow_session(
        flow_session_id,
        user_id=user_id,
        completed_scales=completed_scales,
        draft_scales=draft_scales,
        draft_state=draft_state,
        scale_record_links=links,
    )
    return serialize_flow_session(get_flow_session_for_user(flow_session_id, user_id=user_id))


def finalize_flow_risk_assessment(
    flow_session_id: str,
    *,
    user_id: int,
    trigger_reason: str,
    text_summary: Optional[Dict[str, Any]] = None,
    speech_summary: Optional[Dict[str, Any]] = None,
    emotion_summary: Optional[Dict[str, Any]] = None,
    eeg_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    flow = get_flow_session_for_user(flow_session_id, user_id=user_id)
    if not flow["completed_scales"]:
        raise FlowSessionError("至少完成 1 份完整量表后，才能生成风险评估")

    payload = build_flow_risk_payload(
        flow,
        trigger_reason=trigger_reason,
        text_summary=text_summary,
        speech_summary=speech_summary,
        emotion_summary=emotion_summary,
        eeg_summary=eeg_summary,
    )
    result = evaluate_risk_assessment(payload)
    result_dict = result.to_result_dict()

    update_flow_session(
        flow_session_id,
        user_id=user_id,
        status="risk_generated",
        last_risk_result={
            "result": result_dict,
            "advisory_code": result.advisory_code,
            "advisory_message": result.advisory_message,
            "generated_at": _now_iso(),
        },
        risk_assessment_generated=True,
        latest_trigger_reason=trigger_reason,
        finished_at=_now_iso(),
    )
    updated = get_flow_session_for_user(flow_session_id, user_id=user_id)
    return {
        "flow_session": serialize_flow_session(updated),
        "result": result_dict,
        "advisory_code": result.advisory_code,
        "advisory_message": result.advisory_message,
    }


def build_flow_risk_payload(
    flow: Dict[str, Any],
    *,
    trigger_reason: Optional[str] = None,
    text_summary: Optional[Dict[str, Any]] = None,
    speech_summary: Optional[Dict[str, Any]] = None,
    emotion_summary: Optional[Dict[str, Any]] = None,
    eeg_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    assessment_bundle = build_assessment_bundle_from_flow(flow)
    if not assessment_bundle:
        raise FlowSessionError("当前流程中没有可用于风险评估的完整量表结果")

    sds_emotion_summary = _derive_emotion_summary_from_bundle(assessment_bundle)
    sds_eeg_summary = _derive_eeg_summary_from_bundle(assessment_bundle)
    completed_scales = list(flow.get("completed_scales") or [])
    recommended_order = list(flow.get("recommended_order") or DEFAULT_RECOMMENDED_ORDER)
    return {
        "user_id": flow["user_id"],
        "flow_session_id": flow["flow_session_id"],
        "assessment_bundle": assessment_bundle,
        "text_summary": text_summary or {"available": False},
        "speech_summary": speech_summary or {"available": False},
        "emotion_summary": emotion_summary or sds_emotion_summary or {"available": False},
        "eeg_summary": eeg_summary or sds_eeg_summary or {"available": False},
        "decision_context": {
            "trigger_reason": trigger_reason or flow.get("latest_trigger_reason"),
            "flow_status": flow.get("status"),
            "completed_scales": completed_scales,
            "recommended_order": recommended_order,
        },
        "completion_state": {
            "completed_scales": completed_scales,
            "completed_scale_count": len(completed_scales),
            "is_partial": bool(completed_scales) and len(completed_scales) < len(recommended_order),
            "is_recommended_flow_complete": all(
                slug in completed_scales for slug in recommended_order
            ),
        },
    }


def build_assessment_bundle_from_flow(flow: Dict[str, Any]) -> Dict[str, Any]:
    links = flow.get("scale_record_links") or {}
    bundle: Dict[str, Any] = {}

    phq9_link = links.get("phq9")
    if phq9_link:
        record = get_scale_record(int(phq9_link["record_id"]))
        if record and record.get("user_id") == flow["user_id"]:
            bundle["phq9_summary"] = _scale_record_to_summary(record)

    gad7_link = links.get("gad7")
    if gad7_link:
        record = get_scale_record(int(gad7_link["record_id"]))
        if record and record.get("user_id") == flow["user_id"]:
            bundle["gad7_summary"] = _scale_record_to_summary(record)

    sds_link = links.get("sds")
    if sds_link:
        sds_row = db.fetch_one(
            """
            SELECT *
            FROM test
            WHERE id = ? AND user_id = ? AND status = '已完成'
            """,
            [int(sds_link["record_id"]), flow["user_id"]],
        )
        sds_payload = serialize_sds_record(sds_row)
        if sds_payload:
            bundle["sds_summary"] = _sds_payload_to_summary(sds_payload)

    return bundle


def serialize_flow_session(flow: Dict[str, Any]) -> Dict[str, Any]:
    completed_scales = list(flow.get("completed_scales") or [])
    recommended_order = list(flow.get("recommended_order") or DEFAULT_RECOMMENDED_ORDER)
    remaining_scales = [slug for slug in recommended_order if slug not in completed_scales]
    current_scale = remaining_scales[0] if remaining_scales else None
    return {
        "flow_session_id": flow["flow_session_id"],
        "user_id": flow["user_id"],
        "username": flow["username"],
        "status": flow["status"],
        "recommended_order": recommended_order,
        "completed_scales": completed_scales,
        "draft_scales": list(flow.get("draft_scales") or []),
        "draft_state": flow.get("draft_state") or {},
        "scale_record_links": flow.get("scale_record_links") or {},
        "current_scale_slug": current_scale,
        "remaining_scales": remaining_scales,
        "risk_assessment_generated": bool(flow.get("risk_assessment_generated")),
        "latest_trigger_reason": flow.get("latest_trigger_reason"),
        "last_risk_result": flow.get("last_risk_result"),
        "created_at": flow.get("created_at"),
        "updated_at": flow.get("updated_at"),
        "finished_at": flow.get("finished_at"),
    }


def _scale_record_to_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    answers = record.get("answers") or {}
    self_harm_item_score = None
    if record.get("scale_slug") == "phq9":
        q9_value = answers.get("q9")
        try:
            self_harm_item_score = int(q9_value)
        except (TypeError, ValueError):
            self_harm_item_score = None

    return {
        "available": True,
        "source": "scale_assessment_records",
        "record_id": record.get("id"),
        "scale_type": record.get("scale_code") or record.get("scale_slug"),
        "scale_slug": record.get("scale_slug"),
        "total_score": record.get("total_score"),
        "severity": record.get("severity_key"),
        "severity_label": record.get("severity_label"),
        "self_harm_item_score": self_harm_item_score,
        "summary": record.get("summary"),
        "interpretation": record.get("interpretation"),
        "risk_flags": record.get("risk_flags") or [],
    }


def _sds_payload_to_summary(sds_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "available": True,
        "source": "legacy_sds_test",
        "record_id": sds_payload.get("record_id"),
        "scale_type": "SDS",
        "scale_slug": "sds",
        "total_score": sds_payload.get("score"),
        "severity": sds_payload.get("result"),
        "severity_label": sds_payload.get("result"),
        "summary": f"SDS 标准分 {sds_payload.get('score')}，判定为{sds_payload.get('result')}",
        "comprehensive_score": sds_payload.get("comprehensive_score"),
        "comprehensive_result": sds_payload.get("comprehensive_result"),
    }


def _derive_emotion_summary_from_bundle(bundle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sds_summary = bundle.get("sds_summary") or {}
    comprehensive_result = sds_summary.get("comprehensive_result") or {}
    components = comprehensive_result.get("components") or {}
    emotion_component = components.get("emotion_details") or {}
    if emotion_component.get("available") is False:
        return None
    emotion_score = emotion_component.get("emotion_score") or components.get("emotion_score")
    if emotion_score in (None, ""):
        return None

    details = emotion_component.get("details") or {}
    if int(details.get("total_detections") or 0) <= 0:
        return None

    return {
        "available": True,
        "source": "legacy_sds_emotion_bridge",
        "score": emotion_score,
        "confidence": _confidence_level_to_numeric(emotion_component.get("confidence_level")),
        "summary": emotion_component.get("analysis") or "基于 SDS 旧链路的表情摘要已参与风险评估",
    }


def _derive_eeg_summary_from_bundle(bundle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sds_summary = bundle.get("sds_summary") or {}
    comprehensive_result = sds_summary.get("comprehensive_result") or {}
    components = comprehensive_result.get("components") or {}
    eeg_component = components.get("eeg_details") or {}
    if eeg_component.get("available") is False:
        return None
    eeg_score = eeg_component.get("eeg_score") or components.get("eeg_score")
    if eeg_score in (None, ""):
        return None

    details = eeg_component.get("details") or {}
    if details.get("source") == "simulated":
        return None

    return {
        "available": True,
        "source": "legacy_sds_eeg_bridge",
        "score": eeg_score,
        "confidence": _confidence_level_to_numeric(eeg_component.get("confidence_level")),
        "summary": eeg_component.get("analysis") or "基于 SDS 旧链路的脑电摘要已参与风险评估",
    }


def _confidence_level_to_numeric(value: object) -> float:
    mapping = {
        "low": 0.4,
        "medium": 0.7,
        "high": 0.9,
        "低": 0.4,
        "中": 0.7,
        "高": 0.9,
    }
    key = str(value or "").strip().lower()
    return mapping.get(key, 0.6)


def _append_unique(items: List[str], value: str) -> List[str]:
    normalized = [item for item in items if item]
    if value not in normalized:
        normalized.append(value)
    return normalized


def _normalize_recommended_order(recommended_order: Optional[List[str]]) -> List[str]:
    if not recommended_order:
        return list(DEFAULT_RECOMMENDED_ORDER)

    normalized: List[str] = []
    for value in recommended_order:
        slug = str(value or "").strip().lower()
        if not slug or slug not in SUPPORTED_FLOW_SCALES:
            continue
        if slug not in normalized:
            normalized.append(slug)

    if not normalized:
        return list(DEFAULT_RECOMMENDED_ORDER)
    return normalized


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(sep=" ", timespec="seconds")
