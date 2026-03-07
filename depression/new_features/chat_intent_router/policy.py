#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intent policy for ordinary chat requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

INTENT_CASUAL = "casual"
INTENT_IDENTITY = "identity"
INTENT_REALTIME = "realtime"
INTENT_PSYCHOLOGY = "psychology"
INTENT_GENERAL = "general"

GREETING_REPLY = (
    "你好，我在。你可以直接告诉我你的问题；如果你问的是日期、天气、新闻等最新信息，请先开启联网搜索。"
)
IDENTITY_REPLY = (
    "我是这套系统里的心理健康咨询助手，主要负责咨询对话、量表相关说明和情绪支持。"
    " 如果你想问日期、天气、新闻这类最新信息，请先开启联网搜索。"
)
THANKS_REPLY = "不客气。你可以继续告诉我你现在想聊的问题。"
REALTIME_REFUSAL = "这个问题需要最新信息才能准确回答。请先开启联网搜索，再向我提问。"
REALTIME_UNAVAILABLE = "当前环境未配置联网搜索，暂时无法准确回答这类最新信息问题。"

CASUAL_KEYWORDS = (
    "你好",
    "您好",
    "嗨",
    "哈喽",
    "hello",
    "hi",
    "早上好",
    "下午好",
    "晚上好",
    "在吗",
)
THANKS_KEYWORDS = ("谢谢", "多谢", "感谢", "辛苦了")
IDENTITY_KEYWORDS = (
    "你是谁",
    "你叫什么",
    "介绍一下你自己",
    "介绍下你自己",
    "你的身份",
    "你是干什么的",
    "你能做什么",
    "你可以做什么",
)
REALTIME_KEYWORDS = (
    "今天几号",
    "今天星期几",
    "今天星期几",
    "今天日期",
    "几号",
    "星期",
    "日期",
    "时间",
    "几点",
    "天气",
    "温度",
    "新闻",
    "最新",
    "实时",
    "刚刚",
    "股价",
    "汇率",
    "热搜",
    "比分",
)
PSYCHOLOGY_KEYWORDS = (
    "抑郁",
    "焦虑",
    "心理",
    "情绪",
    "压力",
    "崩溃",
    "绝望",
    "烦",
    "难受",
    "难过",
    "失眠",
    "睡不着",
    "想哭",
    "不想活",
    "自杀",
    "自残",
    "咨询",
    "量表",
    "phq",
    "gad",
    "hamd",
    "sds",
    "脑电",
)


@dataclass(frozen=True)
class ChatIntentDecision:
    """Decision returned by the chat intent classifier."""

    intent: str
    use_rag: bool
    use_web_search: bool
    direct_response: Optional[str]
    response_style: str
    reason: str


def classify_chat_intent(
    message: str,
    *,
    enable_web_search: bool,
    search_available: bool,
) -> ChatIntentDecision:
    """Classify the current request into a small set of chat intents."""
    normalized = _normalize(message)

    if _contains_any(normalized, REALTIME_KEYWORDS):
        if enable_web_search and search_available:
            return ChatIntentDecision(
                intent=INTENT_REALTIME,
                use_rag=False,
                use_web_search=True,
                direct_response=None,
                response_style="realtime",
                reason="latest-info-with-search",
            )

        return ChatIntentDecision(
            intent=INTENT_REALTIME,
            use_rag=False,
            use_web_search=False,
            direct_response=REALTIME_UNAVAILABLE if enable_web_search else REALTIME_REFUSAL,
            response_style="realtime",
            reason="latest-info-without-search",
        )

    if _contains_any(normalized, PSYCHOLOGY_KEYWORDS):
        return ChatIntentDecision(
            intent=INTENT_PSYCHOLOGY,
            use_rag=True,
            use_web_search=False,
            direct_response=None,
            response_style="psychology",
            reason="psychology-keywords",
        )

    if _contains_any(normalized, IDENTITY_KEYWORDS):
        return ChatIntentDecision(
            intent=INTENT_IDENTITY,
            use_rag=False,
            use_web_search=False,
            direct_response=IDENTITY_REPLY,
            response_style="identity",
            reason="identity-keywords",
        )

    if _contains_any(normalized, THANKS_KEYWORDS):
        return ChatIntentDecision(
            intent=INTENT_CASUAL,
            use_rag=False,
            use_web_search=False,
            direct_response=THANKS_REPLY,
            response_style="casual",
            reason="thanks-keywords",
        )

    if _contains_any(normalized, CASUAL_KEYWORDS):
        return ChatIntentDecision(
            intent=INTENT_CASUAL,
            use_rag=False,
            use_web_search=False,
            direct_response=GREETING_REPLY,
            response_style="casual",
            reason="casual-keywords",
        )

    return ChatIntentDecision(
        intent=INTENT_GENERAL,
        use_rag=False,
        use_web_search=False,
        direct_response=None,
        response_style="general",
        reason="default-general",
    )


def _normalize(message: str) -> str:
    return "".join(str(message or "").lower().split())


def _contains_any(text: str, keywords) -> bool:
    return any(keyword in text for keyword in keywords)
