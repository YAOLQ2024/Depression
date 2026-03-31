"""Domain helpers for the refactored care journey."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


DOCTOR_CATALOG: List[Dict[str, Any]] = [
    {
        "slug": "anwen",
        "name": "安雯医生",
        "persona": "温和陪伴型",
        "headline": "先帮你把情绪放稳，再一步步完成初筛。",
        "description": "适合第一次进入系统、需要被安抚和被理解的用户。",
        "interaction_style": "温和陪伴",
        "voice_tone": "轻柔、慢节奏",
        "greeting": "你好，我会陪你完成这次简短评估。如果你中途感到不适，我们随时可以停下来。",
        "video_file": "1.mp4",
        "accent": "#C86A4A",
    },
    {
        "slug": "zhichen",
        "name": "知宸医生",
        "persona": "理性分析型",
        "headline": "我们先按结构化流程完成评估，再一起看结果。",
        "description": "适合希望快速理解风险分层、偏好清晰解释的用户。",
        "interaction_style": "理性分析",
        "voice_tone": "平稳、清晰",
        "greeting": "接下来我会带你完成 PHQ-9 与 GAD-7 初筛，并用可解释的方式说明结果和下一步建议。",
        "video_file": "2.mp4",
        "accent": "#2B7A78",
    },
    {
        "slug": "peipei",
        "name": "沛沛医生",
        "persona": "日常支持型",
        "headline": "像一次有边界的陪聊，但每一步都会留下记录。",
        "description": "适合希望交互自然、愿意后续长期追踪变化的用户。",
        "interaction_style": "陪伴共情",
        "voice_tone": "温暖、鼓励",
        "greeting": "这不是一次冷冰冰的测试，我们会先了解你的状态，再给出适合你节奏的建议。",
        "video_file": "3.mp4",
        "accent": "#D28D49",
    },
]


MODE_LIBRARY: Dict[str, Dict[str, Any]] = {
    "breathing_reset": {
        "label": "呼吸稳定",
        "summary": "适合焦虑、紧张、心跳加快、坐立不安等状态。",
        "video_file": "8.mp4",
    },
    "sleep_relief": {
        "label": "睡前减压",
        "summary": "适合睡眠受影响、思绪停不下来、夜间焦虑。",
        "video_file": "11.mp4",
    },
    "activation_light": {
        "label": "低压激活",
        "summary": "适合情绪低落、动力不足、兴趣下降。",
        "video_file": "6.mp4",
    },
    "grounding_support": {
        "label": "稳定陪伴",
        "summary": "适合需要先获得支持和安定感，再决定下一步。",
        "video_file": "5.mp4",
    },
    "safety_escalation": {
        "label": "安全关注",
        "summary": "适合存在明显风险信号，需要尽快人工关注和现实支持。",
        "video_file": "18.mp4",
    },
}


def get_doctor_catalog() -> List[Dict[str, Any]]:
    return [dict(item) for item in DOCTOR_CATALOG]


def get_doctor_by_slug(slug: Optional[str]) -> Dict[str, Any]:
    for doctor in DOCTOR_CATALOG:
        if doctor["slug"] == slug:
            return dict(doctor)
    return dict(DOCTOR_CATALOG[0])


def default_settings() -> Dict[str, Any]:
    return {
        "voice_broadcast": True,
        "capture_audio": True,
        "capture_camera": True,
        "capture_eeg": False,
        "privacy_ack": False,
        "debug_mode": False,
    }


def merge_settings(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = default_settings()
    if settings:
        merged.update(settings)
    return merged


def summarize_assessment_state(phq_record: Optional[Dict[str, Any]], gad_record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    phq_score = int(phq_record.get("total_score", 0) if phq_record else 0)
    gad_score = int(gad_record.get("total_score", 0) if gad_record else 0)
    combined_score = phq_score + gad_score

    phq_severity = phq_record.get("severity_label", "未完成") if phq_record else "未完成"
    gad_severity = gad_record.get("severity_label", "未完成") if gad_record else "未完成"
    has_item9_flag = any(flag.get("flag") == "item9_positive" for flag in (phq_record or {}).get("risk_flags", []))

    if has_item9_flag:
        risk_tier = "urgent"
        risk_label = "需重点安全关注"
        doctor_script = "本次结果提示存在需要优先关注的风险信号，建议尽快结合现实支持系统和专业人员进一步评估。"
    elif max(phq_score, gad_score) >= 15 or combined_score >= 24:
        risk_tier = "high"
        risk_label = "高风险"
        doctor_script = "从本次量表结果看，你近期的情绪负荷比较高，建议马上进入更具体的调节方案，并尽快安排持续跟踪。"
    elif max(phq_score, gad_score) >= 10 or combined_score >= 16:
        risk_tier = "moderate"
        risk_label = "中风险"
        doctor_script = "你最近可能确实承受着比较明显的情绪压力，接下来适合进入更聚焦的调节建议，而不是只停留在分数上。"
    elif combined_score > 0:
        risk_tier = "mild"
        risk_label = "轻至中低风险"
        doctor_script = "当前量表结果提示存在一定压力，但整体仍处在可调节区间，适合通过轻干预和持续追踪来观察变化。"
    else:
        risk_tier = "baseline"
        risk_label = "基线待建立"
        doctor_script = "你还没有完成完整的初筛，先完成量表后系统才能生成更清楚的分层结果。"

    return {
        "risk_tier": risk_tier,
        "risk_label": risk_label,
        "combined_score": combined_score,
        "phq_score": phq_score,
        "gad_score": gad_score,
        "phq_severity": phq_severity,
        "gad_severity": gad_severity,
        "has_item9_flag": has_item9_flag,
        "doctor_script": doctor_script,
    }


def build_screening_highlights(phq_record: Optional[Dict[str, Any]], gad_record: Optional[Dict[str, Any]]) -> List[str]:
    highlights: List[str] = []
    for record in (phq_record, gad_record):
        if not record:
            continue
        for item in record.get("highlights", [])[:2]:
            if item.get("text"):
                highlights.append(f"{record.get('scale_code')} 第{item.get('index')}题：{item.get('text')}")
    return highlights[:4]


def build_regulation_preview(
    *,
    profile: Optional[Dict[str, Any]],
    preference: Optional[Dict[str, Any]],
    settings: Optional[Dict[str, Any]],
    phq_record: Optional[Dict[str, Any]],
    gad_record: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    assessment = summarize_assessment_state(phq_record, gad_record)
    settings = merge_settings(settings)

    if assessment["has_item9_flag"]:
        mode_key = "safety_escalation"
        plan_title = "先建立安全支持，再进入后续调节"
        summary = "优先降低风险、联结现实支持系统，并保持低刺激陪伴。"
        recommendations = [
            {"title": "现实支持提醒", "detail": "建议尽快联系家人、朋友、校医院或心理老师，不要独自承担。"},
            {"title": "即时安抚视频", "detail": "先播放低刺激医生陪伴视频，稳定情绪后再决定下一步。"},
            {"title": "后续人工关注", "detail": "建议安排人工复核或专业人员进一步评估。"},
        ]
    elif assessment["gad_score"] >= assessment["phq_score"] and assessment["gad_score"] >= 10:
        mode_key = "breathing_reset"
        plan_title = "焦虑缓和与呼吸稳定方案"
        summary = "优先降低生理紧张和思维过载，适合先做短时呼吸练习与低刺激视频。"
        recommendations = [
            {"title": "90 秒呼吸引导", "detail": "用固定节律把注意力从担忧拉回身体。"},
            {"title": "低刺激医生视频", "detail": "播放节奏平缓的陪伴视频，减少信息负荷。"},
            {"title": "睡前减压提醒", "detail": "若晚间焦虑明显，可追加睡前减压内容。"},
        ]
    elif assessment["phq_score"] >= 10:
        mode_key = "activation_light"
        plan_title = "低落缓解与轻激活方案"
        summary = "优先帮助用户恢复一点点行动感和日常节律，而不是一次要求太多。"
        recommendations = [
            {"title": "轻任务激活", "detail": "把调节拆成可完成的小动作，如起身、喝水、晒光。"},
            {"title": "节律型视频提示", "detail": "使用更有节奏的医生视频做行为启动提醒。"},
            {"title": "情绪记录", "detail": "执行后记录最困扰的感受和今天最想改善的一件事。"},
        ]
    elif assessment["gad_score"] >= 5 or assessment["phq_score"] >= 5:
        mode_key = "grounding_support"
        plan_title = "支持性陪伴与短时稳定方案"
        summary = "适合轻度压力状态，先通过陪伴、解释和轻提示完成一次完整闭环。"
        recommendations = [
            {"title": "医生解释结果", "detail": "用更自然的语言帮助用户理解当前压力状态。"},
            {"title": "3 分钟稳定练习", "detail": "进行一次短时放松或专注练习。"},
            {"title": "48 小时再观察", "detail": "建议记录变化并决定是否再次评估。"},
        ]
    else:
        mode_key = "sleep_relief"
        plan_title = "基础自我照护与节律维护方案"
        summary = "当前更适合保持节律、建立记录习惯，并在需要时再次评估。"
        recommendations = [
            {"title": "作息维护", "detail": "保持起床和入睡时间稳定，减少晚间高刺激输入。"},
            {"title": "轻量追踪", "detail": "记录今天情绪波动最明显的时间点和触发因素。"},
            {"title": "按需复测", "detail": "若一周内持续波动，可再次完成量表。"},
        ]

    mode_meta = MODE_LIBRARY[mode_key]
    doctor = get_doctor_by_slug((preference or {}).get("doctor_slug"))
    multimodal_open = [
        name
        for enabled, name in [
            (settings.get("capture_audio"), "语音"),
            (settings.get("capture_camera"), "表情"),
            (settings.get("capture_eeg"), "EEG"),
        ]
        if enabled
    ]

    return {
        "risk_level": assessment["risk_label"],
        "risk_tier": assessment["risk_tier"],
        "plan_title": plan_title,
        "summary": summary,
        "execution_mode": mode_key,
        "mode_label": mode_meta["label"],
        "mode_summary": mode_meta["summary"],
        "video_file": mode_meta["video_file"],
        "doctor_name": doctor["name"],
        "doctor_script": assessment["doctor_script"],
        "recommendations": recommendations,
        "screening_highlights": build_screening_highlights(phq_record, gad_record),
        "multimodal_open": multimodal_open,
        "profile_focus": (profile or {}).get("support_focus", ""),
        "engine_name": "rule-engine-placeholder",
        "available_modes": [
            {
                "key": key,
                "label": value["label"],
                "summary": value["summary"],
                "video_file": value["video_file"],
            }
            for key, value in MODE_LIBRARY.items()
        ],
    }
