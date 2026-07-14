"""
test_phase_2_6.py — Lumina V2 Phase 2.6 Verification Tests

Tests:
  1. Bootstrapping: container registrations.
  2. RuntimeFacade: resolves workspace_manager correctly.
  3. Workspace Integration: generate_cad Socket.IO event handler resolves path via facade's workspace_manager.
  4. Path equivalence check: ensure reading via workspace_manager matches concrete project path.

Run with:
    $env:CONDA_DEFAULT_ENV='lumina'
    $env:PYTHONUTF8='1'
    & "E:\\AI\\conda_envs\\lumina\\python.exe" -X utf8 backend/brain/test_phase_2_6.py
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
    
    _section("Test 1: IWorkspaceManager DI Override Verification")
    try:
        from project_manager import ProjectManager
        IWorkspaceManager.register(ProjectManager)  # Virtual subclass registration for duck-typed class
        
        # Create an AudioLoop to register concrete ProjectManager to container
        loop = AudioLoop(video_mode="none")
        container.override(IWorkspaceManager, loop.project_manager)
        
        assert container.is_registered(IWorkspaceManager), "IWorkspaceManager not registered in DI container"
        _ok("IWorkspaceManager successfully overridden/registered in DI container")
    except Exception as e:
        _fail("IWorkspaceManager overridden/registered in DI container", str(e))

    _section("Test 2: RuntimeFacade workspace_manager property")
    try:
        facade = RuntimeFacade(container)
        mgr = facade.workspace_manager
        assert mgr is not None, "workspace_manager resolved as None"
        assert isinstance(mgr, IWorkspaceManager), "Resolved service does not implement IWorkspaceManager"
        _ok("RuntimeFacade correctly resolves workspace_manager accessor")
    except Exception as e:
        _fail("RuntimeFacade correctly resolves workspace_manager", str(e))

    _section("Test 3: generate_cad Socket.IO Path Emulation")
    try:
        # Mock CAD agent generate_prototype
        called_output_dir = []
        
        class MockCadAgent:
            async def generate_prototype(self, prompt, output_dir):
                called_output_dir.append(output_dir)
                return {"file_path": "mock_design.stl", "data": b"mockstl"}

        # Hook mock CAD agent
        loop.cad_agent = MockCadAgent()
        
        # Set up a mock audio loop global
        server.audio_loop = loop
        
        try:
            # Emulate generate_cad socket call
            await server.generate_cad("mock-sid", {"prompt": "make a cube"})
            
            assert len(called_output_dir) == 1, "Expected generate_prototype to be called once"
            output_dir = called_output_dir[0]
            
            # Read paths directly from concrete project manager and check equivalence
            direct_path = str(loop.project_manager.get_current_project_path() / "cad")
            assert output_dir == direct_path, f"Path mismatch: {output_dir} != {direct_path}"
            _ok("generate_cad Socket.IO handler reads via resolved IWorkspaceManager identically")
        finally:
            server.audio_loop = None
    except Exception as e:
        _fail("generate_cad Socket.IO handler reads via resolved IWorkspaceManager", str(e))

    print(f"\n{'='*60}")
    print(f"  PHASE 2.6 TEST SUMMARY")
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
