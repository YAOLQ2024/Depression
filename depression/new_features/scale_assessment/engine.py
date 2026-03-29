"""Deterministic scoring engine for PHQ-9 and GAD-7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .definitions import get_scale_definition


class ScaleValidationError(ValueError):
    """Raised when scale answers are invalid."""


@dataclass
class ScaleResult:
    scale_slug: str
    scale_code: str
    scale_name: str
    answers: Dict[str, int]
    total_score: int
    severity_key: str
    severity_label: str
    risk_flags: List[Dict[str, str]]
    highlights: List[Dict[str, object]]
    summary: str
    interpretation: str
    recommended_action: str

    def to_dict(self):
        return {
            "scale_slug": self.scale_slug,
            "scale_code": self.scale_code,
            "scale_name": self.scale_name,
            "answers": self.answers,
            "total_score": self.total_score,
            "severity_key": self.severity_key,
            "severity_label": self.severity_label,
            "risk_flags": self.risk_flags,
            "highlights": self.highlights,
            "summary": self.summary,
            "interpretation": self.interpretation,
            "recommended_action": self.recommended_action,
        }


def _normalize_answers(scale_def: Dict, raw_answers: Dict[str, object]) -> Dict[str, int]:
    normalized = {}
    missing = []
    valid_values = {option["value"] for option in scale_def["options"]}

    for item in scale_def["items"]:
        item_id = item["id"]
        raw_value = raw_answers.get(item_id)
        if raw_value in (None, ""):
            missing.append(item_id)
            continue

        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ScaleValidationError(f"{item_id} 的答案无效") from exc

        if value not in valid_values:
            raise ScaleValidationError(f"{item_id} 的分值超出范围")

        normalized[item_id] = value

    if missing:
        raise ScaleValidationError("还有题目未作答，请完整填写后再提交。")

    return normalized


def _resolve_severity(scale_def: Dict, total_score: int):
    for rule in scale_def["severity_rules"]:
        if rule["min"] <= total_score <= rule["max"]:
            return rule["key"], rule["label"]
    raise ScaleValidationError("量表分级规则缺失")


def _build_risk_flags(scale_def: Dict, answers: Dict[str, int]) -> List[Dict[str, str]]:
    flags = []
    for rule in scale_def.get("risk_rules", []):
        score = answers.get(rule["item_id"], 0)
        if score >= rule["min_score"]:
            flags.append({"flag": rule["flag"], "label": rule["label"]})
    return flags


def _build_highlights(scale_def: Dict, answers: Dict[str, int]) -> List[Dict[str, object]]:
    option_map = {option["value"]: option["label"] for option in scale_def["options"]}
    highlights = []
    for item in scale_def["items"]:
        score = answers[item["id"]]
        if score >= 2:
            highlights.append(
                {
                    "item_id": item["id"],
                    "index": item["index"],
                    "text": item["text"],
                    "score": score,
                    "answer_label": option_map.get(score, str(score)),
                }
            )
    highlights.sort(key=lambda row: (-row["score"], row["index"]))
    return highlights[:3]


def _build_copy(scale_slug: str, total_score: int, severity_label: str, risk_flags: List[Dict[str, str]], highlights: List[Dict[str, object]]):
    if scale_slug == "phq9":
        summary = f"PHQ-9 总分 {total_score} 分，当前落在“{severity_label}”区间。"
        interpretation = "该结果反映近两周抑郁相关症状的总体强度，适合作为初步筛查参考，不能替代正式诊断。"
        if highlights:
            highlight_text = "；".join(f"第{row['index']}题（{row['answer_label']}）" for row in highlights)
            interpretation += f" 当前较突出的条目包括：{highlight_text}。"
        if any(flag["flag"] == "item9_positive" for flag in risk_flags):
            recommended_action = "第9题出现阳性，建议尽快结合问诊进一步评估风险，必要时联系专业人员。"
        elif total_score >= 10:
            recommended_action = "建议继续进入自动问诊，并结合后续干预模块做进一步评估与追踪。"
        else:
            recommended_action = "建议结合近期压力事件继续观察，如症状持续加重可进入自动问诊进一步评估。"
        return summary, interpretation, recommended_action

    summary = f"GAD-7 总分 {total_score} 分，当前落在“{severity_label}”区间。"
    interpretation = "该结果反映近两周焦虑相关症状的总体强度，适合作为初步筛查参考，不能替代正式诊断。"
    if highlights:
        highlight_text = "；".join(f"第{row['index']}题（{row['answer_label']}）" for row in highlights)
        interpretation += f" 当前较突出的条目包括：{highlight_text}。"
    if total_score >= 10:
        recommended_action = "建议结合自动问诊继续判断焦虑触发因素，并观察是否已明显影响学习、工作或睡眠。"
    else:
        recommended_action = "建议继续关注近期压力、睡眠和作息变化，如症状持续可进入自动问诊进一步评估。"
    return summary, interpretation, recommended_action


def evaluate_scale(scale_slug: str, raw_answers: Dict[str, object]) -> ScaleResult:
    scale_def = get_scale_definition(scale_slug)
    if not scale_def:
        raise ScaleValidationError("暂不支持该量表")

    answers = _normalize_answers(scale_def, raw_answers)
    total_score = sum(answers.values())
    severity_key, severity_label = _resolve_severity(scale_def, total_score)
    risk_flags = _build_risk_flags(scale_def, answers)
    highlights = _build_highlights(scale_def, answers)
    summary, interpretation, recommended_action = _build_copy(
        scale_def["slug"],
        total_score,
        severity_label,
        risk_flags,
        highlights,
    )

    return ScaleResult(
        scale_slug=scale_def["slug"],
        scale_code=scale_def["code"],
        scale_name=scale_def["name"],
        answers=answers,
        total_score=total_score,
        severity_key=severity_key,
        severity_label=severity_label,
        risk_flags=risk_flags,
        highlights=highlights,
        summary=summary,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )
