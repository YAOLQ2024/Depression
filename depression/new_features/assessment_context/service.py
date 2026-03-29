#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for assessment payloads and counseling context."""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from utils import db

try:
    from new_features.scale_assessment.repository import get_latest_scale_records
except Exception:  # pragma: no cover - keep callers resilient if optional feature fails
    get_latest_scale_records = None

logger = logging.getLogger(__name__)

SDS_QUESTIONS = [
    "我觉得闷闷不乐，情绪低沉",
    "我觉得一天之中早晨最好",
    "我一阵阵哭出来或觉得想哭",
    "我晚上睡眠不好",
    "我吃得跟平常一样多",
    "我与异性密切接触时和以往一样感到愉快",
    "我发觉我的体重在下降",
    "我有便秘的苦恼",
    "我心跳比平常快",
    "我无缘无故地感到疲乏",
    "我的头脑跟平常一样清楚",
    "我觉得经常做的事情并没有困难",
    "我觉得不安而平静不下来",
    "我对将来抱有希望",
    "我比平常容易生气激动",
    "我觉得作出决定是容易的",
    "我觉得自己是个有用的人，有人需要我",
    "我的生活过得很有意思",
    "我认为如果我死了别人会生活得好些",
    "平常感兴趣的事我仍然照样感兴趣",
]


def format_display_time(dt_value: Any) -> str:
    if not dt_value:
        return ""

    try:
        if isinstance(dt_value, str):
            dt_value = datetime.datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
        if getattr(dt_value, "tzinfo", None) is not None:
            dt_value = dt_value.astimezone().replace(tzinfo=None)
        return dt_value.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt_value)


def get_latest_assessment_payload(*, user_id: Optional[int], username: Optional[str], viewer_role: Any = None):
    return get_assessment_payload(
        viewer_user_id=user_id,
        viewer_role=viewer_role,
        username=username,
        report_record_id=None,
    )


def get_assessment_payload(
    *,
    viewer_user_id: Optional[int],
    viewer_role: Any = None,
    username: Optional[str] = None,
    report_record_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    sds_payload = None
    if report_record_id is not None:
        sds_payload = get_sds_report_payload(
            record_id=report_record_id,
            viewer_user_id=viewer_user_id,
            viewer_role=viewer_role,
        )
    elif viewer_user_id is not None:
        sds_payload = get_latest_sds_report_payload(user_id=viewer_user_id)

    target_user_id = viewer_user_id
    target_username = username
    if sds_payload:
        target_user_id = sds_payload.get("user_id") or target_user_id
        target_username = sds_payload.get("username") or target_username

    latest_scales = get_latest_scale_payload(user_id=target_user_id, username=target_username)
    if not sds_payload and not latest_scales:
        return None

    payload = {
        "record_id": None,
        "score": None,
        "result": None,
        "comprehensive_score": None,
        "comprehensive_result": None,
        "emotion_data": None,
        "finish_time": "",
        "use_time": 0,
        "details": [],
        "latest_scales": latest_scales,
    }
    if sds_payload:
        public_sds_payload = dict(sds_payload)
        public_sds_payload.pop("user_id", None)
        public_sds_payload.pop("username", None)
        payload.update(public_sds_payload)
    return payload


def get_sds_report_payload(
    *,
    record_id: int,
    viewer_user_id: Optional[int] = None,
    viewer_role: Any = None,
) -> Optional[Dict[str, Any]]:
    if not record_id:
        return None

    query = ["SELECT * FROM test WHERE id = ?"]
    params: List[Any] = [int(record_id)]
    if not _is_admin(viewer_role) and viewer_user_id is not None:
        query.append("AND user_id = ?")
        params.append(viewer_user_id)

    test = db.fetch_one(" ".join(query), params)
    return serialize_sds_record(test)


def get_latest_sds_report_payload(*, user_id: int) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None

    test = db.fetch_one(
        """
        SELECT *
        FROM test
        WHERE user_id = ? AND status = '已完成'
        ORDER BY id DESC
        LIMIT 1
        """,
        [user_id],
    )
    return serialize_sds_record(test)


def serialize_sds_record(test: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not test:
        return None

    comprehensive_result = _deserialize_json(test.get("comprehensive_result"))
    emotion_data = _deserialize_json(test.get("emotion_data"))

    return {
        "record_id": test.get("id"),
        "user_id": test.get("user_id"),
        "username": test.get("username"),
        "score": test.get("score", 0),
        "result": test.get("result", "未知"),
        "comprehensive_score": test.get("comprehensive_score"),
        "comprehensive_result": comprehensive_result,
        "emotion_data": emotion_data,
        "finish_time": format_display_time(test.get("finish_time", "")),
        "use_time": test.get("use_time", 0),
        "details": build_sds_details(test.get("choose")),
    }


def build_sds_details(choices: Any) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    if not choices:
        return details

    for idx, (question, choice) in enumerate(zip(SDS_QUESTIONS, str(choices)), 1):
        score = int(choice) if str(choice).isdigit() else 0
        details.append(
            {
                "question_id": idx,
                "question_text": question,
                "score": score,
            }
        )
    return details


def get_latest_scale_payload(*, user_id: Optional[int] = None, username: Optional[str] = None) -> List[Dict[str, Any]]:
    if not get_latest_scale_records:
        return []

    try:
        scale_records = get_latest_scale_records(user_id=user_id, username=username)
    except Exception as exc:
        logger.warning("获取最新量表结果失败: %s", exc)
        return []

    payload: List[Dict[str, Any]] = []
    for record in scale_records:
        payload.append(
            {
                "record_id": record.get("id"),
                "scale_slug": record.get("scale_slug"),
                "scale_code": record.get("scale_code"),
                "scale_name": record.get("scale_name"),
                "total_score": record.get("total_score"),
                "severity_label": record.get("severity_label"),
                "summary": record.get("summary"),
                "interpretation": record.get("interpretation"),
                "recommended_action": record.get("recommended_action"),
                "completed_at": format_display_time(record.get("completed_at") or record.get("created_at")),
                "risk_flags": [
                    flag.get("label")
                    for flag in record.get("risk_flags", [])
                    if isinstance(flag, dict) and flag.get("label")
                ],
                "highlights": [
                    {
                        "index": item.get("index"),
                        "text": item.get("text"),
                        "score": item.get("score"),
                        "answer_label": item.get("answer_label"),
                    }
                    for item in record.get("highlights", [])[:3]
                ],
            }
        )
    return payload


def has_assessment_data(payload: Optional[Dict[str, Any]]) -> bool:
    if not payload:
        return False
    return bool(payload.get("record_id") or payload.get("latest_scales"))


def build_assessment_context(payload: Optional[Dict[str, Any]]) -> str:
    if not has_assessment_data(payload):
        return ""

    has_sds_report = bool(payload.get("record_id"))
    scale_reports = payload.get("latest_scales") or []
    lines = [
        "请结合以下最近评估背景理解用户状态，并在回答里优先围绕用户当前问题展开，不要机械复述量表说明。",
        "",
    ]

    if has_sds_report:
        sds_parts = [
            f"【完整测评（SDS）】标准分: {payload.get('score')}",
            f"抑郁程度: {payload.get('result')}",
        ]
        if payload.get("comprehensive_score"):
            sds_parts.append(f"综合评分: {payload.get('comprehensive_score')}")
        if payload.get("finish_time"):
            sds_parts.append(f"完成时间: {payload.get('finish_time')}")
        lines.append("，".join(sds_parts))

        comp = payload.get("comprehensive_result") or {}
        comp_summary = []
        if comp.get("depression_level"):
            comp_summary.append(f"抑郁等级: {comp.get('depression_level')}")
        if comp.get("comprehensive_score"):
            comp_summary.append(f"综合分: {comp.get('comprehensive_score')}")
        if comp.get("sds_score"):
            comp_summary.append(f"SDS分: {comp.get('sds_score')}")
        if comp_summary:
            lines.append(f"综合评分摘要: {'，'.join(comp_summary)}")

        emotion = payload.get("emotion_data") or {}
        if emotion.get("summary"):
            lines.append(f"表情识别摘要: {_compact_json(emotion.get('summary'))}")
        else:
            simplified = {}
            if emotion.get("dominant_emotion"):
                simplified["dominant_emotion"] = emotion.get("dominant_emotion")
            if emotion.get("total_detections") is not None:
                simplified["total_detections"] = emotion.get("total_detections")
            if simplified:
                lines.append(f"表情识别摘要: {_compact_json(simplified)}")

        high_score_items = [
            item for item in payload.get("details", []) if int(item.get("score") or 0) >= 3
        ]
        if high_score_items:
            lines.append(
                "高分题目: "
                + "，".join(
                    f"{item.get('question_id')}({item.get('score')}分)" for item in high_score_items
                )
            )
        lines.append("")

    if scale_reports:
        lines.append("【结构化量表结果】")
        for scale in scale_reports:
            line_parts = [
                f"{(scale.get('scale_code') or '量表')} {(scale.get('scale_name') or '')}".strip(),
                f"总分 {scale.get('total_score', '-')}",
                f"分级 {scale.get('severity_label') or '未知'}",
            ]
            if scale.get("completed_at"):
                line_parts.append(f"完成时间 {scale.get('completed_at')}")
            lines.append(f"- {'，'.join(line_parts)}")

            if scale.get("risk_flags"):
                lines.append(f"  风险提示: {'；'.join(scale.get('risk_flags'))}")

            highlights = scale.get("highlights") or []
            if highlights:
                highlight_text = "，".join(
                    f"第{item.get('index')}题（{item.get('answer_label') or item.get('score') or '-'}）"
                    for item in highlights
                )
                lines.append(f"  突出条目: {highlight_text}")

            if scale.get("summary"):
                lines.append(f"  摘要: {scale.get('summary')}")
            if scale.get("recommended_action"):
                lines.append(f"  建议: {scale.get('recommended_action')}")
        lines.append("")

    lines.append("请把这些内容当作背景信息，结合用户接下来的问题给出具体、温和且有针对性的回应。")
    return "\n".join(lines).strip()


def _compact_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _deserialize_json(value: Any) -> Optional[Any]:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def _is_admin(role: Any) -> bool:
    return str(role) == "2"
