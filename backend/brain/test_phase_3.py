"""
brain/test_phase_3.py — Phase 3 Standalone Architectural Verification Tests (Isolated Contexts)

Tests:
  1. SessionManager: attaching and detaching an AudioLoop mutates truth records in BrainState and triggers EventBus lifecycle events.
  2. ServiceAccessor: bridges calls to IMemoryManager and IWorkspaceManager, checking container resolution first, then falling back to SessionManager.
  3. BrainState User Turn: synchronizes turn events with state.
  4. RuntimeFacade: correctly routes session_manager and service_accessor.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_3.py
"""

import os
import sys
import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock

# Setup paths
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root / "backend"))

from core.container import DependencyContainer
from core.interfaces import IBrainState, IEventBus, IMemoryManager, IWorkspaceManager
from brain.state import BrainState
from brain.events import InProcessEventBus
from core.session import SessionManager
from core.service_accessor import ServiceAccessor
from core.runtime_facade import RuntimeFacade

# Dummy legacy classes
class DummyMemoryStore:
    def __init__(self, path="dummy.db"):
        self.db_path = path

    def add_memory(self, mtype, content, **kwargs):
        return "mem_123"

    def get_memories(self, limit=10, update_access=False):
        return [{"id": "m1", "type": "fact", "content": "hello"}]


class DummyProjectManager:
    def __init__(self, proj="default_project"):
        self.current_project = proj

    def get_current_project_path(self):
        return Path("/dummy/path")


class DummyAudioLoop:
    def __init__(self):
        self.memory_store = DummyMemoryStore()
        self.project_manager = DummyProjectManager()


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


def make_clean_context():
    """Helper to return an isolated sandbox environment."""
    c = DependencyContainer()
    brain_state = BrainState()
    event_bus = InProcessEventBus()
    
    c.register_instance(IBrainState, brain_state)
    c.register_instance(IEventBus, event_bus)
    
    session_mgr = SessionManager(brain_state=brain_state, event_bus=event_bus)
    c.register_instance(SessionManager, session_mgr)
    
    svc_accessor = ServiceAccessor(container=c, session_manager=session_mgr)
    c.register_instance(ServiceAccessor, svc_accessor)
    
    facade = RuntimeFacade(container=c)
    c.register_instance(RuntimeFacade, facade)
    
    return c, brain_state, event_bus, session_mgr, svc_accessor, facade


async def run_tests():
    global _passed, _failed
    
    # -------------------------------------------------------------
    # Test 1: SessionManager attach / detach lifecycle
    # -------------------------------------------------------------
    _section("Test 1: SessionManager attach/detach lifecycle")
    c, brain_state, event_bus, session_mgr, svc_accessor, facade = make_clean_context()
    try:
        events_received = []
        await event_bus.subscribe("session.audio_attached", lambda t, p: events_received.append(("attached", p)))
        await event_bus.subscribe("session.audio_detached", lambda t, p: events_received.append(("detached", p)))
        
        assert not session_mgr.is_active, "Expected inactive initial state"
        assert brain_state.snapshot().session.connected_at is None, "Expected empty connected_at in BrainState"
        
        # Attach
        loop = DummyAudioLoop()
        session_mgr.attach(loop)
        
        assert session_mgr.is_active, "Expected active state after attach"
        assert session_mgr.audio_loop is loop, "Expected audio_loop reference to match"
        assert brain_state.snapshot().session.connected_at is not None, "Expected connected_at to be populated"
        assert len(events_received) == 1, f"Expected 1 event, got {len(events_received)}"
        assert events_received[0][0] == "attached", "Expected attach event"
        
        # Detach
        session_mgr.detach()
        
        assert not session_mgr.is_active, "Expected inactive state after detach"
        assert session_mgr.audio_loop is None, "Expected audio_loop reference to be cleared"
        assert brain_state.snapshot().session.connected_at is None, "Expected connected_at to be reset in BrainState"
        assert len(events_received) == 2, f"Expected 2 events, got {len(events_received)}"
        assert events_received[1][0] == "detached", "Expected detach event"
        
        _ok("SessionManager updates BrainState and triggers EventBus hooks correctly")
    except Exception as e:
        _fail("SessionManager updates BrainState and triggers EventBus hooks correctly", str(e))

    # -------------------------------------------------------------
    # Test 2: ServiceAccessor DI vs Fallback paths
    # -------------------------------------------------------------
    _section("Test 2: ServiceAccessor DI vs Fallback paths")
    c, brain_state, event_bus, session_mgr, svc_accessor, facade = make_clean_context()
    try:
        # Starting: no DI registrations
        assert svc_accessor.memory_store is None, "Expected None memory_store initially"
        assert svc_accessor.project_manager is None, "Expected None project_manager initially"
        
        # Attach session
        loop = DummyAudioLoop()
        session_mgr.attach(loop)
        
        # Yields attributes via fallback
        assert svc_accessor.memory_store is loop.memory_store, "Expected fallback memory_store"
        assert svc_accessor.project_manager is loop.project_manager, "Expected fallback project_manager"
        assert svc_accessor.current_project == "default_project", "Expected current project helper fallback"
        
        # Register mock implementations directly to container override
        mock_mem = MagicMock()
        mock_ws = MagicMock()
        c.override(IMemoryManager, mock_mem)
        c.override(IWorkspaceManager, mock_ws)
        
        # DI has higher priority, should bypass fallback
        assert svc_accessor.memory_store is mock_mem, "Expected DI resolved memory_store"
        assert svc_accessor.project_manager is mock_ws, "Expected DI resolved project_manager"
        assert svc_accessor.memory_store is not loop.memory_store, "Bypassed fallback check failed"
        
        _ok("ServiceAccessor resolves container overrides first, falling back to SessionManager if absent")
    except Exception as e:
        _fail("ServiceAccessor resolves container overrides first, falling back to SessionManager if absent", str(e))

    # -------------------------------------------------------------
    # Test 3: BrainState user turn synchronization
    # -------------------------------------------------------------
    _section("Test 3: BrainState user turn synchronization")
    c, brain_state, event_bus, session_mgr, svc_accessor, facade = make_clean_context()
    try:
        assert brain_state.snapshot().conversation.turn_index == 0, "Expected empty initial turn index"
        
        brain_state.record_user_turn("test message turn", mood_state="calm")
        
        snap = brain_state.snapshot()
        assert snap.conversation.turn_index == 1, f"Expected turn index to be 1, got {snap.conversation.turn_index}"
        assert snap.conversation.last_user_text == "test message turn", f"Expected text match, got {snap.conversation.last_user_text}"
        assert snap.conversation.mood_state == "calm", f"Expected mood calm, got {snap.conversation.mood_state}"
        
        _ok("BrainState logs user turn inputs to snapshot conversation metadata correctly")
    except Exception as e:
        _fail("BrainState logs user turn inputs to snapshot conversation metadata correctly", str(e))

    # -------------------------------------------------------------
    # Test 4: RuntimeFacade new properties routing
    # -------------------------------------------------------------
    _section("Test 4: RuntimeFacade new properties routing")
    c, brain_state, event_bus, session_mgr, svc_accessor, facade = make_clean_context()
    try:
        assert facade.session_manager is session_mgr, "Expected facade to resolve session_manager"
        assert facade.service_accessor is svc_accessor, "Expected facade to resolve service_accessor"
        
        _ok("RuntimeFacade provides typed access to session_manager and service_accessor")
    except Exception as e:
        _fail("RuntimeFacade provides typed access to session_manager and service_accessor", str(e))

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  PHASE 3 TEST SUMMARY")
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
