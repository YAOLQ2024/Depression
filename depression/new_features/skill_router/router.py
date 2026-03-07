#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified router for chat-triggered skills."""

from __future__ import annotations

import logging
from typing import List, Optional

from .base import RoutedSkill, SkillContext, SkillResult
from .registry import load_registered_skills

logger = logging.getLogger(__name__)

_skill_router: Optional["SkillRouter"] = None


class SkillRouter:
    """Resolve a chat request to the first matching skill."""

    def __init__(self, skills: Optional[List[RoutedSkill]] = None):
        self.skills = skills if skills is not None else load_registered_skills()

    def route(self, context: SkillContext) -> Optional[SkillResult]:
        for skill in self.skills:
            skill_name = skill.metadata().get("name", skill.__class__.__name__)
            try:
                if not skill.matches(context):
                    continue

                result = skill.execute(context)
                logger.info("skill routed: %s", skill_name)
                return result
            except Exception as exc:
                logger.error("skill route failed: %s", skill_name, exc_info=True)
                logger.warning("skill route failure detail: %s", exc)

        return None

    def list_skills(self) -> List[dict]:
        return [skill.metadata() for skill in self.skills]


def get_skill_router() -> SkillRouter:
    global _skill_router
    if _skill_router is None:
        _skill_router = SkillRouter()
    return _skill_router
