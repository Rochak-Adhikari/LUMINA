"""
test_phase_2_3.py — Lumina V2 Phase 2.3 Verification Tests

Tests:
  1. Bootstrapping: ExecutionContextFactory registers.
  2. RuntimeFacade: new_execution_context_adapter resolves fresh and transient.
  3. ExecutionContext: child derivation and field immutability.
  4. Quest Emulation Flow: Test create_quest logs and traces execution.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_3.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root / "backend"))

# Imports
from core.container import container
from core.interfaces import IExecutionContext
from core.runtime_facade import RuntimeFacade
from core.context import ExecutionContextFactory
from core.adapters import ExecutionContextAdapter
import server  # Bootstraps container natively

# Counters
_passed = 0
_failed = 0

def _ok(name: str) -> None:
    global _passed
    _passed += 1
    print(f"  [PASS] {name}")

def _fail(name: str, reason: str) -> None:
    global _failed
    _failed += 1
    print(f"  [FAIL] {name}")
    print(f"         {reason}")

def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

async def run_tests():
    global _passed, _failed
    
    _section("Test 1: ExecutionContextFactory Registration")
    try:
        assert container.is_registered(ExecutionContextFactory), "ExecutionContextFactory not registered in DI container"
        _ok("ExecutionContextFactory registration in DI verified")
    except Exception as e:
        _fail("ExecutionContextFactory registration in DI verified", str(e))

    _section("Test 2: RuntimeFacade new_execution_context_adapter()")
    try:
        facade = RuntimeFacade(container)
        
        # Verify transient behaviour (resolves fresh wrapper each time)
        adapter1 = facade.new_execution_context_adapter()
        adapter2 = facade.new_execution_context_adapter()
        
        assert isinstance(adapter1, ExecutionContextAdapter), "Expected ExecutionContextAdapter wrapper"
        assert adapter1 is not adapter2, "Expected transient resolution (different instances)"
        assert adapter1.context_id != adapter2.context_id, "Expected distinct context ids"
        _ok("RuntimeFacade resolves fresh transient ExecutionContextAdapter instances")
    except Exception as e:
        _fail("RuntimeFacade resolves fresh transient ExecutionContextAdapter instances", str(e))

    _section("Test 3: ExecutionContext Child Derivation & Immutability")
    try:
        facade = RuntimeFacade(container)
        root_adapter = facade.new_execution_context_adapter()
        
        # Derive child
        child_adapter = root_adapter.child(
            client_sid="sio-1234",
            metadata={"caller": "test"}
        )
        
        assert child_adapter.context_id != root_adapter.context_id, "Expected new context_id"
        assert child_adapter.correlation_id == root_adapter.correlation_id, "Expected correlation_id inheritance"
        assert child_adapter.parent_id == root_adapter.context_id, "Expected parent_id to point to parent context_id"
        assert child_adapter.client_sid == "sio-1234", "Expected overridden client_sid"
        assert child_adapter.metadata["caller"] == "test", "Expected merged metadata"
        
        # Test immutability
        try:
            child_adapter._execution_context.session_id = "new-session"  # type: ignore
            assert False, "Should have raised exception on frozen dataclass mutation"
        except AttributeError:
            _ok("ExecutionContext child derivation is correct and immutable fields are enforced")

    except Exception as e:
        _fail("ExecutionContext child derivation is correct and immutable", str(e))

    _section("Test 4: Quest Creation Path Tracing Emulation")
    try:
        # We need to capture stdout to verify the prints
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            # Emulate quest creation call
            await server.create_quest("mock-client-sid", {"title": "Test Integration Quest"})
            
        output = f.getvalue()
        
        # Verify tracing logs were output
        assert "[TRACE] create_quest starting" in output, "Expected start trace in output log"
        assert "[TRACE] create_quest finished successfully" in output or "[TRACE] create_quest failed" in output, "Expected end/fail trace in output log"
        
        # Verify socket events are not broken (the quest table update works)
        # Check database records
        store = server._get_memory_store()
        quests = store.list_quests()
        found = [q for q in quests if q["title"] == "Test Integration Quest"]
        assert len(found) > 0, "Quest was not created in memory database"
        
        # Clean up database entry
        for q in found:
            store.delete_quest(q["id"])
            
        _ok("create_quest successfully instantiates, traces, and finishes with ExecutionContext")
    except Exception as e:
        _fail("create_quest successfully instantiates, traces, and finishes", str(e))

    print(f"\n{'='*60}")
    print(f"  PHASE 2.3 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"  Passed: {_passed}")
    print(f"  Failed: {_failed}")
    print(f"{'='*60}")
    
    if _failed == 0:
        print("  ALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"  {_failed} TEST(S) FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests())
