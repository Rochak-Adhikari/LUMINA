"""
test_phase_2_4.py — Lumina V2 Phase 2.4 Verification Tests

Tests:
  1. Bootstrapping: IPipeline registers as RequestPipeline.
  2. RuntimeFacade: Resolves IPipeline correctly.
  3. PipelineContext: Construction with ExecutionContext and BrainState snapshot.
  4. Quest Emulation Flow: Test create_quest logs tracing for both ExecutionContext and RequestPipeline.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_4.py
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
from core.interfaces import IPipeline
from core.runtime_facade import RuntimeFacade
from core.pipeline import PipelineContext
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
    
    _section("Test 1: IPipeline Registration Verification")
    try:
        assert container.is_registered(IPipeline), "IPipeline is not registered in the DI container"
        _ok("IPipeline registration in container verified")
    except Exception as e:
        _fail("IPipeline registration in container verified", str(e))

    _section("Test 2: RuntimeFacade IPipeline Resolution")
    try:
        facade = RuntimeFacade(container)
        pipeline = facade.pipeline
        assert pipeline is not None, "pipeline resolved as None"
        assert pipeline.is_sealed, "Expected pipeline to be sealed after bootstrapper completes"
        _ok("RuntimeFacade correctly resolves sealed RequestPipeline instance")
    except Exception as e:
        _fail("RuntimeFacade correctly resolves sealed RequestPipeline", str(e))

    _section("Test 3: PipelineContext Initialization")
    try:
        facade = RuntimeFacade(container)
        ctx_adapter = facade.new_execution_context_adapter()
        brain_snap = facade.brain_state_adapter.snapshot()
        
        pipeline_ctx = PipelineContext(
            execution_context=ctx_adapter._execution_context,
            brain_snapshot=brain_snap,
            request_metadata={"kind": "test_verification"}
        )
        
        assert pipeline_ctx.execution_context is not None, "Expected associated ExecutionContext"
        assert pipeline_ctx.brain_snapshot is not None, "Expected associated BrainState snapshot"
        assert pipeline_ctx.request_metadata["kind"] == "test_verification", "Expected metadata mapping"
        assert pipeline_ctx.is_cancelled is False, "Expected initial is_cancelled is False"
        
        # Test cancel
        pipeline_ctx.cancel()
        assert pipeline_ctx.is_cancelled is True, "Expected cancelled status to be True"
        _ok("PipelineContext correctly instantiates and maintains lifecycle attributes")
    except Exception as e:
        _fail("PipelineContext correctly instantiates and maintains attributes", str(e))

    _section("Test 4: Request Pipeline Quest Path Emulation")
    try:
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            # Emulate quest creation call
            await server.create_quest("mock-client-sid", {"title": "Test Pipeline Quest"})
            
        output = f.getvalue()
        
        # Verify trace logs from context and pipeline were both output
        assert "[TRACE] create_quest starting" in output, "Expected context start trace"
        assert "[TRACE] create_quest pipeline executed" in output, "Expected pipeline trace"
        assert "is_cancelled=False" in output, "Expected is_cancelled=False in pipeline trace"
        assert "[TRACE] create_quest finished successfully" in output, "Expected context end trace"
        
        # Verify database update succeeded
        store = server._get_memory_store()
        quests = store.list_quests()
        found = [q for q in quests if q["title"] == "Test Pipeline Quest"]
        assert len(found) > 0, "Quest was not created in database"
        
        # Clean up database entry
        for q in found:
            store.delete_quest(q["id"])
            
        _ok("create_quest runs cleanly through the RequestPipeline and executes DB actions successfully")
    except Exception as e:
        _fail("create_quest runs through the RequestPipeline and executes DB actions", str(e))

    print(f"\n{'='*60}")
    print(f"  PHASE 2.4 TEST SUMMARY")
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
