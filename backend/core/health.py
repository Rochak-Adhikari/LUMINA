"""
core/health.py — Lumina V2 Infrastructure Health Reporting (Phase 1.8)

Lightweight, read-only health/status reporting for the infrastructure
services built in Phases 1.2–1.6. This module inspects already-registered
services and reports their status; it performs no mutation, no business
logic, and nothing on any runtime path.

A "healthy" infrastructure service here simply means: it resolves from the
container and answers a trivial read-only probe without raising. This is
deliberately shallow — it verifies wiring, not behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.container import DependencyContainer
from core.interfaces import IBrainState, IEventBus, IPipeline
from core.context import ExecutionContextFactory


STATUS_OK = "ok"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class ServiceHealth:
    """Health record for a single infrastructure service."""

    name: str
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


class HealthReporter:
    """
    Produces read-only health reports for infrastructure services.

    Each probe resolves a service from the container and calls a trivial,
    side-effect-free accessor. Any exception is captured and reported as
    STATUS_ERROR rather than propagated — a health check must never break
    the caller.
    """

    def __init__(self, container: DependencyContainer) -> None:
        self._container = container

    def report(self) -> List[ServiceHealth]:
        """Return a health record for each known infrastructure service."""
        return [
            self._probe("BrainState", self._probe_brain_state),
            self._probe("EventBus", self._probe_event_bus),
            self._probe("ExecutionContextFactory", self._probe_context_factory),
            self._probe("RequestPipeline", self._probe_pipeline),
        ]

    def is_healthy(self) -> bool:
        """True if every probed service reports STATUS_OK."""
        return all(h.status == STATUS_OK for h in self.report())

    # ------------------------------------------------------------------
    # Individual probes — each returns a detail dict or raises.
    # ------------------------------------------------------------------

    def _probe_brain_state(self) -> Dict[str, Any]:
        brain = self._container.resolve(IBrainState)
        status = brain.get_status()
        return {"resolved": True, "status_keys": sorted(status.keys())}

    def _probe_event_bus(self) -> Dict[str, Any]:
        bus = self._container.resolve(IEventBus)
        status = bus.get_status()
        return {"resolved": True, "subscription_count": status.get("subscription_count", 0)}

    def _probe_context_factory(self) -> Dict[str, Any]:
        factory = self._container.resolve(ExecutionContextFactory)
        ctx = factory.create()
        return {"resolved": True, "sample_context_id": ctx.context_id[:8] + "…"}

    def _probe_pipeline(self) -> Dict[str, Any]:
        pipeline = self._container.resolve(IPipeline)
        return {
            "resolved": True,
            "sealed": getattr(pipeline, "is_sealed", None),
            "middleware_count": getattr(pipeline, "middleware_count", None),
        }

    # ------------------------------------------------------------------

    def _probe(self, name: str, fn) -> ServiceHealth:
        try:
            detail = fn()
            return ServiceHealth(name=name, status=STATUS_OK, detail=detail)
        except Exception as e:  # noqa: BLE001 — health checks must not raise
            return ServiceHealth(
                name=name,
                status=STATUS_ERROR,
                detail={"error": type(e).__name__, "message": str(e)},
            )
