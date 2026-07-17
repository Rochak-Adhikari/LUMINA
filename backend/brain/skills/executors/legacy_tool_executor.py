"""
brain/skills/executors/legacy_tool_executor.py — Phase 5.2 legacy adapter

Adapts today's existing runtime execution path into the executor shape the
SkillManager dispatches to. Introduces NO new behavior:

  - The actual legacy dispatch is an INJECTED async/sync callable
    (signature: dispatch(provider_ref: str, params: dict) -> Any).
  - Phase 5.2 registers this executor UNBOUND (dispatch=None): running a
    task returns a failed SkillResult explaining nothing is wired yet.
    Binding the real legacy dispatch is a later-milestone decision made at
    the runtime seam — this module never imports server.py or agents.
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Callable, Dict, Optional

from brain.skills.models import SkillResult, SkillSpec


class LegacyToolExecutor:
    """Executor for SkillSpec.provider == 'legacy'."""

    provider = "legacy"

    def __init__(self, dispatch: Optional[Callable[..., Any]] = None) -> None:
        self._dispatch = dispatch

    def supports(self, spec: SkillSpec) -> bool:
        """True if this executor can run *spec*."""
        return spec.provider == self.provider

    async def run(self, spec: SkillSpec, params: Dict[str, Any]) -> SkillResult:
        """
        Execute *spec* through the injected legacy dispatch.

        Unbound dispatch → failed SkillResult (never raises): Phase 5.2 has
        no runtime wiring, so execution is intentionally inert.
        """
        if self._dispatch is None:
            return SkillResult(
                skill_id=spec.id,
                ok=False,
                error="LegacyToolExecutor has no dispatch bound (Phase 5.2: "
                      "runtime wiring intentionally deferred).",
            )
        start = time.perf_counter()
        try:
            outcome = self._dispatch(spec.provider_ref, params)
            if inspect.isawaitable(outcome):
                outcome = await outcome
            return SkillResult(
                skill_id=spec.id,
                ok=True,
                output=outcome,
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )
        except Exception as e:
            return SkillResult(
                skill_id=spec.id,
                ok=False,
                error=f"{type(e).__name__}: {e}",
                latency_ms=(time.perf_counter() - start) * 1000.0,
            )
