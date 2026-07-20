"""
brain/skill_creator/lifecycle_manager.py — Phase 7.9: LifecycleManager

Pipeline stage 08 (Lifecycle). Consumes a RegistryEntry plus an EXPLICIT
transition intent supplied by the caller and appends one immutable
LifecycleEvent to an append-only log. Never edits or replaces the RegistryEntry
or any prior event — supersession/archival is another appended event.

Rules:
  - Gated: only a registered entry (registration_status == "registered") may
    transition; otherwise status="skipped", skipped_reason="not_registered",
    nothing appended.
  - Legal transitions only (see _ALLOWED); an illegal transition yields
    status="skipped", skipped_reason="invalid_transition", nothing appended.
  - Default state for a key with no events is "registered".

Deterministic: the event is a pure function of (entry, current state,
transition). No timestamps, uuids, generated ids, randomness, hashing,
filesystem, network, or execution.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
typing.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from brain.skill_creator.interfaces import ILifecycleManager
from brain.skill_creator.models import RegistryEntry, LifecycleEvent

_DEFAULT_STATE = "registered"

# Legal transitions: (transition intent) -> {from_state: to_state}. A transition
# is legal only if the current state is a key in the intent's mapping.
_ALLOWED: Dict[str, Dict[str, str]] = {
    "activate": {"registered": "active", "inactive": "active"},
    "deactivate": {"active": "inactive"},
    "archive": {"registered": "archived", "active": "archived", "inactive": "archived"},
    "supersede": {"active": "superseded", "inactive": "superseded"},
}


class LifecycleManager(ILifecycleManager):
    """Append-only, deterministic skill-lifecycle event log."""

    def __init__(self) -> None:
        self._events: List[LifecycleEvent] = []

    def transition(
        self,
        registry_entry: RegistryEntry,
        transition: str,
        *,
        actor: str = "",
        transition_reason: str = "",
    ) -> LifecycleEvent:
        key = registry_entry.registry_key

        # Gate: only registered entries have a lifecycle.
        if registry_entry.registration_status != "registered":
            return self._skip(registry_entry, transition, actor, transition_reason,
                              previous_state="", reason="not_registered")

        current = self.current_state(key)
        target = _ALLOWED.get(transition, {}).get(current)
        if target is None:
            return self._skip(registry_entry, transition, actor, transition_reason,
                              previous_state=current, reason="invalid_transition")

        event = LifecycleEvent(
            blueprint_id=registry_entry.blueprint_id,
            recommendation_id=registry_entry.recommendation_id,
            registry_key=key,
            previous_state=current,
            new_state=target,
            transition=transition,
            transition_reason=transition_reason,
            actor=actor,
            status="transitioned",
        )
        self._events.append(event)  # append-only
        return event

    def events(self) -> List[LifecycleEvent]:
        return list(self._events)  # copy — never expose mutable state

    def current_state(self, registry_key: str) -> str:
        # Latest transitioned event for the key wins; default "registered".
        for event in reversed(self._events):
            if event.registry_key == registry_key and event.status == "transitioned":
                return event.new_state
        return _DEFAULT_STATE

    # ---- helpers ------------------------------------------------------

    @staticmethod
    def _skip(entry: RegistryEntry, transition: str, actor: str,
              transition_reason: str, *, previous_state: str, reason: str) -> LifecycleEvent:
        # Skipped events are NOT appended — they carry no state change.
        return LifecycleEvent(
            blueprint_id=entry.blueprint_id,
            recommendation_id=entry.recommendation_id,
            registry_key=entry.registry_key,
            previous_state=previous_state,
            new_state=previous_state,
            transition=transition,
            transition_reason=transition_reason,
            actor=actor,
            status="skipped",
            skipped_reason=reason,
        )
