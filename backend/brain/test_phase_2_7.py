"""
test_phase_2_7.py — Lumina V2 Phase 2.7 Verification Tests

Tests:
  1. Bootstrapping: container registrations.
  2. Workspace Interface registration and registration virtually.
  3. Tool Dispatcher: handle_list_projects execution via workspace_manager from facade.
  4. Equivalence Check: ensure list output matches concrete project_manager.list_projects().

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_7.py
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
from core.interfaces import IWorkspaceManager
from core.registry import ToolDispatcherRegistry
import server  # Bootstraps container natively
from lumina import AudioLoop

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
    
    _section("Test 1: WorkspaceManager DI Override Setup")
    try:
        from project_manager import ProjectManager
        IWorkspaceManager.register(ProjectManager)  # Virtual subclass registration for duck-typed class
        
        loop = AudioLoop(video_mode="none")
        container.override(IWorkspaceManager, loop.project_manager)
        
        assert container.is_registered(IWorkspaceManager), "IWorkspaceManager not registered in DI container"
        _ok("IWorkspaceManager successfully registered in DI container")
    except Exception as e:
        _fail("IWorkspaceManager successfully registered in DI container", str(e))

    _section("Test 2: ToolDispatcherRegistry list_projects Check")
    try:
        assert ToolDispatcherRegistry.contains("list_projects"), "list_projects tool handler not registered in dispatcher"
        handler = ToolDispatcherRegistry.get("list_projects")
        assert callable(handler), "list_projects handler is not callable"
        _ok("list_projects handler is registered in ToolDispatcherRegistry")
    except Exception as e:
        _fail("list_projects handler is registered in ToolDispatcherRegistry", str(e))

    _section("Test 3: handle_list_projects Tool Execution Flow")
    try:
        # Mock FunctionCall object to pass to handler
        class MockFunctionCall:
            def __init__(self):
                self.name = "list_projects"
                self.args = {}
                self.id = "fc-test-999"

        fc = MockFunctionCall()
        
        # Execute handler using loop with the initialized facade
        handler = ToolDispatcherRegistry.get("list_projects")
        result = await handler(fc, loop)
        
        assert isinstance(result, dict), "Expected dict response"
        assert "result" in result, "Expected 'result' key in return dict"
        assert "Available projects:" in result["result"], "Result string format mismatch"
        
        # Compare output content with direct call
        direct_list = loop.project_manager.list_projects()
        direct_msg = f"Available projects: {', '.join(direct_list)}"
        assert result["result"] == direct_msg, f"Message output mismatch: {result['result']} != {direct_msg}"
        
        _ok("handle_list_projects executes successfully via facade's WorkspaceManager with identical outputs")
    except Exception as e:
        _fail("handle_list_projects executes successfully via facade's WorkspaceManager", str(e))

    print(f"\n{'='*60}")
    print(f"  PHASE 2.7 TEST SUMMARY")
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
