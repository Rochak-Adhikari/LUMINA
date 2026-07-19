"""
brain/evolution/store.py — Phase 6.1: in-memory append-only EvolutionStore

Isolated observation store (ADR-0008). Append-only: no update, no delete, no
mutation, no rewriting. Deterministic — records kept in insertion order.

No filesystem, no runtime imports, no DI, no singleton. Owns observation
records only. Separate from every runtime store.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from brain.evolution.interfaces import IEvolutionStore
from brain.evolution.models import EvolutionObservation


class EvolutionStore(IEvolutionStore):
    """In-memory, append-only observation store."""

    def __init__(self) -> None:
        self._records: List[EvolutionObservation] = []
        self._by_id: Dict[str, EvolutionObservation] = {}

    def append(self, observation: EvolutionObservation) -> None:
        """Append one observation. First write wins per id — an id already
        present is ignored (append-only; never overwrites)."""
        if observation.id in self._by_id:
            return
        self._records.append(observation)
        self._by_id[observation.id] = observation

    def get(self, observation_id: str) -> Optional[EvolutionObservation]:
        return self._by_id.get(observation_id)

    def list(self) -> List[EvolutionObservation]:
        return list(self._records)  # copy — callers can't mutate internals

    def count(self) -> int:
        return len(self._records)
