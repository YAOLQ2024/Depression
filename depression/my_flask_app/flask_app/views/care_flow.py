from __future__ import annotations

import json
import time
from datetime import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for

from new_features.care_flow.repository import (
    create_execution_record,
    create_regulation_plan,
    ensure_care_flow_tables,
    get_admin_snapshot,
    get_care_preference,
    get_latest_regulation_plan,
    get_patient_profile,
    get_regulation_plan,
    get_user_settings,
    list_execution_records,
    list_regulation_plans,
    save_care_preference,
    save_patient_profile,
    save_user_settings,
)
from new_features.care_flow.service import (
    build_regulation_preview,
    get_doctor_by_slug,
    get_doctor_catalog,
    merge_settings,
    summarize_assessment_state,
)
from new_features.scale_assessment.definitions import get_scale_definition
from new_features.scale_assessment.engine import ScaleValidationError, evaluate_scale
from new_features.scale_assessment.repository import create_scale_record, get_scale_record, list_scale_records
from new_features.session_summary_skill.service import load_history_from_db

ensure_care_flow_tables()

cf = Blueprint("care_flow", __name__)


def _current_user():
    return session.get("userinfo")


def _current_user_id() -> int:
    userinfo = _current_user() or {}
    return int(userinfo.get("id") or 0)


def _current_username() -> str:
    userinfo = _current_user() or {}
    return str(userinfo.get("name") or userinfo.get("username") or "")


def _is_admin() -> bool:
    role = str((_current_user() or {}).get("role") or "")
    return role == "2"


def _doctor_with_media(doctor):
    decorated = dict(doctor or {})
    video_file = decorated.get("video_file")
    decorated["video_url"] = url_for("get_video", filename=video_file) if video_file else ""
    return decorated


def _journey_context(extra=None):
    user_id = _current_user_id()
    profile = get_patient_profile(user_id) if user_id else None
    preference = get_care_preference(user_id) if user_id else None
    settings = merge_settings(get_user_settings(user_id)) if user_id else merge_settings(None)
    doctor = _doctor_with_media(get_doctor_by_slug((preference or {}).get("doctor_slug")))

    context = {
        "journey_profile": profile,
        "journey_preference": preference,
        "journey_settings": settings,
        "selected_doctor": doctor if preference else None,
        "journey_user": _current_user(),
    }
    if extra:
        context.update(extra)
    return context


def _latest_scale_pair():
    user_id = _current_user_id()
    records = list_scale_records(user_id=user_id, limit=20)
    latest = {}
    for record in records:
        latest.setdefault(record.get("scale_slug"), record)
    return latest.get("phq9"), latest.get("gad7")


def _current_scale_pair():
    state = session.get("journey_latest_scale_ids") or {}
    phq_record = get_scale_record(state["phq9"]) if state.get("phq9") else None
    gad_record = get_scale_record(state["gad7"]) if state.get("gad7") else None
    if phq_record or gad_record:
        return phq_record, gad_record
    return _latest_scale_pair()


def _serialize_timeline(scales, plans, executions):
    items = []
    for scale in scales:
        items.append(
            {
                "kind": "assessment",
                "timestamp": scale.get("completed_at") or scale.get("created_at") or "",
                "title": f"{scale.get('scale_code')} · {scale.get('severity_label')}",
                "summary": scale.get("summary"),
                "meta": f"总分 {scale.get('total_score')}",
            }
        )
    for plan in plans:
        items.append(
            {
                "kind": "plan",
                "timestamp": plan.get("created_at") or "",
                "title": plan.get("plan_title"),
                "summary": plan.get("plan_summary"),
                "meta": plan.get("risk_level"),
            }
        )
    for execution in executions:
        items.append(
            {
                "kind": "execution",
                "timestamp": execution.get("completed_at") or "",
                "title": "调节执行完成",
                "summary": execution.get("feedback_text") or "已完成一次调节执行并记录反馈。",
                "meta": f"反馈 {execution.get('feedback_score', 0)}/5",
            }
        )
    items.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
    return items


@cf.route("/journey/entry")
def journey_entry():
    if not _current_user():
        return redirect("/login")

    user_id = _current_user_id()
    profile = get_patient_profile(user_id)
    if not profile:
        return redirect(url_for("care_flow.profile"))

    preference = get_care_preference(user_id)
    if not preference:
        return redirect(url_for("care_flow.doctor_select"))

    return redirect(url_for("care_flow.task_home"))


