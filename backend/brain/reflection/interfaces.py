"""
brain/reflection/interfaces.py — Phase 5.7.2: Reflection contract

IReflectionEngine: the read-only post-execution evaluation contract.
Behaviour only — no state, no side effects. Produces the existing Reflection
value object (brain/core/models.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from brain.core.models import BrainRequest, BrainContext, Plan, Reflection


class IReflectionEngine(ABC):
    """Read-only, deterministic post-execution evaluator."""

    @abstractmethod
    def reflect(
        self,
        request: BrainRequest,
        plan: Optional[Plan],
        results: List[Any],
        context: Optional[BrainContext] = None,
    ) -> Reflection:
        """
        Produce a Reflection for one completed request.

        Pure function: the same inputs always yield the same Reflection. Never
        executes, mutates, or calls out. *results* is a list of SkillResult-
        like objects (skill_id / ok / error / latency_ms).
        """
