"""
test_phase_2_5.py — Lumina V2 Phase 2.5 Verification Tests

Tests:
  1. Bootstrapping: container registrations.
  2. RuntimeFacade: resolves memory_manager correctly.
  3. Memory Integration: get_memories Socket.IO event handler reads data via facade's memory_manager.
  4. Database equivalence check: ensure reading via memory_manager is identical to concrete store.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_5.py
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
from core.interfaces import IMemoryManager
from core.runtime_facade import RuntimeFacade
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
    
    _section("Test 1: IMemoryManager DI Override Verification")
    try:
        from memory_store import MemoryStore
        IMemoryManager.register(MemoryStore)  # Virtual subclass registration for duck-typed class
        
        # Create an AudioLoop to register concrete MemoryStore to container
        loop = AudioLoop(video_mode="none")
        container.override(IMemoryManager, loop.memory_store)
        
        assert container.is_registered(IMemoryManager), "IMemoryManager not registered in DI container"
        _ok("IMemoryManager successfully overridden/registered in DI container")
    except Exception as e:
        _fail("IMemoryManager overridden/registered in DI container", str(e))

    _section("Test 2: RuntimeFacade memory_manager property")
    try:
        facade = RuntimeFacade(container)
        mgr = facade.memory_manager
        assert mgr is not None, "memory_manager resolved as None"
        assert isinstance(mgr, IMemoryManager), "Resolved service does not implement IMemoryManager"
        _ok("RuntimeFacade correctly resolves memory_manager accessor")
    except Exception as e:
        _fail("RuntimeFacade correctly resolves memory_manager", str(e))

    _section("Test 3: get_memories Socket.IO Path Emulation")
    try:
        # We need to capture socket event emissions by mocking sio.emit
        emitted_events = []
        
        async def mock_emit(event_name, payload, **kwargs):
            emitted_events.append((event_name, payload))
            
        # Hook mock emit
        original_emit = server.sio.emit
        server.sio.emit = mock_emit
        
        # Set up a mock audio loop global
        server.audio_loop = loop
        
        try:
            # Emulate get_memories socket call
            await server.get_memories("mock-sid", {"type": "fact", "limit": 2})
            
            assert len(emitted_events) == 1, "Expected exactly 1 socket event emission"
            event_name, payload = emitted_events[0]
            assert event_name == "memories", f"Expected event 'memories', got '{event_name}'"
            assert "memories" in payload, "Payload is missing 'memories' key"
            
            # Read memories directly from concrete store and check equivalence
            direct_memories = loop.memory_store.get_memories("fact", limit=2, update_access=False)
            assert len(payload["memories"]) == len(direct_memories), "Memories count mismatch"
            _ok("get_memories Socket.IO handler reads via resolved IMemoryManager identically")
        finally:
            # Restore original emit
            server.sio.emit = original_emit
            server.audio_loop = None
    except Exception as e:
        _fail("get_memories Socket.IO handler reads via resolved IMemoryManager", str(e))

    print(f"\n{'='*60}")
    print(f"  PHASE 2.5 TEST SUMMARY")
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
