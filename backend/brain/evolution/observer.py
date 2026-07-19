"""
brain/evolution/observer.py — Phase 6.1: EvolutionObserver

The observation entry point of the Evolution Engine (ADR-0008). Reads a
Reflection (duck-typed), builds an immutable EvolutionObservation, and appends
it to the injected store. Returns the stored record; returns nothing to the
runtime and never influences execution.

Deterministic: the observation id is derived from the reflection's identifiers
(no UUID generation); the timestamp is caller-supplied and never generated
inline. Read-only over the reflection — copies primitive values only, never the
reflection object or any runtime reference.

Analysis-layer only: NO analysis, NO recommendations, NO evolution, NO runtime
mutation. Just observe + persist.
"""

from __future__ import annotations

from typing import Any, Optional

from brain.evolution.interfaces import IEvolutionObserver, IEvolutionStore
from brain.evolution.models import EvolutionObservation


class EvolutionObserver(IEvolutionObserver):
    """Observes Reflection → stores EvolutionObservation. No runtime effect."""

    def __init__(self, store: IEvolutionStore) -> None:
        self._store = store

    def observe(
        self,
        reflection: Any,
        *,
        timestamp: Optional[float] = None,
        planner_used: str = "",
        strategy_used: str = "",
    ) -> EvolutionObservation:
        reflection_id = str(getattr(reflection, "request_id", "") or "")
        plan_id = getattr(reflection, "plan_id", None)
        success = bool(getattr(reflection, "success", False))
        latency = getattr(reflection, "latency_ms", None)

        observation = EvolutionObservation(
            id=self._derive_id(reflection_id, plan_id),
            timestamp=timestamp,
            reflection_id=reflection_id,
            plan_id=plan_id,
            planner_used=planner_used,
            strategy_used=strategy_used,
            success=success,
            latency=latency,
        )
        self._store.append(observation)
        return observation

    @staticmethod
    def _derive_id(reflection_id: str, plan_id: Optional[str]) -> str:
        """Deterministic id from reflection identifiers — no UUID, no time."""
        return f"obs:{reflection_id}:{plan_id or ''}"
