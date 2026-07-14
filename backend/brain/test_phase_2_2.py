"""
test_phase_2_2.py — Lumina V2 Phase 2.2 Verification Tests

Tests:
  1. Bootstrapping: EventBus registers as IEventBus.
  2. RuntimeFacade: Resolves IEventBus correctly.
  3. Disconnect Event Hook: Test mock disconnect event publishing.
  4. Wildcard matching delivery order and execution.
  5. Regression checks: ensure DI and other interfaces compile and run properly.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_2.py
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
from core.interfaces import IEventBus
from core.runtime_facade import RuntimeFacade
from core.bootstrap import Bootstrapper
from core.application import ApplicationHost
import server  # Bootstraps the container environment natively

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
    
    _section("Test 1: EventBus Registration Verification")
    try:
        assert container.is_registered(IEventBus), "IEventBus is not registered in the DI container"
        _ok("IEventBus registration in container verified")
    except Exception as e:
        _fail("IEventBus registration in container verified", str(e))

    _section("Test 2: RuntimeFacade EventBus Resolution")
    try:
        facade = RuntimeFacade(container)
        bus = facade.event_bus
        assert bus is not None, "event_bus resolved as None"
        _ok("RuntimeFacade correctly resolves event_bus property")
    except Exception as e:
        _fail("RuntimeFacade correctly resolves event_bus property", str(e))

    _section("Test 3: EventBus Publish and Sync/Async Subscribe Order")
    try:
        facade = RuntimeFacade(container)
        bus = facade.event_bus_adapter
        
        execution_order = []
        
        async def async_handler(topic, payload):
            sid_val = payload.get('sid') or payload.get('client_sid')
            execution_order.append(f"async:{topic}:{sid_val}")
            
        def sync_handler(topic, payload):
            sid_val = payload.get('sid') or payload.get('client_sid')
            execution_order.append(f"sync:{topic}:{sid_val}")

            
        # Subscribe both
        await bus.subscribe("session.*", async_handler)
        await bus.subscribe("session.disconnected", sync_handler)
        
        # Publish
        test_payload = {"sid": "client-999"}
        await bus.publish("session.disconnected", test_payload)
        
        assert len(execution_order) == 2, f"Expected 2 executions, got {len(execution_order)}"
        assert execution_order[0] == "async:session.disconnected:client-999", f"Expected async first, got {execution_order[0]}"
        assert execution_order[1] == "sync:session.disconnected:client-999", f"Expected sync second, got {execution_order[1]}"
        _ok("EventBus executes subscribers correctly and preserves expected order")
    except Exception as e:
        _fail("EventBus executes subscribers and preserves order", str(e))

    _section("Test 4: Disconnect Runtime Path Emulation")
    try:
        disconnect_calls = []
        
        async def on_disconnect(topic, payload):
            disconnect_calls.append(payload)
            
        # Subscribe to session.disconnected on server's runtime facade event bus
        await server._runtime_facade.event_bus_adapter.subscribe("session.disconnected", on_disconnect)
        
        # Emulate disconnect trigger by calling server.disconnect directly
        test_sid = "test-sid-555"
        server.connected_clients[test_sid] = {'status': 'connected'}
        
        await server.disconnect(test_sid)
        
        assert test_sid not in server.connected_clients, "Expected client removed from global connected_clients map"
        assert len(disconnect_calls) == 1, "Expected exactly 1 disconnect event to be published and received"
        assert disconnect_calls[0]["client_sid"] == test_sid, f"Expected client_sid={test_sid}, got {disconnect_calls[0]}"
        _ok("disconnect() Socket.IO handler successfully publishes to InProcessEventBus with correct payload")
    except Exception as e:
        _fail("disconnect() Socket.IO handler successfully publishes to InProcessEventBus", str(e))

    # Reset container to original state
    # (Removed to avoid side effects on caching/imports)

    
    print(f"\n{'='*60}")
    print(f"  PHASE 2.2 TEST SUMMARY")
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
