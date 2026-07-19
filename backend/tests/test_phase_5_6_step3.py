"""
tests/test_phase_5_6_step3.py — Phase 5.6.3: WorkspaceMemoryStore (persistence)

JSON load/save only. Atomic writes, safe recovery, isolation. No DI, no
consumer, no ProjectManager.
"""

import json
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

from brain.workspace.memory import WorkspaceMemory
from brain.workspace.store import WorkspaceMemoryStore
from brain.workspace.models import ProjectInfo, Decision, Note, WorkspaceTask


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = WorkspaceMemoryStore()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _ws(self, name):
        p = self.root / name
        p.mkdir(parents=True, exist_ok=True)
        return p


class TestSaveLoad(_Tmp):
    def test_missing_file_returns_empty(self):
        mem = self.store.load(self._ws("A"))
        self.assertIsInstance(mem, WorkspaceMemory)
        self.assertIsNone(mem.project_info())
        self.assertEqual(mem.list_notes(), [])

    def test_missing_dir_returns_empty(self):
        mem = self.store.load(self.root / "does_not_exist")
        self.assertIsInstance(mem, WorkspaceMemory)

    def test_save_creates_file(self):
        d = self._ws("A")
        self.store.save(d, WorkspaceMemory("A"))
        self.assertTrue((d / "workspace_memory.json").exists())

    def test_save_writes_valid_json(self):
        d = self._ws("A")
        m = WorkspaceMemory("A")
        m.set_project_info(ProjectInfo(name="A"))
        self.store.save(d, m)
        data = json.loads((d / "workspace_memory.json").read_text(encoding="utf-8"))
        self.assertEqual(data["workspace"], "A")
        self.assertEqual(data["info"]["name"], "A")

    def test_round_trip_populated(self):
        d = self._ws("Lumina")
        m = WorkspaceMemory("Lumina")
        m.set_project_info(ProjectInfo(name="Lumina", description="asst",
                                       architecture="layered",
                                       metadata={"phase": "5.6"}))
        m.add_decision(Decision(title="json persist", rationale="simple",
                                tags=["persistence"]))
        m.add_note(Note(title="n", body="b", tags=["t"]))
        m.add_task(WorkspaceTask(title="wire", status="open"))
        self.store.save(d, m)

        loaded = self.store.load(d)
        s = loaded.snapshot()
        self.assertEqual(s.info.name, "Lumina")
        self.assertEqual(s.info.metadata, {"phase": "5.6"})
        self.assertEqual(s.decisions[0].tags, ["persistence"])
        self.assertEqual(s.notes[0].body, "b")
        self.assertEqual(s.tasks[0].status, "open")

    def test_round_trip_empty(self):
        d = self._ws("E")
        self.store.save(d, WorkspaceMemory("E"))
        loaded = self.store.load(d)
        self.assertIsNone(loaded.project_info())
        self.assertEqual(loaded.snapshot().workspace, "E")

    def test_insertion_order_preserved(self):
        d = self._ws("O")
        m = WorkspaceMemory("O")
        for i in range(5):
            m.add_note(Note(title=f"n{i}"))
        self.store.save(d, m)
        titles = [n.title for n in self.store.load(d).list_notes()]
        self.assertEqual(titles, ["n0", "n1", "n2", "n3", "n4"])

    def test_ids_preserved(self):
        d = self._ws("I")
        m = WorkspaceMemory("I")
        m.add_decision(Decision(title="d", id="fixed-id"))
        self.store.save(d, m)
        self.assertEqual(self.store.load(d).list_decisions()[0].id, "fixed-id")


class TestCorruptAndRecovery(_Tmp):
    def test_corrupt_json_returns_empty(self):
        d = self._ws("C")
        (d / "workspace_memory.json").write_text("{ not valid json ", encoding="utf-8")
        mem = self.store.load(d)
        self.assertIsInstance(mem, WorkspaceMemory)
        self.assertIsNone(mem.project_info())

    def test_non_object_json_returns_empty(self):
        d = self._ws("C2")
        (d / "workspace_memory.json").write_text("[1,2,3]", encoding="utf-8")
        self.assertIsNone(self.store.load(d).project_info())

    def test_malformed_record_skipped(self):
        d = self._ws("C3")
        payload = {"workspace": "C3", "notes": [{"title": "ok"}, {"bad": 1}]}
        (d / "workspace_memory.json").write_text(json.dumps(payload), encoding="utf-8")
        notes = self.store.load(d).list_notes()
        # The valid note loads; the malformed one is skipped (no title).
        self.assertEqual([n.title for n in notes], ["ok"])


class TestAtomicAndIsolation(_Tmp):
    def test_no_tmp_left_after_save(self):
        d = self._ws("A")
        self.store.save(d, WorkspaceMemory("A"))
        leftovers = list(d.glob("*.tmp"))
        self.assertEqual(leftovers, [])

    def test_overwrite_replaces_cleanly(self):
        d = self._ws("A")
        m1 = WorkspaceMemory("A"); m1.add_note(Note(title="first"))
        self.store.save(d, m1)
        m2 = WorkspaceMemory("A"); m2.add_note(Note(title="second"))
        self.store.save(d, m2)
        notes = [n.title for n in self.store.load(d).list_notes()]
        self.assertEqual(notes, ["second"])  # full replace, not append

    def test_two_workspaces_isolated(self):
        da, db = self._ws("A"), self._ws("B")
        ma = WorkspaceMemory("A"); ma.add_note(Note(title="a"))
        mb = WorkspaceMemory("B"); mb.add_note(Note(title="b"))
        self.store.save(da, ma)
        self.store.save(db, mb)
        self.assertEqual([n.title for n in self.store.load(da).list_notes()], ["a"])
        self.assertEqual([n.title for n in self.store.load(db).list_notes()], ["b"])


class TestNoRuntimeImports(unittest.TestCase):
    def test_store_imports_workspace_only(self):
        import ast
        src = (backend_dir / "brain" / "workspace" / "store.py").read_text(encoding="utf-8")
        mods = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
            elif isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
        for m in mods:
            root = m.split(".")[0]
            self.assertNotIn(root, ("server", "lumina", "core"),
                             f"store must not import runtime module '{m}'")
            self.assertNotIn("planning", m)
            self.assertNotIn("skills", m)


if __name__ == '__main__':
    unittest.main()
