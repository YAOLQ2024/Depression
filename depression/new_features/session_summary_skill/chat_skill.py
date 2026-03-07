#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat router adapter for the session summary skill."""

from __future__ import annotations

import logging
import re
from typing import Dict

from new_features.skill_router.base import SkillContext, SkillResult

from .service import SessionSummarySkill

logger = logging.getLogger(__name__)

SUMMARY_TRIGGER_PHRASES = [
    "总结会话",
    "总结对话",
    "总结以上对话",
    "总结上述对话",
    "总结上面的对话",
    "总结前面的对话",
    "总结聊天",
    "对话总结",
    "会话总结",
    "总结一下",
    "帮我总结",
    "给我总结",
    "概括以上对话",
    "概括一下",
]


class SessionSummaryChatSkill:
    """Expose session summary as a routed chat skill."""

    def __init__(self):
        self.summary_skill = SessionSummarySkill()

    def metadata(self) -> Dict[str, object]:
        metadata = self.summary_skill.metadata()
        metadata.update(
            {
                "name": "session-summary",
                "trigger_examples": SUMMARY_TRIGGER_PHRASES[:6],
                "route_type": "chat-intent",
            }
        )
        return metadata

    def matches(self, context: SkillContext) -> bool:
        text = str(context.message or "").strip()
        if not text:
            return False

        normalized = re.sub(r"\s+", "", text)
        if any(phrase in normalized for phrase in SUMMARY_TRIGGER_PHRASES):
            return True

        has_summary_keyword = ("总结" in normalized) or ("概括" in normalized)
        has_dialog_context = any(
            keyword in normalized
            for keyword in ("对话", "会话", "聊天", "以上", "上述", "上面", "前面", "刚才")
        )
        return has_summary_keyword and has_dialog_context

    def execute(self, context: SkillContext) -> SkillResult:
        result = self.summary_skill.run(
            username=context.username,
            history=context.history if context.history else None,
            limit=100,
            style="structured",
            max_points=8,
            include_risk=True,
            timeout=120,
            max_tokens=1200,
        )

        summary_text = str(result.get("summary", "") or "").strip()
        if not summary_text:
            summary_text = "暂无可总结的会话内容。"

        logger.info("[session-summary] generated for user=%s", context.username)
        return SkillResult(
            skill_name="session-summary",
            response_text=summary_text,
            should_store=True,
            metadata=result,
        )
