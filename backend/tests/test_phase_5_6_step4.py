"""
tests/test_phase_5_6_step4.py — Phase 5.6.4: WorkspaceMemoryManager + DI

Manager coordinates the active WorkspaceMemory via the store. Dormant DI
registration; no consumer, no ProjectManager/Brain coupling.
"""

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
from brain.workspace.memory import WorkspaceMemory
from brain.workspace.models import Note


class TestManagerBehavior(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = WorkspaceMemoryStore()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _ws(self, name, seed_note=None):
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        if seed_note is not None:
            m = WorkspaceMemory(name)
            m.add_note(Note(title=seed_note))
            self.store.save(d, m)
        return d

    def test_starts_empty(self):
        mgr = WorkspaceMemoryManager(store=self.store)
        cur = mgr.current()
        self.assertIsInstance(cur, WorkspaceMemory)
        self.assertEqual(cur.list_notes(), [])

    def test_switch_loads_memory(self):
        d = self._ws("A", seed_note="a-note")
        mgr = WorkspaceMemoryManager(store=self.store)
        cur = mgr.switch(d)
        self.assertEqual([n.title for n in cur.list_notes()], ["a-note"])
        self.assertIs(mgr.current(), cur)

    def test_switch_missing_returns_empty(self):
        mgr = WorkspaceMemoryManager(store=self.store)
        cur = mgr.switch(self.root / "nope")
        self.assertEqual(cur.list_notes(), [])

    def test_multiple_switches_replace(self):
        da = self._ws("A", seed_note="a")
        db = self._ws("B", seed_note="b")
        mgr = WorkspaceMemoryManager(store=self.store)
        mgr.switch(da)
        self.assertEqual([n.title for n in mgr.current().list_notes()], ["a"])
        mgr.switch(db)
        self.assertEqual([n.title for n in mgr.current().list_notes()], ["b"])

    def test_clear_resets(self):
        d = self._ws("A", seed_note="a")
        mgr = WorkspaceMemoryManager(store=self.store)
        mgr.switch(d)
        mgr.clear()
        self.assertEqual(mgr.current().list_notes(), [])

    def test_deterministic(self):
        d = self._ws("A", seed_note="a")
        mgr = WorkspaceMemoryManager(store=self.store)
        a = mgr.switch(d).snapshot().model_dump()
        b = mgr.switch(d).snapshot().model_dump()
        self.assertEqual(a, b)

    def test_default_store_created(self):
        # No store arg → manager builds its own WorkspaceMemoryStore.
        mgr = WorkspaceMemoryManager()
        self.assertIsInstance(mgr.current(), WorkspaceMemory)


class TestDIRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()
        cls.facade = RuntimeFacade(cls.container)

    def test_manager_registered(self):
        m = self.container.resolve(WorkspaceMemoryManager)
        self.assertIsInstance(m, WorkspaceMemoryManager)
        self.assertIs(m, self.container.resolve(WorkspaceMemoryManager))

    def test_store_registered(self):
        s = self.container.resolve(WorkspaceMemoryStore)
        self.assertIsInstance(s, WorkspaceMemoryStore)

    def test_facade_exposes_manager(self):
        self.assertIs(self.facade.workspace_memory_manager,
                      self.container.resolve(WorkspaceMemoryManager))

    def test_metadata_registry_unchanged(self):
        from core.metadata import ServiceMetadataRegistry
        self.assertEqual(len(self.container.resolve(ServiceMetadataRegistry)), 11)

    def test_skill_registry_still_19(self):
        from brain.skills.registry import SkillRegistry
        self.assertEqual(len(self.container.resolve(SkillRegistry)), 19)


class TestNoForbiddenImports(unittest.TestCase):
    def test_manager_imports_workspace_only(self):
        import ast
        src = (backend_dir / "brain" / "workspace" / "manager.py").read_text(encoding="utf-8")
        mods = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
            elif isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
        for m in mods:
            root = m.split(".")[0]
            self.assertNotIn(root, ("server", "lumina"),
                             f"manager must not import runtime module '{m}'")
            self.assertNotIn("planning", m, "manager must not import planner")
            self.assertNotIn("brain.core", m, "manager must not import BrainCore")
            self.assertNotIn("project_manager", m, "manager must not import ProjectManager")


if __name__ == '__main__':
    unittest.main()
