"""Definitions for supported screening scales."""

from __future__ import annotations

OPTION_LABELS_FOUR_POINT = [
    {"value": 0, "label": "完全没有", "description": "过去两周从未出现"},
    {"value": 1, "label": "几天", "description": "过去两周偶尔出现"},
    {"value": 2, "label": "一半以上天数", "description": "过去两周经常出现"},
    {"value": 3, "label": "几乎每天", "description": "过去两周大部分时间出现"},
]


SCALE_DEFINITIONS = {
    "phq9": {
        "code": "PHQ-9",
        "slug": "phq9",
        "name": "PHQ-9 抑郁筛查量表",
        "short_name": "PHQ-9",
        "description": "用于快速评估近两周抑郁症状的严重程度。",
        "intro": "请根据过去两周你的实际状态作答。",
        "mode": "self_report",
        "options": OPTION_LABELS_FOUR_POINT,
        "items": [
            {"id": "q1", "index": 1, "text": "做事时提不起劲或没有兴趣"},
            {"id": "q2", "index": 2, "text": "感到心情低落、沮丧或绝望"},
            {"id": "q3", "index": 3, "text": "入睡困难、睡不安稳或睡眠过多"},
            {"id": "q4", "index": 4, "text": "感觉疲倦或没有活力"},
            {"id": "q5", "index": 5, "text": "食欲不振或吃太多"},
            {"id": "q6", "index": 6, "text": "觉得自己很糟，或觉得自己很失败，或让自己或家人失望"},
            {"id": "q7", "index": 7, "text": "对事物专注有困难，例如阅读报纸或看电视时"},
            {"id": "q8", "index": 8, "text": "动作或说话速度缓慢到别人已经察觉，或正好相反，烦躁或坐立不安、动来动去比平常更多"},
            {"id": "q9", "index": 9, "text": "有不如死掉或用某种方式伤害自己的念头"},
        ],
        "severity_rules": [
            {"min": 0, "max": 4, "key": "minimal", "label": "无或极轻度"},
            {"min": 5, "max": 9, "key": "mild", "label": "轻度"},
            {"min": 10, "max": 14, "key": "moderate", "label": "中度"},
            {"min": 15, "max": 19, "key": "moderately_severe", "label": "中重度"},
            {"min": 20, "max": 27, "key": "severe", "label": "重度"},
        ],
        "risk_rules": [
            {"item_id": "q9", "min_score": 1, "flag": "item9_positive", "label": "第9题阳性"},
        ],
    },
    "gad7": {
        "code": "GAD-7",
        "slug": "gad7",
        "name": "GAD-7 焦虑筛查量表",
        "short_name": "GAD-7",
        "description": "用于快速评估近两周焦虑症状的严重程度。",
        "intro": "请根据过去两周你的实际状态作答。",
        "mode": "self_report",
        "options": OPTION_LABELS_FOUR_POINT,
        "items": [
            {"id": "q1", "index": 1, "text": "感到紧张、焦虑或心神不定"},
            {"id": "q2", "index": 2, "text": "无法停止或控制担忧"},
            {"id": "q3", "index": 3, "text": "对各种各样的事情担忧过多"},
            {"id": "q4", "index": 4, "text": "很难放松下来"},
            {"id": "q5", "index": 5, "text": "由于坐立不安而难以静坐"},
            {"id": "q6", "index": 6, "text": "变得容易烦恼或急躁"},
            {"id": "q7", "index": 7, "text": "感到害怕，好像有什么可怕的事情会发生"},
        ],
        "severity_rules": [
            {"min": 0, "max": 4, "key": "minimal", "label": "无或极轻度"},
            {"min": 5, "max": 9, "key": "mild", "label": "轻度"},
            {"min": 10, "max": 14, "key": "moderate", "label": "中度"},
            {"min": 15, "max": 21, "key": "severe", "label": "重度"},
        ],
        "risk_rules": [],
    },
}


def get_scale_definition(scale_slug: str):
    """Return a supported scale definition by slug."""
    if not scale_slug:
        return None
    return SCALE_DEFINITIONS.get(str(scale_slug).strip().lower())


def list_scale_definitions():
    """Return all scale definitions in display order."""
    return [SCALE_DEFINITIONS["phq9"], SCALE_DEFINITIONS["gad7"]]
