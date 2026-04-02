"""Assessment-dominant scoring engine for risk assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from . import rules


class RiskAssessmentValidationError(ValueError):
    """Raised when the risk assessment payload is invalid."""

    def __init__(self, message: str, *, code: int = 4002, data: Optional[Dict[str, object]] = None):
        super().__init__(message)
        self.code = code
        self.data = data or {}


@dataclass
class RiskAssessmentResult:
    risk_level: str
    risk_score: int
    severity_band: str
    referral_recommended: bool
    emergency_notice: bool
    allow_continue: bool
    recommended_next_step: str
    assessment_confidence: float
    triggered_rules: List[Dict[str, str]]
    evidence_summary: List[Dict[str, str]]
    contributions: Dict[str, float]
    safety_advice: Dict[str, object]
    threshold_snapshot: Dict[str, object]
    advisory_code: int = 0
    advisory_message: str = "ok"

    def to_result_dict(self) -> Dict[str, object]:
        return {
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "severity_band": self.severity_band,
            "referral_recommended": self.referral_recommended,
            "emergency_notice": self.emergency_notice,
            "allow_continue": self.allow_continue,
            "recommended_next_step": self.recommended_next_step,
            "assessment_confidence": self.assessment_confidence,
            "triggered_rules": self.triggered_rules,
            "evidence_summary": self.evidence_summary,
            "contributions": self.contributions,
            "safety_advice": self.safety_advice,
            "threshold_snapshot": self.threshold_snapshot,
        }


def _ensure_mapping(payload: object, *, field_name: str) -> Dict[str, object]:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise RiskAssessmentValidationError(
            f"{field_name} 必须是对象",
            code=4002,
            data={"field": field_name},
        )
    return payload


def _text_blob(summary: Dict[str, object]) -> str:
    parts: List[str] = []
    summary_text = summary.get("summary")
    if isinstance(summary_text, str):
        parts.append(summary_text)
    label = summary.get("label")
    if isinstance(label, str):
        parts.append(label)
    keywords = summary.get("keywords")
    if isinstance(keywords, list):
        parts.extend(str(item) for item in keywords if item not in (None, ""))
    return " ".join(parts)


def _has_assessment_signal(summary: Dict[str, object]) -> bool:
    if not isinstance(summary, dict) or not summary:
        return False
    if summary.get("available") is True:
        return True
    if summary.get("total_score") not in (None, ""):
        return True
    if summary.get("score") not in (None, ""):
        return True
    if summary.get("severity") or summary.get("severity_key") or summary.get("severity_label"):
        return True
    return False


def _normalize_bundle_summary(raw_summary: object, *, field_name: str, scale_type: str) -> Dict[str, object]:
    summary = _ensure_mapping(raw_summary, field_name=field_name)
    if summary and "available" not in summary:
        summary = dict(summary)
        summary["available"] = _has_assessment_signal(summary)
    elif not summary:
        summary = {"available": False}
    if summary.get("available") and not summary.get("scale_type"):
        summary = dict(summary)
        summary["scale_type"] = scale_type
    return summary


def _aggregate_assessment_bundle(bundle_payload: object) -> tuple[Dict[str, object], Dict[str, Dict[str, object]]]:
    bundle = _ensure_mapping(bundle_payload, field_name="assessment_bundle")
    normalized_bundle = {
        "phq9_summary": _normalize_bundle_summary(
            bundle.get("phq9_summary"),
            field_name="assessment_bundle.phq9_summary",
            scale_type="PHQ-9",
        ),
        "gad7_summary": _normalize_bundle_summary(
            bundle.get("gad7_summary"),
            field_name="assessment_bundle.gad7_summary",
            scale_type="GAD-7",
        ),
        "sds_summary": _normalize_bundle_summary(
            bundle.get("sds_summary"),
            field_name="assessment_bundle.sds_summary",
            scale_type="SDS",
        ),
    }

    available_summaries = [
        summary for summary in normalized_bundle.values() if summary.get("available")
    ]
    if not available_summaries:
        raise RiskAssessmentValidationError(
            "assessment_bundle 中至少需要 1 个完整量表结果",
            code=4002,
            data={"field": "assessment_bundle"},
        )

    overall_band = "low"
    overall_score = 0
    self_harm_score = None
    detail_parts: List[str] = []
    available_scales: List[str] = []

    for summary in available_summaries:
        band = rules.assessment_band(summary) or "low"
        score = rules.assessment_score(summary)
        overall_band = rules.band_at_least(overall_band, band)
        if score is not None:
            overall_score = max(overall_score, int(round(score)))

        scale_type = str(summary.get("scale_type") or summary.get("scale_slug") or "").strip() or "UNKNOWN"
        available_scales.append(scale_type)
        detail_label = summary.get("severity_label") or summary.get("severity") or band
        raw_score = summary.get("total_score")
        if raw_score not in (None, ""):
            detail_parts.append(f"{scale_type} {raw_score}分（{detail_label}）")
        else:
            detail_parts.append(f"{scale_type} 已纳入评估（{detail_label}）")

        candidate_self_harm = rules.self_harm_item_score(summary)
        if candidate_self_harm is not None:
            self_harm_score = max(self_harm_score or 0, candidate_self_harm)

    overall_score = max(overall_score, rules.min_score_for_band(overall_band))
    aggregated_summary = {
        "available": True,
        "scale_type": "ASSESSMENT_BUNDLE",
        "severity": overall_band,
        "severity_label": overall_band,
        "score": overall_score,
        "self_harm_item_score": self_harm_score,
        "summary": "；".join(detail_parts),
        "available_scales": available_scales,
    }
    return aggregated_summary, normalized_bundle


def _normalize_payload(payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    if not isinstance(payload, dict):
        raise RiskAssessmentValidationError("请求体必须为 JSON 对象", code=4001)

    user_id = payload.get("user_id")
    if user_id in (None, ""):
        raise RiskAssessmentValidationError(
            "缺少必填字段: user_id",
            code=4001,
            data={"field": "user_id"},
        )

    assessment_bundle_payload = payload.get("assessment_bundle")
    assessment_bundle = {}
    if assessment_bundle_payload is not None:
        assessment_summary, assessment_bundle = _aggregate_assessment_bundle(assessment_bundle_payload)
    else:
        assessment_summary = payload.get("assessment_summary")
        if assessment_summary is None:
            raise RiskAssessmentValidationError(
                "缺少必填字段: assessment_summary 或 assessment_bundle",
                code=4001,
                data={"field": "assessment_summary"},
            )

        assessment_summary = _ensure_mapping(assessment_summary, field_name="assessment_summary")
        assessment_score_value = assessment_summary.get("total_score")
        if assessment_score_value in (None, ""):
            assessment_score_value = assessment_summary.get("score")
        if assessment_summary.get("available") and assessment_score_value in (None, ""):
            raise RiskAssessmentValidationError(
                "assessment_summary.total_score 或 assessment_summary.score 在 available=true 时为必填",
                code=4002,
                data={"field": "assessment_summary.total_score"},
            )

    return {
        "assessment": assessment_summary,
        "assessment_bundle": assessment_bundle,
        "text": _ensure_mapping(payload.get("text_summary"), field_name="text_summary"),
        "speech": _ensure_mapping(payload.get("speech_summary"), field_name="speech_summary"),
        "emotion": _ensure_mapping(payload.get("emotion_summary"), field_name="emotion_summary"),
        "eeg": _ensure_mapping(payload.get("eeg_summary"), field_name="eeg_summary"),
    }


def _build_contributions(source_scores: Dict[str, Optional[float]]) -> Dict[str, float]:
    active_weights = {
        source: weight
        for source, weight in rules.BASE_WEIGHTS.items()
        if source_scores.get(source) is not None
    }
    total_weight = sum(active_weights.values())
    if total_weight <= 0:
        return {source: 0.0 for source in rules.BASE_WEIGHTS}

    normalized = {
        source: round(weight / total_weight, 2)
        for source, weight in active_weights.items()
    }
    for source in rules.BASE_WEIGHTS:
        normalized.setdefault(source, 0.0)
    return normalized


def _build_evidence(source_name: str, summary: Dict[str, object], score: Optional[float]) -> Optional[Dict[str, str]]:
    if score is None:
        return None

    summary_text = str(summary.get("summary") or "").strip()
    if not summary_text:
        if source_name == "assessment":
            summary_text = "量表结果已参与初步风险分层"
        else:
            summary_text = "该模态结果已参与初步风险分层"

    return {
        "source": source_name,
        "signal": f"{source_name}_signal",
        "detail": summary_text,
    }


def _base_band_and_score(assessment_summary: Dict[str, object]) -> tuple[str, int]:
    base_score = rules.assessment_score(assessment_summary)
    base_band = rules.assessment_band(assessment_summary)

    if base_score is None:
        return "low", 0

    numeric_score = int(round(base_score))
    if base_band is None:
        base_band = rules.band_from_score(numeric_score)
    numeric_score = max(numeric_score, rules.min_score_for_band(base_band))
    return base_band, numeric_score


def _confidence(source_summaries: Dict[str, Dict[str, object]], source_scores: Dict[str, Optional[float]]) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for source, weight in rules.BASE_WEIGHTS.items():
        if source_scores.get(source) is None:
            continue
        confidence = rules.normalize_confidence(source_summaries[source].get("confidence"), default=0.7)
        weighted_sum += confidence * weight
        total_weight += weight

    if total_weight <= 0:
        return 0.5
    return round(weighted_sum / total_weight, 2)


def _evaluate_hard_rules(source_summaries: Dict[str, Dict[str, object]]) -> tuple[str, List[Dict[str, str]], List[Dict[str, str]]]:
    triggered_rules: List[Dict[str, str]] = []
    evidence_summary: List[Dict[str, str]] = []
    forced_band = "low"

    assessment_summary = source_summaries["assessment"]
    self_harm_score = rules.self_harm_item_score(assessment_summary)
    if self_harm_score is not None:
        if self_harm_score >= 2:
            forced_band = rules.band_at_least(forced_band, "urgent")
            triggered_rules.append(
                {
                    "rule_id": "self_harm_item_score_urgent",
                    "reason": "PHQ-9 第9题达到中高频阳性，触发紧急风险提示",
                }
            )
            evidence_summary.append(
                {
                    "source": "assessment",
                    "signal": "self_harm_item_score_urgent",
                    "detail": f"PHQ-9 第9题得分为 {self_harm_score}，达到紧急提示阈值",
                }
            )
        elif self_harm_score >= 1:
            forced_band = rules.band_at_least(forced_band, "high")
            triggered_rules.append(
                {
                    "rule_id": "self_harm_item_score_high",
                    "reason": "PHQ-9 第9题出现阳性，至少进入高风险安全提醒",
                }
            )
            evidence_summary.append(
                {
                    "source": "assessment",
                    "signal": "self_harm_item_score_high",
                    "detail": f"PHQ-9 第9题得分为 {self_harm_score}，达到高风险安全提醒阈值",
                }
            )

    combined_text_parts = []
    for source_name in ("assessment", "text", "speech", "emotion"):
        combined_text_parts.append(_text_blob(source_summaries[source_name]))
    combined_text = " ".join(part for part in combined_text_parts if part)

    urgent_keyword = rules.contains_keywords(combined_text, rules.URGENT_KEYWORDS)
    if urgent_keyword:
        forced_band = rules.band_at_least(forced_band, "urgent")
        triggered_rules.append(
            {
                "rule_id": "urgent_keyword_detected",
                "reason": f"检测到紧急风险关键词: {urgent_keyword}",
            }
        )
        evidence_summary.append(
            {
                "source": "text",
                "signal": "urgent_keyword_detected",
                "detail": f"检测到紧急风险关键词“{urgent_keyword}”",
            }
        )

    high_keyword = rules.contains_keywords(combined_text, rules.HIGH_RISK_KEYWORDS)
    if high_keyword and forced_band != "urgent":
        forced_band = rules.band_at_least(forced_band, "high")
        triggered_rules.append(
            {
                "rule_id": "high_risk_keyword_detected",
                "reason": f"检测到高风险关键词: {high_keyword}",
            }
        )
        evidence_summary.append(
            {
                "source": "text",
                "signal": "high_risk_keyword_detected",
                "detail": f"检测到高风险关键词“{high_keyword}”",
            }
        )

    return forced_band, triggered_rules, evidence_summary


def _evaluate_multimodal_uplift(
    source_summaries: Dict[str, Dict[str, object]],
    current_band: str,
) -> tuple[str, List[Dict[str, str]], List[Dict[str, str]]]:
    if current_band == "urgent":
        return current_band, [], []

    support_modalities = []
    for source_name in ("text", "speech", "emotion", "eeg"):
        if rules.is_high_support_signal(source_summaries[source_name]):
            support_modalities.append(source_name)

    if len(support_modalities) < rules.NON_ASSESSMENT_UPLIFT_COUNT:
        return current_band, [], []

    uplifted_band = rules.next_band(current_band, maximum=rules.NON_ASSESSMENT_MAX_TARGET_BAND)
    if uplifted_band == current_band:
        return current_band, [], []

    joined = "、".join(support_modalities)
    triggered_rules = [
        {
            "rule_id": "multimodal_support_uplift",
            "reason": f"{joined} 同时达到高异常阈值，触发多模态保守升档",
        }
    ]
    evidence_summary = [
        {
            "source": "multimodal",
            "signal": "multimodal_support_uplift",
            "detail": f"{joined} 同时满足高异常且高置信度条件，风险升高 1 档",
        }
    ]
    return uplifted_band, triggered_rules, evidence_summary


def evaluate_risk_assessment(payload: Dict[str, object]) -> RiskAssessmentResult:
    source_summaries = _normalize_payload(payload)

    source_scores: Dict[str, Optional[float]] = {
        "assessment": rules.assessment_score(source_summaries["assessment"]),
        "text": rules.modality_score(source_summaries["text"]),
        "speech": rules.modality_score(source_summaries["speech"]),
        "emotion": rules.modality_score(source_summaries["emotion"]),
        "eeg": rules.modality_score(source_summaries["eeg"]),
    }

    risk_band, risk_score = _base_band_and_score(source_summaries["assessment"])

    forced_band, triggered_rules, rule_evidence = _evaluate_hard_rules(source_summaries)
    risk_band = rules.band_at_least(risk_band, forced_band)

    uplifted_band, uplift_rules, uplift_evidence = _evaluate_multimodal_uplift(
        source_summaries,
        risk_band,
    )
    risk_band = uplifted_band
    triggered_rules.extend(uplift_rules)
    rule_evidence.extend(uplift_evidence)
    risk_score = max(risk_score, rules.min_score_for_band(risk_band))

    evidence_summary: List[Dict[str, str]] = []
    for source_name, score in source_scores.items():
        evidence = _build_evidence(source_name, source_summaries[source_name], score)
        if evidence and score is not None and score >= 40:
            evidence_summary.append(evidence)
    evidence_summary.extend(rule_evidence)

    contributions = _build_contributions(source_scores)
    assessment_confidence = _confidence(source_summaries, source_scores)
    advisory_headline, advisory_actions, next_step = rules.safety_advice_for_band(risk_band)

    referral_recommended = risk_band in {"high", "urgent"}
    emergency_notice = risk_band == "urgent"
    advisory_code = 1001 if referral_recommended or emergency_notice else 0
    advisory_message = (
        "emergency_notice" if emergency_notice else "referral_recommended" if referral_recommended else "ok"
    )

    return RiskAssessmentResult(
        risk_level=risk_band,
        risk_score=risk_score,
        severity_band=risk_band,
        referral_recommended=referral_recommended,
        emergency_notice=emergency_notice,
        allow_continue=True,
        recommended_next_step=next_step,
        assessment_confidence=assessment_confidence,
        triggered_rules=triggered_rules,
        evidence_summary=evidence_summary,
        contributions=contributions,
        safety_advice={
            "headline": advisory_headline,
            "actions": advisory_actions,
        },
        threshold_snapshot=rules.threshold_snapshot(),
        advisory_code=advisory_code,
        advisory_message=advisory_message,
    )
