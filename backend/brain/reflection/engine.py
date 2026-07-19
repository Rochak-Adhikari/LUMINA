"""
brain/reflection/engine.py — Phase 5.7.2: ReflectionEngine

Pure, deterministic, read-only post-execution evaluator. Computes a Reflection
strictly from information already present in the inputs — no randomness, no
timestamps of its own, no UUID generation, no external calls.

Imports only brain.core.models + stdlib/typing/abc. Zero dependency on
Planner, SkillManager, Executor, BrainCore, WorkspaceMemory, ProjectManager,
MemoryEngine, server, or lumina.
"""

from __future__ import annotations

from typing import Any, List, Optional

from brain.reflection.interfaces import IReflectionEngine
from brain.core.models import BrainRequest, BrainContext, Plan, Reflection


class ReflectionEngine(IReflectionEngine):
    """Deterministic Reflection producer. Owns no state."""

    def reflect(
        self,
        request: BrainRequest,
        plan: Optional[Plan],
        results: List[Any],
        context: Optional[BrainContext] = None,
    ) -> Reflection:
        results = list(results or [])

        # skills_used: skill_id of every result that carries one (order kept).
        skills_used = [
            sid for sid in (getattr(r, "skill_id", None) for r in results)
            if sid
        ]

        # failures: one record per non-ok result (deterministic shape).
        failures: List[dict] = []
        for r in results:
            if not getattr(r, "ok", False):
                failures.append({
                    "skill_id": getattr(r, "skill_id", "") or "",
                    "error": getattr(r, "error", None),
                })

        # success: a plan with tasks whose every result succeeded. No plan or
        # no results → not a success (nothing executed).
        success = bool(results) and not failures

        # latency_ms: deterministic sum of provided per-result latencies
        # (None when none were supplied — never invents a timestamp).
        latencies = [
            r.latency_ms for r in results
            if getattr(r, "latency_ms", None) is not None
        ]
        latency_ms: Optional[float] = sum(latencies) if latencies else None

        # confidence: carry the plan's confidence when fully successful,
        # else scale by the success ratio (deterministic, in [0,1]).
        plan_conf = getattr(plan, "confidence", 1.0) if plan is not None else 1.0
        if results:
            ratio = (len(results) - len(failures)) / len(results)
        else:
            ratio = 0.0
        confidence = max(0.0, min(1.0, plan_conf * ratio))

        # notes: deterministic human-readable summary.
        if not results:
            notes = "No skills executed."
        elif success:
            notes = f"All {len(results)} task(s) succeeded."
        else:
            notes = f"{len(failures)} of {len(results)} task(s) failed."

        return Reflection(
            request_id=request.request_id,
            plan_id=(getattr(plan, "plan_id", None) if plan is not None else None),
            success=success,
            failures=failures,
            latency_ms=latency_ms,
            skills_used=skills_used,
            corrections=[],  # deterministic default; populated by later phases
            confidence=confidence,
            notes=notes,
        )