@cf.route("/journey/profile", methods=["GET", "POST"])
def profile():
    if not _current_user():
        return redirect("/login")

    user_id = _current_user_id()
    profile = get_patient_profile(user_id) or {}

    if request.method == "POST":
        save_patient_profile(
            user_id,
            {
                "display_name": request.form.get("display_name", "").strip() or _current_username(),
                "age_band": request.form.get("age_band", "").strip(),
                "gender": request.form.get("gender", "").strip(),
                "first_visit": request.form.get("first_visit", "yes") == "yes",
                "emotional_history": request.form.get("emotional_history", "").strip(),
                "support_focus": request.form.get("support_focus", "").strip(),
            },
        )
        flash("基础建档信息已保存。", "info")
        return redirect(url_for("care_flow.doctor_select"))

    return render_template(
        "journey/profile.html",
        **_journey_context(
            {
                "page_kicker": "入口与身份层",
                "page_title": "患者建档",
                "page_description": "先建立基础画像，后续量表、历史和调节建议都会基于这份上下文组织。",
                "profile": profile,
            }
        ),
    )


@cf.route("/journey/doctor", methods=["GET", "POST"])
def doctor_select():
    if not _current_user():
        return redirect("/login")

    user_id = _current_user_id()
    preference = get_care_preference(user_id) or {}
    settings = merge_settings(get_user_settings(user_id))
    doctors = [_doctor_with_media(doctor) for doctor in get_doctor_catalog()]

    if request.method == "POST":
        selected_slug = request.form.get("doctor_slug", "").strip()
        doctor = get_doctor_by_slug(selected_slug)
        voice_enabled = "voice_enabled" in request.form
        save_care_preference(
            user_id,
            {
                "doctor_slug": doctor["slug"],
                "doctor_name": doctor["name"],
                "interaction_style": request.form.get("interaction_style", doctor["interaction_style"]).strip(),
                "voice_enabled": voice_enabled,
                "greeting_script": doctor["greeting"],
                "avatar_video": doctor["video_file"],
            },
        )
        save_user_settings(
            user_id,
            {
                **settings,
                "voice_broadcast": voice_enabled,
            },
        )
        flash("虚拟医生与交互风格已更新。", "info")
        return redirect(url_for("care_flow.task_home"))

    preview_doctor = _doctor_with_media(get_doctor_by_slug((preference or {}).get("doctor_slug")))
    return render_template(
        "journey/doctor_select.html",
        **_journey_context(
            {
                "page_kicker": "角色与任务入口层",
                "page_title": "选择虚拟医生",
                "page_description": "先确认交互对象和语音风格，再进入正式的初筛与调节主链。",
                "doctors": doctors,
                "preference": preference,
                "preview_doctor": preview_doctor,
            }
        ),
    )


@cf.route("/journey/home")
def task_home():
    if not _current_user():
        return redirect("/login")

    profile = get_patient_profile(_current_user_id())
    if not profile:
        return redirect(url_for("care_flow.profile"))

    preference = get_care_preference(_current_user_id())
    if not preference:
        return redirect(url_for("care_flow.doctor_select"))

    phq_record, gad_record = _latest_scale_pair()
    assessment = summarize_assessment_state(phq_record, gad_record)
    latest_plan = get_latest_regulation_plan(_current_user_id())
    recent_scales = list_scale_records(user_id=_current_user_id(), limit=4)

    return render_template(
        "journey/home.html",
        **_journey_context(
            {
                "page_kicker": "角色与任务入口层",
                "page_title": "问诊首页 / 任务入口",
                "page_description": "从这里进入结构化量表、查看历史变化，或回到上一轮调节任务。",
                "assessment": assessment,
                "latest_plan": latest_plan,
                "recent_scales": recent_scales,
            }
        ),
    )


