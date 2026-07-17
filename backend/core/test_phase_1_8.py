"""
core/test_phase_1_8.py — Phase 1.8 verification tests (Final Infrastructure Layer)

Covers: RuntimeFacade, runtime entry facades, service metadata, health
reporting, and architecture validation.

Run:
    conda activate lumina && python backend/core/test_phase_1_8.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_passed = 0
_failed = 0


def check(condition: bool, description: str) -> None:
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {description}")
    else:
        _failed += 1
        print(f"  [FAIL] {description}")


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run() -> None:
    from core.container import DependencyContainer
    from core.bootstrap import Bootstrapper
    from core.interfaces import IBrainState, IEventBus, IPipeline, IMemoryManager, IWorkspaceManager
    from core.context import ExecutionContextFactory
    from core.adapters import (
        BrainStateAdapter,
        EventBusAdapter,
        PipelineAdapter,
        ExecutionContextAdapter,
    )
    from core.runtime_facade import RuntimeFacade
    from core.runtime_entries import SocketIORuntimeEntry, AudioLoopRuntimeEntry
    from core.metadata import ServiceMetadataRegistry, ServiceMetadata, LIFECYCLE_TRANSIENT
    from core.health import HealthReporter, STATUS_OK
    from core.validation import ArchitectureValidator

    def _bootstrapped_container() -> DependencyContainer:
        c = DependencyContainer()
        Bootstrapper(container=c, kasa_agent=None).bootstrap()
        return c

    # ------------------------------------------------------------------
    section("RuntimeFacade — typed access")
    c = _bootstrapped_container()
    facade = RuntimeFacade(c)
    check(facade.brain_state is c.resolve(IBrainState), "facade.brain_state resolves the registered IBrainState")
    check(facade.event_bus is c.resolve(IEventBus), "facade.event_bus resolves the registered IEventBus")
    check(facade.pipeline is c.resolve(IPipeline), "facade.pipeline resolves the registered IPipeline")
    check(
        facade.execution_context_factory is c.resolve(ExecutionContextFactory),
        "facade.execution_context_factory resolves the registered factory",
    )
    check(isinstance(facade.brain_state_adapter, BrainStateAdapter), "facade.brain_state_adapter typed correctly")
    check(isinstance(facade.event_bus_adapter, EventBusAdapter), "facade.event_bus_adapter typed correctly")
    check(isinstance(facade.pipeline_adapter, PipelineAdapter), "facade.pipeline_adapter typed correctly")

    section("RuntimeFacade — no caching / transient correctness")
    check(facade.brain_state is facade.brain_state, "facade delegates to container singleton semantics")
    a = facade.new_execution_context_adapter()
    b = facade.new_execution_context_adapter()
    check(a is not b, "new_execution_context_adapter() returns a fresh transient each call")

    section("Runtime entry facades — scaffolding only")
    sio_entry = SocketIORuntimeEntry(facade)
    audio_entry = AudioLoopRuntimeEntry(facade)
    check(sio_entry.facade is facade, "SocketIORuntimeEntry holds the injected RuntimeFacade")
    check(audio_entry.facade is facade, "AudioLoopRuntimeEntry holds the injected RuntimeFacade")
    check(
        not hasattr(sio_entry, "on") and not hasattr(audio_entry, "start"),
        "entry facades expose no runtime handlers (scaffolding only)",
    )

    section("Service metadata")
    c = _bootstrapped_container()
    registry = c.resolve(ServiceMetadataRegistry)
    check(isinstance(registry, ServiceMetadataRegistry), "ServiceMetadataRegistry resolves from container")
    check(len(registry) == 11, "metadata registry describes all 11 infrastructure services (10 pre-4.4 + MemoryEngine from Phase 4.4)")
    brain_md = registry.get(repr(IBrainState))
    check(brain_md is not None and brain_md.name == "BrainState", "BrainState metadata present and named")
    check(brain_md.owner == "Phase 1.2", "BrainState metadata records owning phase")
    mem_md = registry.get(repr(IMemoryManager))
    check(mem_md is not None and mem_md.name == "MemoryStore", "MemoryStore metadata present and named")
    check(mem_md is not None and mem_md.owner == "Phase 4.2", "MemoryStore metadata records owning phase (4.2)")
    proj_md = registry.get(repr(IWorkspaceManager))
    check(proj_md is not None and proj_md.name == "ProjectManager", "ProjectManager metadata present and named")
    check(proj_md is not None and proj_md.owner == "Phase 4.2", "ProjectManager metadata records owning phase (4.2)")
    from core.interfaces import IKnowledgeManager
    km_md = registry.get(repr(IKnowledgeManager))
    check(km_md is not None and km_md.name == "MemoryEngine", "MemoryEngine metadata present and named")
    check(km_md is not None and km_md.owner == "Phase 4.4", "MemoryEngine metadata records owning phase (4.4)")
    ctx_md = registry.get(repr(ExecutionContextAdapter))
    check(
        ctx_md is not None and ctx_md.lifecycle == LIFECYCLE_TRANSIENT,
        "ExecutionContextAdapter metadata records transient lifecycle",
    )
    check(all(isinstance(m, ServiceMetadata) for m in registry.all()), "registry.all() returns ServiceMetadata records")

    section("Service metadata does not affect container behaviour")
    # The metadata registry is additive: core interface resolution is unchanged.
    check(c.resolve(IBrainState) is c.resolve(IBrainState), "IBrainState still a consistent singleton after metadata registration")
    check(c.is_registered(IEventBus), "IEventBus registration intact alongside metadata")

    section("Health reporting")
    c = _bootstrapped_container()
    reporter = HealthReporter(c)
    report = reporter.report()
    check(len(report) == 4, "health report covers the 4 core infrastructure services")
    check(all(h.status == STATUS_OK for h in report), "all infrastructure services report STATUS_OK")
    check(reporter.is_healthy() is True, "reporter.is_healthy() True on a bootstrapped container")
    pipeline_health = next(h for h in report if h.name == "RequestPipeline")
    check(pipeline_health.detail.get("sealed") is True, "pipeline health detail reports sealed=True")

    section("Health reporting — error isolation")
    empty = DependencyContainer()
    empty_reporter = HealthReporter(empty)
    empty_report = empty_reporter.report()
    check(all(h.status != STATUS_OK for h in empty_report), "unbootstrapped services report errors, not exceptions")
    check(empty_reporter.is_healthy() is False, "is_healthy() False on empty container (no raise)")

    section("Architecture validation — healthy container")
    c = _bootstrapped_container()
    result = ArchitectureValidator(c).validate()
    check(result.ok is True, "validation passes on a correctly bootstrapped container")
    check(len(result.errors) == 0, "no validation errors on healthy container")
    check(any("pipeline is sealed" in ch for ch in result.checks), "validation confirms pipeline sealed")
    check(
        any("BrainStateAdapter wraps" in ch for ch in result.checks),
        "validation confirms adapter wraps registered instance",
    )

    section("Architecture validation — broken container detected")
    broken = DependencyContainer()  # nothing registered
    broken_result = ArchitectureValidator(broken).validate()
    check(broken_result.ok is False, "validation fails on an empty container")
    check(len(broken_result.errors) > 0, "validation reports errors for missing registrations")

    section("Backward compatibility — legacy registrations untouched")
    c = _bootstrapped_container()
    bs = Bootstrapper(container=DependencyContainer(), kasa_agent=None)
    # Prove that adding Phase 1.8 registrations did not displace core bindings.
    check(c.resolve(IBrainState) is not None, "IBrainState resolves")
    check(c.resolve(IEventBus) is not None, "IEventBus resolves")
    check(c.resolve(IPipeline) is not None, "IPipeline resolves")
    check(c.resolve(ExecutionContextFactory) is not None, "ExecutionContextFactory resolves")

    section("PHASE 1.8 TEST SUMMARY")
    print(f"  Passed: {_passed}")
    print(f"  Failed: {_failed}")
    print("=" * 60)
    if _failed == 0:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    run()
