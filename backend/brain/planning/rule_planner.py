"""
brain/planning/rule_planner.py — Phase 5.2 RulePlanner

Deterministic BrainContext → Plan mapping. No AI, no Gemini, no network,
no model calls, no side effects.

Recognizes a deliberately tiny set of intents that already exist as
deterministic behaviors in the legacy runtime:

  - navigation  ("open/go to/show <panel>")            → legacy.navigation
  - memory verbs ("remember/forget/what do you remember") → legacy.memory

Anything else → None (no Plan). Alignment with server.py ActionRouter's
exact patterns is deferred to the milestone that wires routing (reading
server.py is out of scope for 5.2).
"""

from __future__ import annotations

import re
from typing import Optional

from brain.core.interfaces import IPlanner
from brain.core.models import BrainContext, Plan, Task

# (compiled pattern, skill_id, intent, param-group name)
_RULES = [
    (
        re.compile(r"^(?:open|go to|show|switch to)\s+(?:the\s+)?(?P<target>[\w\s]{1,40}?)(?:\s+(?:panel|page|view|tab))?$", re.IGNORECASE),
        "legacy.navigation",
        "navigate",
        "target",
    ),
    (
        re.compile(r"^remember\s+(?:that\s+)?(?P<content>.+)$", re.IGNORECASE),
        "legacy.memory",
        "memory.remember",
        "content",
    ),
    (
        re.compile(r"^forget\s+(?:that\s+|about\s+)?(?P<content>.+)$", re.IGNORECASE),
        "legacy.memory",
        "memory.forget",
        "content",
    ),
    (
        re.compile(r"^what\s+do\s+you\s+remember(?:\s+about\s+(?P<content>.+))?[\?\.]?$", re.IGNORECASE),
        "legacy.memory",
        "memory.recall",
        "content",
    ),
]


class RulePlanner(IPlanner):
    """Deterministic pattern-based planner."""

    def plan(self, context: BrainContext) -> Optional[Plan]:
        """
        Evaluate rules against the request text.

        Returns a single-task Plan on match, None otherwise. Voice-tool
        requests (pre-decided by Gemini Live) and empty text are never
        planned here.
        """
        text = (context.request.text or "").strip()
        if not text or context.request.tool_call is not None:
            return None

        normalized = text.rstrip(".!?").strip()
        for pattern, skill_id, intent, group in _RULES:
            match = pattern.match(normalized)
            if match is None:
                continue
            value = (match.groupdict().get(group) or "").strip()
            params = {group: value} if value else {}
            task = Task(intent=intent, skill_id=skill_id, params=params)
            return Plan(
                tasks=[task],
                strategy="sequential",
                confidence=1.0,
                rationale=f"RulePlanner deterministic match: {intent}",
            )
        return None