@cf.route("/journey/screening", methods=["GET", "POST"])
def screening():
    if not _current_user():
        return redirect("/login")

    phq_scale = get_scale_definition("phq9")
    gad_scale = get_scale_definition("gad7")
    started_at = request.form.get("started_at") or str(int(time.time()))
    settings = merge_settings(get_user_settings(_current_user_id()))

    if request.method == "POST":
        user_id = _current_user_id()
        username = _current_username()
        phq_raw = {item["id"]: request.form.get(f"phq9_{item['id']}") for item in phq_scale["items"]}
        gad_raw = {item["id"]: request.form.get(f"gad7_{item['id']}") for item in gad_scale["items"]}

        try:
            phq_result = evaluate_scale("phq9", phq_raw).to_dict()
            gad_result = evaluate_scale("gad7", gad_raw).to_dict()
        except ScaleValidationError as exc:
            flash(str(exc), "error")
            return redirect(url_for("care_flow.screening"))

        use_time = 0
        if started_at.isdigit():
            use_time = max(0, int(time.time()) - int(started_at))

        phq_id = create_scale_record(user_id=user_id, username=username, result=phq_result, use_time=use_time)
        gad_id = create_scale_record(user_id=user_id, username=username, result=gad_result, use_time=use_time)
        session["journey_latest_scale_ids"] = {"phq9": phq_id, "gad7": gad_id}
        flash("初筛量表已完成，系统正在整理风险分层结果。", "info")
        return redirect(url_for("care_flow.result_analysis"))

    return render_template(
        "journey/screening.html",
        **_journey_context(
            {
                "page_kicker": "问诊执行层",
                "page_title": "结构化量表问诊",
                "page_description": "当前 V1 以 PHQ-9 和 GAD-7 为硬主链，语音、表情和 EEG 作为辅助采集层并行接入。",
                "phq_scale": phq_scale,
                "gad_scale": gad_scale,
                "scale_sections": [(phq_scale, "phq9"), (gad_scale, "gad7")],
                "started_at": started_at,
                "settings": settings,
            }
        ),
    )


@cf.route("/journey/result")
def result_analysis():
    if not _current_user():
        return redirect("/login")

    phq_record, gad_record = _current_scale_pair()
    if not phq_record and not gad_record:
        flash("请先完成结构化量表问诊。", "error")
        return redirect(url_for("care_flow.screening"))

    assessment = summarize_assessment_state(phq_record, gad_record)
    doctor = _doctor_with_media(get_doctor_by_slug((get_care_preference(_current_user_id()) or {}).get("doctor_slug")))

    return render_template(
        "journey/result.html",
        **_journey_context(
            {
                "page_kicker": "问诊执行层",
                "page_title": "结果分析与风险分层",
                "page_description": "先给出清楚、可解释的分层结果，再交给虚拟医生完成自然语言反馈。",
                "phq_record": phq_record,
                "gad_record": gad_record,
                "assessment_records": [record for record in (phq_record, gad_record) if record],
                "assessment": assessment,
                "doctor_feedback": doctor.get("greeting", ""),
            }
        ),
    )


@cf.route("/journey/decision", methods=["GET", "POST"])
def decision():
    if not _current_user():
        return redirect("/login")

    phq_record, gad_record = _current_scale_pair()
    if not phq_record and not gad_record:
        flash("请先完成结果分析。", "error")
        return redirect(url_for("care_flow.screening"))

    profile = get_patient_profile(_current_user_id())
    preference = get_care_preference(_current_user_id())
    settings = merge_settings(get_user_settings(_current_user_id()))
    preview = build_regulation_preview(
        profile=profile,
        preference=preference,
        settings=settings,
        phq_record=phq_record,
        gad_record=gad_record,
    )

    if request.method == "POST":
        mode_key = request.form.get("execution_mode", preview["execution_mode"])
        selected_mode = next((item for item in preview["available_modes"] if item["key"] == mode_key), preview["available_modes"][0])
        plan_id = create_regulation_plan(
            _current_user_id(),
            {
                "phq_record_id": phq_record.get("id") if phq_record else None,
                "gad_record_id": gad_record.get("id") if gad_record else None,
                "risk_level": preview["risk_level"],
                "plan_title": request.form.get("plan_title", preview["plan_title"]).strip(),
                "plan_summary": request.form.get("plan_summary", preview["summary"]).strip(),
                "recommendations": preview["recommendations"],
                "execution_mode": mode_key,
                "media_type": "video",
                "media_url": url_for("get_video", filename=selected_mode["video_file"]),
                "engine_name": request.form.get("engine_name", preview["engine_name"]).strip() or preview["engine_name"],
                "status": "recommended",
            },
        )
        session["journey_latest_plan_id"] = plan_id
        flash("个性化调控决策已生成。", "info")
        return redirect(url_for("care_flow.advice", plan_id=plan_id))

    return render_template(
        "journey/decision.html",
        **_journey_context(
            {
                "page_kicker": "问诊执行层",
                "page_title": "个性化调控决策",
                "page_description": "这一页先用规则引擎占位，后续可以替换成本地 LLM 或远端 API 决策。",
                "preview": preview,
                "phq_record": phq_record,
                "gad_record": gad_record,
            }
        ),
    )


