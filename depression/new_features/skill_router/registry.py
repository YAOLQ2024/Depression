#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registry for all chat-triggered skills."""

from __future__ import annotations

import logging
from typing import List

from .base import RoutedSkill

logger = logging.getLogger(__name__)


def load_registered_skills() -> List[RoutedSkill]:
    """Load all skills that should participate in chat routing."""
    skills: List[RoutedSkill] = []

    try:
        from new_features.session_summary_skill.chat_skill import SessionSummaryChatSkill

        skills.append(SessionSummaryChatSkill())
    except Exception as exc:
        logger.warning("session_summary skill not registered: %s", exc)

    return skills
