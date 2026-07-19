"""
brain/planning/rule_planner.py — Phase 5.2 RulePlanner (Phase 5.4 Step 1: contract-aligned)

Deterministic BrainContext → Plan mapping. No AI, no Gemini, no network,
no model calls, no side effects.

Recognizes a deliberately tiny set of navigation intents that already exist
as deterministic behaviors in the legacy runtime:

  - navigation ("open/go to/show <panel>") → legacy.navigate_ui, params {panel, view}

The emitted skill_id (`legacy.navigate_ui`) and params (`panel`, `view`)
match the truth-aligned skill catalog (brain/skills/builtin.py) and the real
`navigate_ui` handler in core/tool_handlers.py, which reads fc.args["panel"].

Only navigation targets that map to a real UI panel are planned; any other
target returns None (abstain — legacy handles it). Memory verbs are NOT
planned here: no dispatchable memory tool exists in either legacy registry,
so memory continues to be handled by the legacy inline path in server.py's
user_input flow (extract_memory_candidates). This keeps every emitted
skill_id a member of the skill catalog.

Anything unrecognized → None (no Plan). The panel vocabulary mirrors
server.py's nav fast-path (quests/archive/events/settings/home); it is an
intentional data duplication (brain/* may not import server.py).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from brain.core.interfaces import IPlanner
from brain.core.models import BrainContext, Plan, Task

# Fallback skill id for navigation when no registry / no metadata match is
# available (Migration Strategy: preserve current behavior → zero regression).
_NAV_FALLBACK_SKILL_ID = "legacy.navigate_ui"
# Metadata category used to DISCOVER the navigation capability (Phase 5.5
# Step 3). Derived from SkillSpec tags; legacy.navigate_ui carries tag
# "navigation" as its first tag → category "navigation".
_NAV_CATEGORY = "navigation"

# Canonical UI panels and their spoken aliases → canonical panel name.
# Mirrors server.py nav fast-path vocabulary (quests/archive/events/settings/home).
_PANEL_ALIASES = {
    "quests": "quests",
    "quest": "quests",
    "questions": "quests",
    "question": "quests",
    "archive": "archive",
    "archives": "archive",
    "notes": "archive",
    "note": "archive",
    "knowledge archive": "archive",
    "events": "events",
    "event": "events",
    "reminders": "events",
    "reminder": "events",
    "calendar": "events",
    "settings": "settings",
    "setting": "settings",
    "home": "home",
    "main": "home",
    "dashboard": "home",
}

# View filters recognized in the request text (else "all").
_VIEW_KEYWORDS = ("completed", "active", "side")

_NAV_RE = re.compile(
    r"^(?:open|go to|show|switch to)\s+(?:the\s+|my\s+)?(?P<target>[\w\s]{1,40}?)"
    r"(?:\s+(?:panel|page|view|tab))?$",
    re.IGNORECASE,
)


class RulePlanner(IPlanner):
    """Deterministic pattern-based planner."""

    def __init__(self, skill_registry: Optional[Any] = None) -> None:
        """
        Phase 5.5 Step 3: optionally accept a SkillRegistry for metadata-driven
        capability discovery. Backward-compatible — RulePlanner() with no args
        keeps working and uses the hardcoded fallback (identical behavior).
        """
        self._registry = skill_registry

    def _resolve_nav_skill_id(self) -> str:
        """
        Discover the navigation skill id via deterministic capability ranking
        (Phase 5.5 Step 4).

        Delegates ALL ranking to CapabilityResolver — the planner holds no
        ranking logic. Falls back to the hardcoded id when no registry is
        injected or no capability is resolved, guaranteeing zero runtime
        regression (Migration Strategy).
        """
        if self._registry is not None:
            try:
                from brain.skills.resolver import CapabilityResolver
                best = CapabilityResolver(self._registry).resolve(category=_NAV_CATEGORY)
                if best is not None:
                    return best.id  # deterministic highest-score winner
            except Exception:
                pass
        return _NAV_FALLBACK_SKILL_ID

    def plan(self, context: BrainContext) -> Optional[Plan]:
        """
        Evaluate navigation rules against the request text.

        Returns a single-task navigation Plan when the target maps to a real
        UI panel; None otherwise. Voice-tool requests (pre-decided by Gemini
        Live) and empty text are never planned here.
        """
        text = (context.request.text or "").strip()
        if not text or context.request.tool_call is not None:
            return None

        normalized = text.rstrip(".!?").strip()
        match = _NAV_RE.match(normalized)
        if match is None:
            return None

        target = (match.group("target") or "").strip().lower()

        # Detect and strip a leading view filter embedded in the target,
        # e.g. "show completed quests" → view="completed", target="quests".
        lowered = normalized.lower()
        view = "all"
        for v in _VIEW_KEYWORDS:
            if v in lowered:
                view = v
                if target.startswith(v + " "):
                    target = target[len(v) + 1:].strip()
                break

        panel = _PANEL_ALIASES.get(target)
        if panel is None:
            # Unknown navigation target → abstain; legacy path handles it.
            return None

        task = Task(
            intent="navigate",
            skill_id=self._resolve_nav_skill_id(),
            params={"panel": panel, "view": view},
        )
        return Plan(
            tasks=[task],
            strategy="sequential",
            confidence=1.0,
            rationale="RulePlanner deterministic match: navigate",
        )
