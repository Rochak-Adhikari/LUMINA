"""
tests/test_phase_5_9_step2.py — Milestone 5.9.2 Verification (WorkspaceRetriever)

Verifies the deterministic, read-only retrieval layer over the active
WorkspaceMemory:

  - constructor injection (manager, duck-typed)
  - snapshot-only usage (never private lists)
  - case-insensitive substring retrieval
  - record_type filtering (single generic API)
  - exact tag filtering
  - deterministic ordering (insertion order + fixed kind order)
  - no mutation of WorkspaceMemory
  - empty snapshot / empty query / no matches
  - serialization + frozen result models
  - forbidden imports (no store/sync/runtime/cognitive coupling)
  - no runtime dependencies

Stdlib unittest; no heavy deps.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.workspace.memory import WorkspaceMemory
from brain.workspace.models import (
    ProjectInfo,
    Decision,
    Note,
    WorkspaceTask,
    RetrievalHit,
    WorkspaceRetrievalResult,
)
from brain.workspace.interfaces import IWorkspaceRetriever
from brain.workspace.retriever import WorkspaceRetriever


class _FakeManager:
    """WorkspaceMemoryManager stand-in exposing current() only."""

    def __init__(self, memory: WorkspaceMemory) -> None:
        self._memory = memory
        self.current_calls = 0

    def current(self) -> WorkspaceMemory:
        self.current_calls += 1
        return self._memory


def _populated() -> WorkspaceMemory:
    m = WorkspaceMemory("proj")
    m.set_project_info(
        ProjectInfo(
            name="Lumina",
            description="voice assistant",
            architecture="FastAPI brain layers",
        )
    )
    m.add_decision(
        Decision(id="d1", title="Use pydantic", rationale="frozen models", tags=["arch"])
    )
    m.add_decision(
        Decision(id="d2", title="Async loop", rationale="socketio", tags=["runtime"])
    )
    m.add_note(Note(id="n1", title="Todo cleanup", body="remove dead code", tags=["chore"]))
    m.add_task(WorkspaceTask(id="t1", title="Wire retriever", status="open", notes="phase 5.9"))
    return m


class TestConstructionAndSnapshot(unittest.TestCase):
    def test_constructor_injection(self):
        mgr = _FakeManager(_populated())
        r = WorkspaceRetriever(mgr)
        self.assertIsInstance(r, IWorkspaceRetriever)

    def test_reads_snapshot_only(self):
        mgr = _FakeManager(_populated())
        r = WorkspaceRetriever(mgr)
        r.retrieve("")
        # Retrieval must go through manager.current() (which yields snapshot()).
        self.assertGreaterEqual(mgr.current_calls, 1)


class TestRetrieval(unittest.TestCase):
    def setUp(self):
        self.r = WorkspaceRetriever(_FakeManager(_populated()))

    def test_substring_case_insensitive(self):
        res = self.r.retrieve("PYDANTIC")
        ids = [h.record_id for h in res.hits]
        self.assertIn("d1", ids)
        self.assertNotIn("d2", ids)

    def test_matches_info_fields(self):
        res = self.r.retrieve("fastapi")
        types = [h.record_type for h in res.hits]
        self.assertEqual(types, ["info"])

    def test_record_type_filter(self):
        res = self.r.retrieve("", record_type="task")
        self.assertTrue(all(h.record_type == "task" for h in res.hits))
        self.assertEqual([h.record_id for h in res.hits], ["t1"])

    def test_tag_filter_exact(self):
        res = self.r.retrieve("", tags=["arch"])
        self.assertEqual([h.record_id for h in res.hits], ["d1"])

    def test_tag_filter_excludes_untagged_kinds(self):
        # Tasks/info carry no tags => never match under a tag filter.
        res = self.r.retrieve("", tags=["arch"])
        self.assertTrue(all(h.record_type == "decision" for h in res.hits))

    def test_empty_query_returns_all(self):
        res = self.r.retrieve("")
        # info + 2 decisions + 1 note + 1 task = 5
        self.assertEqual(len(res.hits), 5)

    def test_no_matches(self):
        res = self.r.retrieve("zzz-nomatch")
        self.assertEqual(res.hits, [])
        self.assertEqual(res.query, "zzz-nomatch")

    def test_deterministic_ordering(self):
        a = self.r.retrieve("")
        b = self.r.retrieve("")
        self.assertEqual(
            [(h.record_type, h.record_id) for h in a.hits],
            [(h.record_type, h.record_id) for h in b.hits],
        )
        # Fixed kind order: info, decision, decision, note, task.
        self.assertEqual(
            [h.record_type for h in a.hits],
            ["info", "decision", "decision", "note", "task"],
        )

    def test_empty_snapshot(self):
        r = WorkspaceRetriever(_FakeManager(WorkspaceMemory()))
        res = r.retrieve("")
        self.assertEqual(res.hits, [])


class TestNoMutation(unittest.TestCase):
    def test_retrieve_does_not_mutate_memory(self):
        mem = _populated()
        before = mem.snapshot()
        r = WorkspaceRetriever(_FakeManager(mem))
        r.retrieve("pydantic", record_type="decision", tags=["arch"])
        after = mem.snapshot()
        self.assertEqual(before, after)


class TestModels(unittest.TestCase):
    def test_result_frozen(self):
        res = WorkspaceRetrievalResult(query="q", hits=[])
        with self.assertRaises(Exception):
            res.query = "mutated"

    def test_hit_frozen(self):
        hit = RetrievalHit(record_type="note", record_id="n1", record=Note(title="x"))
        with self.assertRaises(Exception):
            hit.record_type = "task"

    def test_serialization_roundtrip(self):
        res = WorkspaceRetriever(_FakeManager(_populated())).retrieve("", record_type="note")
        dumped = res.model_dump()
        self.assertEqual(dumped["query"], "")
        self.assertEqual(dumped["hits"][0]["record_type"], "note")
        rebuilt = WorkspaceRetrievalResult(**res.model_dump())
        self.assertEqual(rebuilt.query, res.query)

    def test_record_type_is_free_string(self):
        # No enum constraint — arbitrary future kinds accepted.
        hit = RetrievalHit(record_type="architecture", record=object())
        self.assertEqual(hit.record_type, "architecture")


class TestBoundaries(unittest.TestCase):
    def test_forbidden_imports(self):
        src = (backend_dir / "brain" / "workspace" / "retriever.py").read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        forbidden = [
            "brain.workspace.store",
            "brain.workspace.sync",
            "brain.workspace.manager",
            "core.bootstrap",
            "core.runtime_facade",
            "core.project_manager",
            "brain.core.brain_core",
            "brain.core.context_builder",
            "brain.reflection.engine",
            "server",
        ]
        for f in forbidden:
            self.assertNotIn(f, modules, f"retriever must not import {f}")

    def test_only_workspace_and_stdlib_imports(self):
        src = (backend_dir / "brain" / "workspace" / "retriever.py").read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        allowed_prefixes = ("brain.workspace.interfaces", "brain.workspace.models", "typing", "__future__")
        for m in modules:
            self.assertTrue(
                m.startswith(allowed_prefixes),
                f"unexpected import: {m}",
            )


if __name__ == "__main__":
    unittest.main()
