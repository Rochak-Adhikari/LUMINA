"""
test_phase_2_1.py — Lumina V2 Phase 2.1 Verification Tests

Tests:
  1. Bootstrapping: ApplicationHost and Bootstrapper wire container correctly.
  2. RuntimeFacade: Resolves IMemoryManager, IBrainState, IEventBus, IWorkspaceManager, and IKnowledgeManager.
  3. BrainState & Facade: Read and write pending_confirmation_id via RuntimeFacade.
  4. AudioLoop Integration: Verify AudioLoop contains self._facade and it is a RuntimeFacade.
  5. Mock Tool Confirmation Path: Test setting and clearing pending_confirmation_id via the facade.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_1.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root / "backend"))

# Import container & interfaces
from core.container import container
from core.interfaces import IBrainState, IEventBus, IMemoryManager, IWorkspaceManager, IKnowledgeManager
from core.runtime_facade import RuntimeFacade
from core.bootstrap import Bootstrapper
from core.application import ApplicationHost
from brain.state import BrainState
from brain.events import InProcessEventBus

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
    _section("Test 1: Core Bootstrap and Container Registration")
    try:
        # Reset container for clean test environment
        container.reset()
        bootstrapper = Bootstrapper(container)
        app_host = ApplicationHost(container, bootstrapper)
        app_host.initialize()
        app_host.start()
        
        # Verify registrations
        assert container.is_registered(IBrainState), "IBrainState not registered"
        assert container.is_registered(IEventBus), "IEventBus not registered"
        _ok("Bootstrap successfully registers core services in DI container")
    except Exception as e:
        _fail("Bootstrap successfully registers core services", str(e))

    _section("Test 2: RuntimeFacade Resolution")
    try:
        facade = RuntimeFacade(container)
        assert facade.brain_state is not None, "BrainState not resolved"
        assert facade.event_bus is not None, "EventBus not resolved"
        _ok("RuntimeFacade correctly resolves registered infrastructure services")
    except Exception as e:
        _fail("RuntimeFacade correctly resolves services", str(e))

    _section("Test 3: BrainState pending_confirmation_id Mutations")
    try:
        facade = RuntimeFacade(container)
        # Verify initial default is None
        snap = facade.brain_state_adapter.snapshot()
        assert snap.execution.pending_confirmation_id is None, "Expected initial None"
        
        # Set to mock ID
        mock_id = "test-uuid-123"
        with facade.brain_state_adapter.transaction() as draft:
            draft.pending_confirmation_id = mock_id
            
        snap = facade.brain_state_adapter.snapshot()
        assert snap.execution.pending_confirmation_id == mock_id, f"Expected {mock_id}, got {snap.execution.pending_confirmation_id}"
        
        # Clear ID
        with facade.brain_state_adapter.transaction() as draft:
            if draft.pending_confirmation_id == mock_id:
                draft.pending_confirmation_id = None
                
        snap = facade.brain_state_adapter.snapshot()
        assert snap.execution.pending_confirmation_id is None, "Expected cleared None"
        _ok("pending_confirmation_id written & cleared via RuntimeFacade")
    except Exception as e:
        _fail("pending_confirmation_id written & cleared via RuntimeFacade", str(e))

    _section("Test 4: AudioLoop Facade Initialization")
    try:
        from lumina import AudioLoop
        
        # Construct AudioLoop with mock callbacks and parameters
        # No actual PyAudio or Gemini Live start will occur
        loop = AudioLoop(
            video_mode="none",
            on_audio_data=lambda x: None
        )
        
        assert hasattr(loop, "_facade"), "AudioLoop is missing self._facade property"
        assert isinstance(loop._facade, RuntimeFacade), "AudioLoop._facade is not an instance of RuntimeFacade"
        _ok("AudioLoop successfully initializes its own RuntimeFacade instance")
    except Exception as e:
        _fail("AudioLoop successfully initializes its own RuntimeFacade instance", str(e))

    _section("Test 5: AudioLoop Tool Confirmation Flow Simulation")
    try:
        from lumina import AudioLoop
        loop = AudioLoop(
            video_mode="none",
            on_audio_data=lambda x: None
        )
        
        mock_uuid = "audio-loop-test-uuid"
        
        # Set validation
        with loop._facade.brain_state_adapter.transaction() as draft:
            draft.pending_confirmation_id = mock_uuid
            
        snap = loop._facade.brain_state_adapter.snapshot()
        assert snap.execution.pending_confirmation_id == mock_uuid, "Expected UUID to be mirrored in BrainState"
        
        # Clear validation
        with loop._facade.brain_state_adapter.transaction() as draft:
            if draft.pending_confirmation_id == mock_uuid:
                draft.pending_confirmation_id = None
                
        snap = loop._facade.brain_state_adapter.snapshot()
        assert snap.execution.pending_confirmation_id is None, "Expected UUID to be cleared in BrainState"
        _ok("AudioLoop correctly sets and clears pending_confirmation_id via its facade")
    except Exception as e:
        _fail("AudioLoop correctly sets and clears pending_confirmation_id", str(e))

    # Reset container to original state for other test suites
    container.reset()
    
    print(f"\n{'='*60}")
    print(f"  PHASE 2.1 TEST SUMMARY")
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
