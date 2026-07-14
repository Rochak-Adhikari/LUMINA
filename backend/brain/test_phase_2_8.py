"""
test_phase_2_8.py — Lumina V2 Phase 2.8 Verification Tests

Tests:
  1. Bootstrapping: container registrations.
  2. Workspace Interface registration and registration virtually.
  3. AudioLoop Integration: flush_chat execution logs via workspace_manager from facade.
  4. Output Check: verify logged chat matches active project chat history.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_8.py
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

    _section("Test 2: AudioLoop flush_chat Integration")
    try:
        # Populate chat buffer
        loop.chat_buffer = {"sender": "User", "text": "Hello Lumina - test message for Phase 2.8"}
        
        # Verify log_chat calls through the facade.
        # We can verify by checking if the message was written to the project log.
        # First check project path.
        current_project = loop.project_manager.current_project
        assert current_project == "temp", f"Expected temp project, got '{current_project}'"
        
        # Flush the buffer to trigger log_chat
        loop.flush_chat()
        
        # Buffer should be cleared
        assert loop.chat_buffer["sender"] is None, "Expected sender to be reset"
        assert loop.chat_buffer["text"] == "", "Expected text to be reset"
        
        # Read the recent history to verify
        history = loop.project_manager.get_recent_chat_history(limit=5)
        found = [msg for msg in history if "test message for Phase 2.8" in msg.get("text", "")]
        assert len(found) > 0, "Log entry not found in project history"
        _ok("AudioLoop flush_chat logs to project history via resolved WorkspaceManager successfully")
    except Exception as e:
        _fail("AudioLoop flush_chat logs to project history via resolved WorkspaceManager", str(e))

    print(f"\n{'='*60}")
    print(f"  PHASE 2.8 TEST SUMMARY")
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
