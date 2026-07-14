"""
core/test_phase_1_4.py — Phase 1.4 verification tests (Execution Context Layer)

Run:
    conda activate lumina && python backend/core/test_phase_1_4.py
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
    from core.context import ExecutionContext, ExecutionContextFactory
    from core.interfaces import IExecutionContext
    from core.container import DependencyContainer

    section("ExecutionContext — construction & immutability")
    ctx = ExecutionContext()
    check(isinstance(ctx, IExecutionContext), "ExecutionContext implements IExecutionContext")
    check(bool(ctx.context_id), "context_id auto-generated")
    check(bool(ctx.correlation_id), "correlation_id auto-generated")
    check(ctx.parent_id is None, "root context has no parent_id")
    try:
        ctx.context_id = "mutated"  # type: ignore[misc]
        check(False, "context is frozen (mutation should raise)")
    except Exception:
        check(True, "context is frozen (mutation raises)")

    section("ExecutionContext — child derivation")
    child = ctx.child(session_id="sess-1", client_sid="sid-1")
    check(child.context_id != ctx.context_id, "child has a new context_id")
    check(child.correlation_id == ctx.correlation_id, "child inherits correlation_id")
    check(child.parent_id == ctx.context_id, "child.parent_id == parent.context_id")
    check(child.session_id == "sess-1", "child overrides session_id")

    grandchild = child.child(workspace_id="alpha")
    check(grandchild.correlation_id == ctx.correlation_id, "grandchild keeps root correlation_id")
    check(grandchild.session_id == "sess-1", "grandchild inherits unset fields from parent")
    check(grandchild.parent_id == child.context_id, "grandchild.parent_id == child.context_id")

    section("ExecutionContext — metadata is read-only")
    meta_ctx = ExecutionContext(metadata={"a": 1})
    try:
        meta_ctx.metadata["b"] = 2  # type: ignore[index]
        check(False, "metadata mapping should be immutable")
    except TypeError:
        check(True, "metadata mapping is immutable (TypeError on write)")

    section("ExecutionContextFactory")
    factory = ExecutionContextFactory()
    root_a = factory.create(session_id="s1")
    root_b = factory.create(session_id="s1")
    check(root_a.correlation_id != root_b.correlation_id, "each factory.create() gets a fresh correlation_id")

    class _FakeSession:
        session_id = "sess-xyz"
        client_sid = "sid-xyz"

    class _FakeWorkspace:
        current_project = "myproject"

    class _FakeSnapshot:
        session = _FakeSession()
        workspace = _FakeWorkspace()

    from_snapshot = factory.from_brain_snapshot(_FakeSnapshot())
    check(from_snapshot.session_id == "sess-xyz", "from_brain_snapshot reads session_id")
    check(from_snapshot.workspace_id == "myproject", "from_brain_snapshot reads workspace_id")

    section("DI Container integration")
    c = DependencyContainer()
    c.register_instance(ExecutionContextFactory, factory)
    resolved = c.resolve(ExecutionContextFactory)
    check(resolved is factory, "ExecutionContextFactory resolves from container")

    section("Bootstrapper integration")
    from core.bootstrap import Bootstrapper
    bc = DependencyContainer()
    bs = Bootstrapper(container=bc, kasa_agent=None)
    bs.bootstrap()
    check(bs.context_factory is not None, "Bootstrapper constructs an ExecutionContextFactory")
    check(
        bc.resolve(ExecutionContextFactory) is bs.context_factory,
        "Bootstrapper registers the same factory instance it exposes",
    )

    section("PHASE 1.4 TEST SUMMARY")
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
