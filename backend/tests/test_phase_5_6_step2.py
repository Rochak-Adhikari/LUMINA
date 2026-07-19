"""
tests/test_phase_5_6_step2.py — Phase 5.6.2: WorkspaceMemory (in-memory)

Pure in-memory structured store. No persistence, no DI, no consumer.
"""

import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from brain.workspace.memory import WorkspaceMemory
from brain.workspace.interfaces import IWorkspaceMemory
from brain.workspace.models import (
    ProjectInfo, Decision, Note, WorkspaceTask, WorkspaceSnapshot,
)


class TestProjectInfo(unittest.TestCase):
    def test_set_get(self):
        m = WorkspaceMemory("Lumina")
        self.assertIsNone(m.project_info())
        info = ProjectInfo(name="Lumina", description="assistant")
        m.set_project_info(info)
        self.assertIs(m.project_info(), info)

    def test_set_replaces(self):
        m = WorkspaceMemory()
        m.set_project_info(ProjectInfo(name="A"))
        m.set_project_info(ProjectInfo(name="B"))
        self.assertEqual(m.project_info().name, "B")


class TestRecords(unittest.TestCase):
    def setUp(self):
        self.m = WorkspaceMemory("w")

    def test_add_list_decisions_order(self):
        self.m.add_decision(Decision(title="d1"))
        self.m.add_decision(Decision(title="d2"))
        self.assertEqual([d.title for d in self.m.list_decisions()], ["d1", "d2"])

    def test_add_list_notes_order(self):
        self.m.add_note(Note(title="n1"))
        self.m.add_note(Note(title="n2"))
        self.assertEqual([n.title for n in self.m.list_notes()], ["n1", "n2"])

    def test_add_list_tasks_order(self):
        self.m.add_task(WorkspaceTask(title="t1"))
        self.m.add_task(WorkspaceTask(title="t2", status="done"))
        tasks = self.m.list_tasks()
        self.assertEqual([t.title for t in tasks], ["t1", "t2"])
        self.assertEqual(tasks[1].status, "done")

    def test_list_returns_copy(self):
        self.m.add_note(Note(title="n"))
        got = self.m.list_notes()
        got.append(Note(title="rogue"))
        self.assertEqual(len(self.m.list_notes()), 1)  # internal not mutated


class TestSnapshot(unittest.TestCase):
    def test_snapshot_contents(self):
        m = WorkspaceMemory("Lumina")
        m.set_project_info(ProjectInfo(name="Lumina"))
        m.add_decision(Decision(title="d"))
        m.add_note(Note(title="n"))
        m.add_task(WorkspaceTask(title="t"))
        s = m.snapshot()
        self.assertIsInstance(s, WorkspaceSnapshot)
        self.assertEqual(s.workspace, "Lumina")
        self.assertEqual(s.info.name, "Lumina")
        self.assertEqual(len(s.decisions), 1)
        self.assertEqual(len(s.notes), 1)
        self.assertEqual(len(s.tasks), 1)

    def test_snapshot_frozen(self):
        s = WorkspaceMemory("w").snapshot()
        with self.assertRaises(Exception):
            s.workspace = "x"

    def test_snapshot_decoupled_from_later_mutation(self):
        m = WorkspaceMemory("w")
        m.add_note(Note(title="n1"))
        s = m.snapshot()
        m.add_note(Note(title="n2"))
        self.assertEqual(len(s.notes), 1)  # snapshot is a point-in-time copy

    def test_empty_snapshot(self):
        s = WorkspaceMemory("w").snapshot()
        self.assertIsNone(s.info)
        self.assertEqual(s.decisions, [])
        self.assertEqual(s.notes, [])
        self.assertEqual(s.tasks, [])

    def test_deterministic_repeatable(self):
        m = WorkspaceMemory("w")
        m.add_decision(Decision(title="d", id="fixed"))
        a = m.snapshot().model_dump()
        b = m.snapshot().model_dump()
        self.assertEqual(a, b)


class TestClearAndIsolation(unittest.TestCase):
    def test_clear(self):
        m = WorkspaceMemory("w")
        m.set_project_info(ProjectInfo(name="w"))
        m.add_decision(Decision(title="d"))
        m.add_note(Note(title="n"))
        m.add_task(WorkspaceTask(title="t"))
        m.clear()
        self.assertIsNone(m.project_info())
        self.assertEqual(m.list_decisions(), [])
        self.assertEqual(m.list_notes(), [])
        self.assertEqual(m.list_tasks(), [])

    def test_instance_isolation(self):
        a = WorkspaceMemory("A")
        b = WorkspaceMemory("B")
        a.add_note(Note(title="a-note"))
        self.assertEqual(len(b.list_notes()), 0)
        self.assertEqual(b.snapshot().workspace, "B")

    def test_implements_interface(self):
        self.assertIsInstance(WorkspaceMemory(), IWorkspaceMemory)


if __name__ == '__main__':
    unittest.main()
