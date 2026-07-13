"""
core/validation.py — Lumina V2 Architecture Validation (Phase 1.8)

Verifies that the infrastructure assembled by the Bootstrapper is
internally consistent: expected registrations exist, services resolve,
the pipeline is sealed, adapters wrap the correct instances, and the
container is in a coherent state.

This is a diagnostic/read-only module. It never mutates the container or
any service, and it is not on any runtime path. It is intended to be run
at startup (optionally) or from tests to catch wiring mistakes early.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from core.container import DependencyContainer
from core.interfaces import IBrainState, IEventBus, IPipeline
from core.context import ExecutionContextFactory
from core.adapters import (
    BrainStateAdapter,
    EventBusAdapter,
    ExecutionContextAdapter,
    PipelineAdapter,
)


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of the architecture validation pass."""

    ok: bool
    checks: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ArchitectureValidator:
    """
    Runs a series of consistency checks against a bootstrapped container.

    Each check appends to either `checks` (passed) or `errors` (failed).
    validate() never raises for a failed check — it collects and returns
    all findings so callers can decide how to react.
    """

    def __init__(self, container: DependencyContainer) -> None:
        self._container = container
        self._checks: List[str] = []
        self._errors: List[str] = []

    def validate(self) -> ValidationResult:
        self._validate_registrations()
        self._validate_resolution()
        self._validate_pipeline_integrity()
        self._validate_adapter_integrity()
        self._validate_container_consistency()
        return ValidationResult(
            ok=not self._errors,
            checks=list(self._checks),
            errors=list(self._errors),
        )

    # ------------------------------------------------------------------

    def _expect(self, condition: bool, label: str) -> None:
        if condition:
            self._checks.append(label)
        else:
            self._errors.append(label)

    def _validate_registrations(self) -> None:
        for iface in (IBrainState, IEventBus, IPipeline, ExecutionContextFactory):
            self._expect(
                self._container.is_registered(iface),
                f"registration present: {iface.__name__}",
            )
        for adapter in (BrainStateAdapter, EventBusAdapter, PipelineAdapter, ExecutionContextAdapter):
            self._expect(
                self._container.is_registered(adapter),
                f"registration present: {adapter.__name__}",
            )

    def _validate_resolution(self) -> None:
        for iface in (IBrainState, IEventBus, IPipeline, ExecutionContextFactory):
            try:
                self._container.resolve(iface)
                self._checks.append(f"resolves: {iface.__name__}")
            except Exception as e:  # noqa: BLE001
                self._errors.append(f"resolve failed: {iface.__name__} ({e})")

    def _validate_pipeline_integrity(self) -> None:
        try:
            pipeline = self._container.resolve(IPipeline)
        except Exception as e:  # noqa: BLE001
            self._errors.append(f"pipeline unresolved: {e}")
            return
        self._expect(getattr(pipeline, "is_sealed", False) is True, "pipeline is sealed")
        self._expect(
            getattr(pipeline, "middleware_count", None) == 0,
            "pipeline has no middleware (infrastructure-only)",
        )

    def _validate_adapter_integrity(self) -> None:
        try:
            brain = self._container.resolve(IBrainState)
            bus = self._container.resolve(IEventBus)
            pipeline = self._container.resolve(IPipeline)
            brain_adapter = self._container.resolve(BrainStateAdapter)
            bus_adapter = self._container.resolve(EventBusAdapter)
            pipe_adapter = self._container.resolve(PipelineAdapter)
        except Exception as e:  # noqa: BLE001
            self._errors.append(f"adapter integrity unresolved: {e}")
            return

        self._expect(
            getattr(brain_adapter, "_brain_state", None) is brain,
            "BrainStateAdapter wraps the registered IBrainState instance",
        )
        self._expect(
            getattr(bus_adapter, "_event_bus", None) is bus,
            "EventBusAdapter wraps the registered IEventBus instance",
        )
        self._expect(
            getattr(pipe_adapter, "_pipeline", None) is pipeline,
            "PipelineAdapter wraps the registered IPipeline instance",
        )

        # ExecutionContextAdapter is transient — two resolves must differ.
        try:
            a = self._container.resolve(ExecutionContextAdapter)
            b = self._container.resolve(ExecutionContextAdapter)
            self._expect(a is not b, "ExecutionContextAdapter is transient (distinct per resolve)")
        except Exception as e:  # noqa: BLE001
            self._errors.append(f"ExecutionContextAdapter resolve failed: {e}")

    def _validate_container_consistency(self) -> None:
        # Singleton interfaces must return the same instance on repeat resolve.
        for iface in (IBrainState, IEventBus, IPipeline):
            try:
                self._expect(
                    self._container.resolve(iface) is self._container.resolve(iface),
                    f"singleton consistency: {iface.__name__}",
                )
            except Exception as e:  # noqa: BLE001
                self._errors.append(f"singleton check failed: {iface.__name__} ({e})")