@cf.route("/journey/advice")
def advice():
    if not _current_user():
        return redirect("/login")

    plan_id = request.args.get("plan_id", type=int) or session.get("journey_latest_plan_id")
    plan = get_regulation_plan(plan_id) if plan_id else get_latest_regulation_plan(_current_user_id())
    if not plan:
        flash("请先生成调控决策方案。", "error")
        return redirect(url_for("care_flow.decision"))

    return render_template(
        "journey/advice.html",
        **_journey_context(
            {
                "page_kicker": "调节闭环层",
                "page_title": "调节建议",
                "page_description": "先把建议讲清楚，再进入具体执行；这一步强调可执行和可追踪，而不是只给抽象口号。",
                "plan": plan,
            }
        ),
    )


@cf.route("/journey/execution", methods=["GET", "POST"])
def execution():
    if not _current_user():
        return redirect("/login")

    plan_id = request.args.get("plan_id", type=int) or session.get("journey_latest_plan_id")
    plan = get_regulation_plan(plan_id) if plan_id else get_latest_regulation_plan(_current_user_id())
    if not plan:
        flash("请先生成并确认调节方案。", "error")
        return redirect(url_for("care_flow.decision"))

    if request.method == "POST":
        create_execution_record(
            plan_id=plan["id"],
            user_id=_current_user_id(),
            feedback_score=request.form.get("feedback_score", type=int) or 0,
            feedback_text=request.form.get("feedback_text", "").strip(),
            duration_seconds=request.form.get("duration_seconds", type=int) or 0,
        )
        flash("本次调节执行已记录，后续可以在历史页查看变化。", "info")
        return redirect(url_for("care_flow.history"))

    doctor = _doctor_with_media(get_doctor_by_slug((get_care_preference(_current_user_id()) or {}).get("doctor_slug")))
    return render_template(
        "journey/execution.html",
        **_journey_context(
            {
                "page_kicker": "调节闭环层",
                "page_title": "调节执行",
                "page_description": "这里先提供医生视频播放与执行反馈接口，后续可替换为更复杂的音乐、色彩或动作干预。",
                "plan": plan,
                "playback_url": plan.get("media_url") or doctor.get("video_url"),
            }
        ),
    )


@cf.route("/journey/history")
def history():
    if not _current_user():
        return redirect("/login")

    scales = list_scale_records(user_id=_current_user_id(), limit=20)
    plans = list_regulation_plans(_current_user_id(), limit=20)
    executions = list_execution_records(_current_user_id(), limit=20)
    counseling_rounds = load_history_from_db(_current_username(), limit=12)

    return render_template(
        "journey/history.html",
        **_journey_context(
            {
                "page_kicker": "调节闭环层",
                "page_title": "历史记录 / 再评估",
                "page_description": "把量表、调控方案、执行反馈和咨询摘要放到一条时间线上，形成可回看的闭环。",
                "timeline_items": _serialize_timeline(scales, plans, executions),
                "scales": scales,
                "plans": plans,
                "executions": executions,
                "counseling_rounds": counseling_rounds,
            }
        ),
    )


@cf.route("/journey/admin")
def admin():
    if not _current_user():
        return redirect("/login")
    if not _is_admin():
        abort(403)

    snapshot = get_admin_snapshot(limit=15)
    return render_template(
        "journey/admin.html",
        **_journey_context(
            {
                "page_kicker": "支撑与管理层",
                "page_title": "医生 / 研究后台",
                "page_description": "V1 先聚焦数据查看和导出视角，作为临床测试和研究整理的占位后台。",
                "snapshot": snapshot,
            }
        ),
    )


