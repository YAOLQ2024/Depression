#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Base contracts for chat-triggered skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class SkillContext:
    """Context passed from the main chat endpoint to routed skills."""

    username: str
    message: str
    history: Optional[List[Any]] = None
    include_emotion: bool = False
    emotion_context: Any = None
    stream: bool = True
    web_search: bool = False
    request_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Normalized response returned by a routed skill."""

    skill_name: str
    response_text: str
    should_store: bool = True
    emotion_context: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class RoutedSkill(Protocol):
    """Protocol for all chat-triggered skills."""

    def metadata(self) -> Dict[str, Any]:
        ...

    def matches(self, context: SkillContext) -> bool:
        ...

    def execute(self, context: SkillContext) -> SkillResult:
        ...
