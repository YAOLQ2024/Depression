"""Rule helpers for the risk assessment module."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

BASE_WEIGHTS: Dict[str, float] = {
    "assessment": 0.70,
    "text": 0.075,
    "speech": 0.075,
    "emotion": 0.075,
    "eeg": 0.075,
}

RISK_BANDS = (
    ("low", 0, 34),
    ("medium", 35, 59),
    ("high", 60, 79),
    ("urgent", 80, 100),
)

BAND_PRIORITY = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "urgent": 3,
}

MIN_SCORE_BY_BAND = {
    "low": 0,
    "medium": 35,
    "high": 60,
    "urgent": 80,
}

SCALE_TYPE_ALIASES = {
    "PHQ9": "PHQ-9",
    "PHQ-9": "PHQ-9",
    "PHQ_9": "PHQ-9",
    "phq9": "PHQ-9",
    "phq-9": "PHQ-9",
    "GAD7": "GAD-7",
    "GAD-7": "GAD-7",
    "GAD_7": "GAD-7",
    "gad7": "GAD-7",
    "gad-7": "GAD-7",
    "SDS": "SDS",
    "sds": "SDS",
}

SCALE_RULES = {
    "PHQ-9": {
        "max_score": 27.0,
        "low_upper": 9,
        "medium_upper": 14,
        "high_upper": 27,
        "medium_threshold": 10,
        "high_threshold": 15,
        "self_harm_key": "q9",
    },
    "GAD-7": {
        "max_score": 21.0,
        "low_upper": 9,
        "medium_upper": 14,
        "high_upper": 21,
        "medium_threshold": 10,
        "high_threshold": 15,
        "self_harm_key": None,
    },
    "SDS": {
        "max_score": 100.0,
        "low_upper": 52,
        "medium_upper": 62,
        "high_upper": 100,
        "medium_threshold": 53,
        "high_threshold": 63,
        "self_harm_key": None,
    },
}

FALLBACK_SEVERITY_TO_BAND = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "urgent": "urgent",
    "低": "low",
    "中": "medium",
    "高": "high",
    "紧急": "urgent",
    "低风险": "low",
    "中风险": "medium",
    "高风险": "high",
    "紧急风险": "urgent",
    "normal": "low",
    "minimal": "low",
    "none": "low",
    "无或极轻度": "low",
    "无抑郁": "low",
    "轻度": "low",
    "mild": "low",
    "moderate": "medium",
    "中度": "medium",
    "轻度抑郁": "medium",
    "moderately_severe": "high",
    "moderately-severe": "high",
    "中重度": "high",
    "severe": "high",
    "very_severe": "high",
    "重度": "high",
    "中度抑郁": "high",
    "重度抑郁": "high",
}

FALLBACK_SEVERITY_TO_SCORE = {
    "low": 20.0,
    "medium": 50.0,
    "high": 75.0,
    "urgent": 90.0,
}

NON_ASSESSMENT_HIGH_THRESHOLD = 70.0
NON_ASSESSMENT_MIN_CONFIDENCE = 0.70
NON_ASSESSMENT_UPLIFT_COUNT = 2
NON_ASSESSMENT_MAX_TARGET_BAND = "high"

URGENT_KEYWORDS = (
    "自杀",
    "轻生",
    "结束生命",
    "不想活",
    "马上去死",
    "现在就想死",
)

HIGH_RISK_KEYWORDS = (
    "伤害自己",
    "自残",
    "活不下去",
    "绝望",
    "崩溃",
    "撑不住",
    "没有意义",
)


def clamp_score(value: object, *, minimum: float = 0.0, maximum: float = 100.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(maximum, numeric))


def normalize_confidence(value: object, *, default: float = 0.5) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if numeric < 0:
        return default
    if numeric <= 1:
        return max(0.0, min(1.0, numeric))
    if numeric <= 100:
        return max(0.0, min(1.0, numeric / 100.0))
    return default


def normalize_summary_score(value: object) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= numeric <= 1.0:
        numeric *= 100.0
    return clamp_score(numeric)


def normalize_scale_type(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return SCALE_TYPE_ALIASES.get(raw, SCALE_TYPE_ALIASES.get(raw.upper(), raw.upper()))


def _summary_severity_band(summary: Dict[str, object]) -> Optional[str]:
    severity_candidates = [
        summary.get("severity"),
        summary.get("severity_key"),
        summary.get("severity_label"),
        summary.get("level"),
    ]
    for candidate in severity_candidates:
        key = str(candidate or "").strip().lower()
        if not key:
            continue
        band = FALLBACK_SEVERITY_TO_BAND.get(key)
        if band:
            return band
    return None


def assessment_band(summary: Dict[str, object]) -> Optional[str]:
    if not summary.get("available"):
        return None

    scale_type = normalize_scale_type(
        summary.get("scale_type") or summary.get("scale_code") or summary.get("scale_slug")
    )
    total_score = summary.get("total_score")
    if total_score in (None, ""):
        total_score = summary.get("score")
    try:
        numeric_score = float(total_score)
    except (TypeError, ValueError):
        numeric_score = None

    rule = SCALE_RULES.get(scale_type)
    if rule and numeric_score is not None:
        if numeric_score < rule["medium_threshold"]:
            return "low"
        if numeric_score < rule["high_threshold"]:
            return "medium"
        return "high"

    return _summary_severity_band(summary)


def assessment_score(summary: Dict[str, object]) -> Optional[float]:
    if not summary.get("available"):
        return None

    total_score = summary.get("total_score")
    if total_score in (None, ""):
        total_score = summary.get("score")
    scale_type = normalize_scale_type(
        summary.get("scale_type") or summary.get("scale_code") or summary.get("scale_slug")
    )
    if total_score not in (None, ""):
        try:
            numeric_score = float(total_score)
        except (TypeError, ValueError):
            numeric_score = None
        if numeric_score is not None:
            max_score = SCALE_RULES.get(scale_type, {}).get("max_score")
            if max_score and max_score > 0:
                return clamp_score((numeric_score / max_score) * 100.0)
            return clamp_score(numeric_score)

    band = _summary_severity_band(summary)
    if band:
        return FALLBACK_SEVERITY_TO_SCORE[band]

    return None


def modality_score(summary: Dict[str, object]) -> Optional[float]:
    if not summary.get("available"):
        return None
    return normalize_summary_score(summary.get("score"))


def self_harm_item_score(summary: Dict[str, object]) -> Optional[int]:
    if not summary.get("available"):
        return None

    direct_candidates = [
        summary.get("self_harm_item_score"),
        summary.get("item9_score"),
    ]
    for candidate in direct_candidates:
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue

    answers = summary.get("answers")
    if isinstance(answers, dict):
        for key in ("q9", "9", "item9"):
            try:
                return int(answers[key])
            except (KeyError, TypeError, ValueError):
                continue

    if summary.get("self_harm_item_positive"):
        return 1

    risk_flags = summary.get("risk_flags")
    if isinstance(risk_flags, list):
        for flag in risk_flags:
            if not isinstance(flag, dict):
                continue
            if str(flag.get("flag") or "").strip().lower() == "item9_positive":
                return 1

    return None


def band_from_score(score: float) -> str:
    numeric = clamp_score(score)
    for band, lower, upper in RISK_BANDS:
        if lower <= numeric <= upper:
            return band
    return "urgent"


def band_at_least(current_band: str, required_band: str) -> str:
    return required_band if BAND_PRIORITY[required_band] > BAND_PRIORITY[current_band] else current_band


def next_band(current_band: str, *, maximum: str = "urgent") -> str:
    order = ("low", "medium", "high", "urgent")
    current_index = order.index(current_band)
    max_index = order.index(maximum)
    return order[min(current_index + 1, max_index)]


def min_score_for_band(band: str) -> int:
    return MIN_SCORE_BY_BAND[band]


def contains_keywords(text: str, keywords: Iterable[str]) -> Optional[str]:
    lowered = text.lower()
    for keyword in keywords:
        if keyword and keyword.lower() in lowered:
            return keyword
    return None


def is_high_support_signal(summary: Dict[str, object]) -> bool:
    if not summary.get("available"):
        return False
    score = modality_score(summary)
    confidence = normalize_confidence(summary.get("confidence"), default=0.0)
    return bool(
        score is not None
        and score >= NON_ASSESSMENT_HIGH_THRESHOLD
        and confidence >= NON_ASSESSMENT_MIN_CONFIDENCE
    )


def threshold_snapshot() -> Dict[str, object]:
    return {
        "referral_threshold": "high",
        "emergency_threshold": "urgent",
        "non_blocking_flow": True,
        "allow_continue_default": True,
        "assessment_primary": True,
        "scale_rules": {
            "PHQ-9": {
                "medium_threshold": SCALE_RULES["PHQ-9"]["medium_threshold"],
                "high_threshold": SCALE_RULES["PHQ-9"]["high_threshold"],
                "self_harm_item_score_high": 1,
                "self_harm_item_score_urgent": 2,
            },
            "GAD-7": {
                "medium_threshold": SCALE_RULES["GAD-7"]["medium_threshold"],
                "high_threshold": SCALE_RULES["GAD-7"]["high_threshold"],
            },
            "SDS": {
                "medium_threshold": SCALE_RULES["SDS"]["medium_threshold"],
                "high_threshold": SCALE_RULES["SDS"]["high_threshold"],
                "score_type": "standard_score",
            },
        },
        "multimodal_uplift": {
            "enabled": True,
            "min_high_modalities": NON_ASSESSMENT_UPLIFT_COUNT,
            "high_score_threshold": NON_ASSESSMENT_HIGH_THRESHOLD,
            "min_confidence": NON_ASSESSMENT_MIN_CONFIDENCE,
            "max_target_band": NON_ASSESSMENT_MAX_TARGET_BAND,
        },
    }


def safety_advice_for_band(band: str) -> Tuple[str, list[str], str]:
    if band == "urgent":
        return (
            "建议立即寻求紧急帮助，系统内容仅作为陪伴性支持。",
            [
                "优先联系心理老师、医生、家属或可信赖照护者",
                "如处于紧急状态，请尽快寻求线下紧急帮助",
            ],
            "seek_emergency_support_now",
        )

    if band == "high":
        return (
            "建议优先寻求专业帮助，系统调控仅作为辅助支持。",
            [
                "优先联系心理老师、医生或可信赖照护者",
                "如愿意，仍可继续完成引导问诊和后续调控体验",
            ],
            "continue_with_strong_warning",
        )

    if band == "medium":
        return (
            "建议继续完成引导问诊，以补充近期状态和需求信息。",
            [
                "保持后续问诊流程",
                "继续观察睡眠、压力和情绪波动",
            ],
            "continue_to_dialogue",
        )

    return (
        "当前可以继续进入引导问诊，系统将进一步补充画像信息。",
        [
            "继续完成引导问诊",
            "后续可根据个人偏好体验调控内容",
        ],
        "continue_to_dialogue",
    )
