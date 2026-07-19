"""
tests/test_phase_5_6_step6.py — Phase 5.6.6: WorkspaceSync (activation, dormant)

WorkspaceSync follows ProjectManager: save-before-switch, read active path,
WorkspaceMemoryManager.switch(path). ProjectManager is the source of truth;
sync never selects a workspace. DORMANT — registered in DI, not wired into
any runtime switch path. ProjectManager untouched.
"""

import asyncio
import unittest
from unittest.mock import MagicMock
from pathlib import Path
import tempfile
import shutil
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper
from core.runtime_facade import RuntimeFacade
from brain.workspace.manager import WorkspaceMemoryManager
from brain.workspace.store import WorkspaceMemoryStore
from brain.workspace.sync import WorkspaceSync
from brain.workspace.memory import WorkspaceMemory
from brain.workspace.models import Note
from brain.core.models import BrainRequest, BrainResult
from brain.core.interfaces import IBrainCore, IContextBuilder


class _StubProjectManager:
    """Duck-typed ProjectManager: only get_current_project_path() is used."""
    def __init__(self, path):
        self._path = Path(path)
    def set_path(self, path):
        self._path = Path(path)
    def get_current_project_path(self):
        return self._path


class TestSync(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = WorkspaceMemoryStore()
        self.wsm = WorkspaceMemoryManager(store=self.store)
        self.sync = WorkspaceSync(self.wsm)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _ws(self, name, seed=None):
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        if seed is not None:
            m = WorkspaceMemory(name); m.add_note(Note(title=seed))
            self.store.save(d, m)
        return d

    def test_switch_a_to_b(self):
        a = self._ws("A", seed="a-note")
        b = self._ws("B", seed="b-note")
        pm = _StubProjectManager(a)
        mem = self.sync.sync_to(pm)
        self.assertEqual([n.title for n in mem.list_notes()], ["a-note"])
        pm.set_path(b)
        mem = self.sync.sync_to(pm)
        self.assertEqual([n.title for n in mem.list_notes()], ["b-note"])

    def test_switch_b_to_a(self):
        a = self._ws("A", seed="a"); b = self._ws("B", seed="b")
        pm = _StubProjectManager(b)
        self.sync.sync_to(pm)
        pm.set_path(a)
        self.assertEqual([n.title for n in self.sync.sync_to(pm).list_notes()], ["a"])

    def test_save_before_switch(self):
        # Enter A (empty), add a note to the live memory, switch to B; A must
        # be persisted by the save-before-switch.
        a = self._ws("A"); b = self._ws("B")
        pm = _StubProjectManager(a)
        self.sync.sync_to(pm)                      # current = A (empty)
        self.wsm.current().add_note(Note(title="added-in-A"))
        pm.set_path(b)
        self.sync.sync_to(pm)                      # saves A, loads B
        # Reload A from disk → the note was saved.
        reloaded = self.store.load(a)
        self.assertEqual([n.title for n in reloaded.list_notes()], ["added-in-A"])

    def test_load_after_switch(self):
        b = self._ws("B", seed="b")
        pm = _StubProjectManager(self._ws("A"))
        self.sync.sync_to(pm)
        pm.set_path(b)
        self.assertEqual([n.title for n in self.sync.sync_to(pm).list_notes()], ["b"])

    def test_workspace_isolation(self):
        a = self._ws("A", seed="a"); b = self._ws("B", seed="b")
        pm = _StubProjectManager(a)
        self.sync.sync_to(pm)
        # Mutate live A memory but do NOT switch → B on disk unaffected.
        self.wsm.current().add_note(Note(title="local"))
        self.assertEqual([n.title for n in self.store.load(b).list_notes()], ["b"])

    def test_missing_memory_file_empty(self):
        pm = _StubProjectManager(self._ws("Fresh"))  # no saved memory
        mem = self.sync.sync_to(pm)
        self.assertEqual(mem.list_notes(), [])

    def test_switching_preserves_previous_on_disk(self):
        a = self._ws("A", seed="a"); b = self._ws("B", seed="b")
        pm = _StubProjectManager(a)
        self.sync.sync_to(pm); pm.set_path(b); self.sync.sync_to(pm)
        # A still intact on disk after moving away.
        self.assertEqual([n.title for n in self.store.load(a).list_notes()], ["a"])

    def test_same_path_no_redundant_save_error(self):
        a = self._ws("A", seed="a")
        pm = _StubProjectManager(a)
        self.sync.sync_to(pm)
        # Re-sync to same path → no crash, still A.
        self.assertEqual([n.title for n in self.sync.sync_to(pm).list_notes()], ["a"])


class TestManagerSave(unittest.TestCase):
    def test_manager_save_roundtrip(self):
        root = Path(tempfile.mkdtemp())
        try:
            d = root / "W"; d.mkdir()
            store = WorkspaceMemoryStore()
            mgr = WorkspaceMemoryManager(store=store)
            mgr.current().add_note(Note(title="n"))
            mgr.save(d)
            self.assertEqual([n.title for n in store.load(d).list_notes()], ["n"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestDIandDormancy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()
        cls.facade = RuntimeFacade(cls.container)

    def test_sync_registered(self):
        s = self.container.resolve(WorkspaceSync)
        self.assertIsInstance(s, WorkspaceSync)
        self.assertIs(s, self.container.resolve(WorkspaceSync))

    def test_facade_exposes_sync(self):
        self.assertIs(self.facade.workspace_sync, self.container.resolve(WorkspaceSync))

    def test_context_builder_reflects_current_workspace(self):
        # After a sync (via stub PM) the ContextBuilder's workspace_ctx reflects
        # the newly-current workspace — proving the ContextBuilder→manager link.
        root = Path(tempfile.mkdtemp())
        try:
            d = root / "Lumina"; d.mkdir()
            store = self.container.resolve(WorkspaceMemoryStore)
            m = WorkspaceMemory("Lumina"); m.add_note(Note(title="live"))
            store.save(d, m)
            self.container.resolve(WorkspaceSync).sync_to(_StubProjectManager(d))
            cb = self.container.resolve(IContextBuilder)
            wc = cb.build(BrainRequest(text="x")).workspace_ctx
            self.assertEqual(wc["workspace"], "Lumina")
            self.assertEqual(wc["notes"][0]["title"], "live")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_brain_core_unchanged(self):
        core = self.container.resolve(IBrainCore)
        result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
        self.assertIsInstance(result, BrainResult)
        self.assertFalse(result.handled)

    def test_metadata_registry_unchanged(self):
        from core.metadata import ServiceMetadataRegistry
        self.assertEqual(len(self.container.resolve(ServiceMetadataRegistry)), 11)


class TestNoForbiddenImports(unittest.TestCase):
    def test_sync_and_manager_do_not_import_project_manager(self):
        import ast
        for fname in ("sync.py", "manager.py", "memory.py", "store.py"):
            src = (backend_dir / "brain" / "workspace" / fname).read_text(encoding="utf-8")
            mods = set()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.add(node.module)
                elif isinstance(node, ast.Import):
                    mods.update(a.name for a in node.names)
            for m in mods:
                self.assertNotIn("project_manager", m, f"{fname} imports ProjectManager")
                self.assertNotIn("planning", m, f"{fname} imports planner")
                self.assertNotIn("brain.core", m, f"{fname} imports BrainCore")
                self.assertNotIn(m.split(".")[0], ("server", "lumina"),
                                 f"{fname} imports runtime module")

    def test_server_does_not_wire_workspace_switch(self):
        # Dormant: no runtime switch path wired this milestone.
        src = (backend_dir / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("WorkspaceSync", src)
        self.assertNotIn("workspace_sync", src)


if __name__ == '__main__':
    unittest.main()