@cf.route("/journey/settings", methods=["GET", "POST"])
def settings():
    if not _current_user():
        return redirect("/login")

    user_id = _current_user_id()
    current_settings = merge_settings(get_user_settings(user_id))

    if request.method == "POST":
        save_user_settings(
            user_id,
            {
                "voice_broadcast": request.form.get("voice_broadcast") == "on",
                "capture_audio": request.form.get("capture_audio") == "on",
                "capture_camera": request.form.get("capture_camera") == "on",
                "capture_eeg": request.form.get("capture_eeg") == "on",
                "privacy_ack": request.form.get("privacy_ack") == "on",
                "debug_mode": request.form.get("debug_mode") == "on",
            },
        )
        flash("系统设置已更新。", "info")
        return redirect(url_for("care_flow.settings"))

    return render_template(
        "journey/settings.html",
        **_journey_context(
            {
                "page_kicker": "支撑与管理层",
                "page_title": "系统设置",
                "page_description": "集中管理语音播报、多模态权限、隐私授权和调试接口，为后续 EEG / 数字人接入预留入口。",
                "current_settings": current_settings,
            }
        ),
    )


@cf.route("/api/virtual-doctors")
def virtual_doctors_api():
    doctors = [_doctor_with_media(doctor) for doctor in get_doctor_catalog()]
    return jsonify({"success": True, "data": doctors})


@cf.route("/api/virtual-doctors/<doctor_slug>")
def virtual_doctor_detail_api(doctor_slug):
    doctor = _doctor_with_media(get_doctor_by_slug(doctor_slug))
    return jsonify({"success": True, "data": doctor})


@cf.route("/api/virtual-doctors/<doctor_slug>/playback")
def virtual_doctor_playback_api(doctor_slug):
    doctor = _doctor_with_media(get_doctor_by_slug(doctor_slug))
    return jsonify(
        {
            "success": True,
            "data": {
                "doctor": doctor["name"],
                "persona": doctor["persona"],
                "video_url": doctor["video_url"],
                "greeting": doctor["greeting"],
                "status": "placeholder-video-interface-ready",
            },
        }
    )


@cf.route("/api/regulation/plan")
def regulation_plan_api():
    if not _current_user():
        return jsonify({"success": False, "error": "unauthorized"}), 401

    phq_record, gad_record = _current_scale_pair()
    preview = build_regulation_preview(
        profile=get_patient_profile(_current_user_id()),
        preference=get_care_preference(_current_user_id()),
        settings=merge_settings(get_user_settings(_current_user_id())),
        phq_record=phq_record,
        gad_record=gad_record,
    )
    preview["video_url"] = url_for("get_video", filename=preview["video_file"])
    return jsonify(
        {
            "success": True,
            "data": preview,
            "status": "rule-engine-placeholder",
        }
    )


@cf.route("/api/regulation/playback/current")
def regulation_playback_api():
    if not _current_user():
        return jsonify({"success": False, "error": "unauthorized"}), 401

    plan = get_latest_regulation_plan(_current_user_id())
    if not plan:
        return jsonify({"success": False, "error": "no_plan"}), 404

    return jsonify(
        {
            "success": True,
            "data": {
                "plan_id": plan["id"],
                "title": plan["plan_title"],
                "media_url": plan.get("media_url"),
                "execution_mode": plan.get("execution_mode"),
                "status": plan.get("status"),
            },
        }
    )


@cf.route("/api/regulation/control", methods=["POST"])
def regulation_control_api():
    if not _current_user():
        return jsonify({"success": False, "error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action") or "noop").strip().lower()
    allowed_actions = {"prepare", "start", "pause", "resume", "stop", "complete"}
    if action not in allowed_actions:
        return jsonify({"success": False, "error": "invalid_action"}), 400

    plan = get_latest_regulation_plan(_current_user_id())
    return jsonify(
        {
            "success": True,
            "status": "placeholder-control-interface-ready",
            "data": {
                "accepted_action": action,
                "plan_id": plan["id"] if plan else None,
                "execution_mode": plan.get("execution_mode") if plan else None,
                "message": "当前仅保留调控控制接口占位，后续可在这里接入数字人、音乐或其他干预引擎。",
            },
        }
    )
