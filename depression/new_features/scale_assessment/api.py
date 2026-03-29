"""Blueprint for PHQ-9 / GAD-7 structured assessment."""

from __future__ import annotations

import time

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .definitions import get_scale_definition, list_scale_definitions
from .engine import ScaleValidationError, evaluate_scale
from .repository import create_scale_record, ensure_scale_tables, get_scale_record

scale_assessment_bp = Blueprint(
    "scale_assessment",
    __name__,
    template_folder="templates",
)

ensure_scale_tables()


@scale_assessment_bp.route("/scales", methods=["GET"])
def scale_home():
    return render_template(
        "scale_assessment/index.html",
        scales=list_scale_definitions(),
    )


@scale_assessment_bp.route("/scales/<scale_slug>", methods=["GET"])
def scale_form(scale_slug):
    scale_def = get_scale_definition(scale_slug)
    if not scale_def:
        flash("暂不支持该量表。", "error")
        return redirect(url_for("scale_assessment.scale_home"))

    return render_template(
        "scale_assessment/fill.html",
        scale=scale_def,
        started_at=int(time.time()),
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
    record = get_scale_record(record_id)
    if not record:
        flash("未找到该量表结果。", "error")
        return redirect(url_for("scale_assessment.scale_home"))

    userinfo = session.get("userinfo", {})
    current_name = userinfo.get("name") or userinfo.get("username")
    is_admin = str(userinfo.get("role", "")) in {"1", "2"}
    if not is_admin and record["username"] != current_name:
        flash("你无权查看该量表结果。", "error")
        return redirect(url_for("scale_assessment.scale_home"))

    scale_def = get_scale_definition(record["scale_slug"])
    if not scale_def:
        flash("量表定义不存在，无法展示结果。", "error")
        return redirect(url_for("scale_assessment.scale_home"))

    option_map = {option["value"]: option["label"] for option in scale_def["options"]}
    item_rows = []
    for item in scale_def["items"]:
        score = record["answers"].get(item["id"])
        item_rows.append(
            {
                "index": item["index"],
                "text": item["text"],
                "score": score,
                "answer_label": option_map.get(score, "-"),
            }
        )

    return render_template(
        "scale_assessment/result.html",
        record=record,
        scale=scale_def,
        item_rows=item_rows,
    )
