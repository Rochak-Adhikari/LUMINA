"""
tests/test_phase_5_6_step1.py — Phase 5.6.1: Workspace Memory models

Frozen, serializable value objects. No logic, no I/O, no consumer yet.
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

from brain.workspace.models import (
    ProjectInfo, Decision, Note, WorkspaceTask, WorkspaceSnapshot,
)


class TestFrozen(unittest.TestCase):
    def test_project_info_frozen(self):
        p = ProjectInfo(name="Lumina")
        with self.assertRaises(Exception):
            p.name = "x"

    def test_records_frozen(self):
        for obj, attr in (
            (Decision(title="d"), "title"),
            (Note(title="n"), "title"),
            (WorkspaceTask(title="t"), "status"),
            (WorkspaceSnapshot(workspace="w"), "workspace"),
        ):
            with self.assertRaises(Exception):
                setattr(obj, attr, "changed")


class TestDefaults(unittest.TestCase):
    def test_project_info_defaults(self):
        p = ProjectInfo(name="Lumina")
        self.assertEqual(p.description, "")
        self.assertEqual(p.architecture, "")
        self.assertEqual(p.metadata, {})

    def test_task_default_status(self):
        self.assertEqual(WorkspaceTask(title="t").status, "open")

    def test_unique_ids(self):
        self.assertNotEqual(Decision(title="a").id, Decision(title="b").id)
        self.assertNotEqual(Note(title="a").id, Note(title="b").id)
        self.assertNotEqual(WorkspaceTask(title="a").id, WorkspaceTask(title="b").id)

    def test_snapshot_defaults_empty(self):
        s = WorkspaceSnapshot(workspace="w")
        self.assertIsNone(s.info)
        self.assertEqual(s.decisions, [])
        self.assertEqual(s.notes, [])
        self.assertEqual(s.tasks, [])


class TestSerialization(unittest.TestCase):
    def test_snapshot_roundtrip(self):
        s = WorkspaceSnapshot(
            workspace="Lumina",
            info=ProjectInfo(name="Lumina", description="assistant",
                             architecture="layered", metadata={"phase": "5.6"}),
            decisions=[Decision(title="use JSON persistence", rationale="simple",
                                tags=["persistence"])],
            notes=[Note(title="note", body="b", tags=["t"])],
            tasks=[WorkspaceTask(title="wire brain", status="open")],
        )
        dumped = s.model_dump_json()
        again = WorkspaceSnapshot.model_validate_json(dumped)
        self.assertEqual(again.workspace, "Lumina")
        self.assertEqual(again.info.name, "Lumina")
        self.assertEqual(again.decisions[0].tags, ["persistence"])
        self.assertEqual(again.tasks[0].status, "open")

    def test_no_callables_in_dump(self):
        # Pure data: model_dump yields JSON-native types only.
        d = WorkspaceSnapshot(workspace="w",
                              info=ProjectInfo(name="w")).model_dump()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["workspace"], "w")


if __name__ == '__main__':
    unittest.main()
