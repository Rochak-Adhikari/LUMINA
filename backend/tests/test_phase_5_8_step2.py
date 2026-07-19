"""
tests/test_phase_5_8_step2.py — Milestone 5.8.2 Verification (Workspace Activation)

Verifies:
  - RuntimeFacade.activate_workspace() exists and delegates to WorkspaceSync
  - Activation follows ProjectManager into WorkspaceMemory
  - Idempotency: re-activating the already-active workspace is a no-op
    (no re-switch, no re-save, no duplicate work)
  - Save-before-switch fires only on an actual path change
  - Tool call-site (_maybe_activate_workspace) is flag-gated (default OFF => no-op)
  - Flag ON triggers activation exactly once via the facade
  - Activation failure never propagates out of the tool trigger
  - Call-site references the facade only, never WorkspaceSync directly
  - Feature flag present in DEFAULT_SETTINGS, default False

Stdlib unittest; heavy deps mocked (established pattern).
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.workspace.sync import WorkspaceSync


class _FakeWSM:
    """WorkspaceMemoryManager stand-in recording switch/save/current calls."""
    def __init__(self):
        self.switches = []
        self.saves = []
        self._current = object()

    def switch(self, path):
        self.switches.append(Path(path))
        self._current = ("memory-for", Path(path))
        return self._current

    def save(self, path):
        self.saves.append(Path(path))

    def current(self):
        return self._current


class _FakePM:
    def __init__(self, path):
        self._path = path

    def get_current_project_path(self):
        return self._path


class TestActivationSync(unittest.TestCase):
    def test_first_activation_switches(self):
        wsm = _FakeWSM()
        sync = WorkspaceSync(wsm)
        mem = sync.sync_to(_FakePM("/proj/a"))
        self.assertEqual(wsm.switches, [Path("/proj/a")])
        self.assertEqual(wsm.saves, [])
        self.assertEqual(mem, ("memory-for", Path("/proj/a")))

    def test_idempotent_reactivation_is_noop(self):
        wsm = _FakeWSM()
        sync = WorkspaceSync(wsm)
        sync.sync_to(_FakePM("/proj/a"))
        # Re-activate the SAME project repeatedly.
        sync.sync_to(_FakePM("/proj/a"))
        sync.sync_to(_FakePM("/proj/a"))
        self.assertEqual(wsm.switches, [Path("/proj/a")], "must switch only once")
        self.assertEqual(wsm.saves, [], "no save when path unchanged")

    def test_switch_saves_previous_then_switches(self):
        wsm = _FakeWSM()
        sync = WorkspaceSync(wsm)
        sync.sync_to(_FakePM("/proj/a"))
        sync.sync_to(_FakePM("/proj/b"))
        self.assertEqual(wsm.switches, [Path("/proj/a"), Path("/proj/b")])
        self.assertEqual(wsm.saves, [Path("/proj/a")], "save old before switching")

    def test_reactivate_after_change_still_idempotent(self):
        wsm = _FakeWSM()
        sync = WorkspaceSync(wsm)
        sync.sync_to(_FakePM("/proj/a"))
        sync.sync_to(_FakePM("/proj/b"))
        sync.sync_to(_FakePM("/proj/b"))  # no-op
        self.assertEqual(wsm.switches, [Path("/proj/a"), Path("/proj/b")])
        self.assertEqual(wsm.saves, [Path("/proj/a")])


class _FakeFacade:
    def __init__(self):
        self.calls = []

    def activate_workspace(self, pm):
        self.calls.append(pm)
        return "activated"


class _FakeFacadeBoom:
    def activate_workspace(self, pm):
        raise RuntimeError("activation blew up")


class _FakeLoop:
    def __init__(self, enabled, facade):
        self.permissions = {"workspace_activation_enabled": enabled}
        self._facade = facade
        self.project_manager = _FakePM("/proj/x")


class TestActivationTrigger(unittest.TestCase):
    def _trigger(self):
        from core.tool_handlers import _maybe_activate_workspace
        return _maybe_activate_workspace

    def test_flag_off_is_noop(self):
        facade = _FakeFacade()
        self._trigger()(_FakeLoop(enabled=False, facade=facade))
        self.assertEqual(facade.calls, [], "flag OFF => activation must not run")

    def test_flag_on_activates_once_via_facade(self):
        facade = _FakeFacade()
        loop = _FakeLoop(enabled=True, facade=facade)
        self._trigger()(loop)
        self.assertEqual(len(facade.calls), 1)
        self.assertIs(facade.calls[0], loop.project_manager)

    def test_activation_failure_is_swallowed(self):
        loop = _FakeLoop(enabled=True, facade=_FakeFacadeBoom())
        # Must not raise.
        self._trigger()(loop)

    def test_missing_facade_is_noop(self):
        loop = _FakeLoop(enabled=True, facade=None)
        self._trigger()(loop)  # must not raise


class TestBoundaries(unittest.TestCase):
    def test_facade_has_activate_workspace(self):
        from core.runtime_facade import RuntimeFacade
        self.assertTrue(hasattr(RuntimeFacade, "activate_workspace"))

    def test_callsite_never_imports_workspace_sync(self):
        src = (backend_dir / "core" / "tool_handlers.py").read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        for m in modules:
            self.assertNotIn("workspace.sync", m,
                             "call-site must reach activation via the facade only")
        # Authoritative check: no import of WorkspaceSync (AST, not substring —
        # the word legitimately appears in the helper's explanatory docstring).
        self.assertNotIn("brain.workspace.sync", modules)

    def test_flag_present_default_false(self):
        src = (backend_dir / "server.py").read_text(encoding="utf-8")
        self.assertIn("workspace_activation_enabled", src)
        # Appears as a False default inside tool_permissions.
        self.assertIn('"workspace_activation_enabled": False', src)


if __name__ == "__main__":
    unittest.main()
