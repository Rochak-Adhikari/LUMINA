"""
tests/test_phase_5_9_step456.py — Milestones 5.9.4–5.9.6 Verification

NotesRecall (5.9.4), TaskRecall (5.9.5), ArchitectureRecall (5.9.6):
thin read-only wrappers over the frozen WorkspaceRetriever.

For each service:
  - delegates exactly once
  - forwards query unchanged
  - passes the correct record_type
  - returns WorkspaceRetrievalResult unchanged
  - no snapshot / WorkspaceMemory / manager access
  - no duplicated retrieval logic
  - deterministic, read-only
  - depends on IWorkspaceRetriever, not concrete WorkspaceRetriever
  - import whitelist / acyclic

Stdlib unittest; no heavy deps.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.workspace.models import RetrievalHit, WorkspaceRetrievalResult
from brain.workspace.interfaces import (
    INotesRecall,
    ITaskRecall,
    IArchitectureRecall,
)
from brain.workspace.recall import NotesRecall, TaskRecall, ArchitectureRecall


class _SpyRetriever:
    """IWorkspaceRetriever stand-in recording calls; returns a canned result."""

    def __init__(self, result: WorkspaceRetrievalResult) -> None:
        self._result = result
        self.calls = []  # (query, record_type, tags)

    def retrieve(self, query, *, record_type=None, tags=None):
        self.calls.append((query, record_type, tags))
        return self._result


def _canned(kind: str) -> WorkspaceRetrievalResult:
    return WorkspaceRetrievalResult(
        query="q",
        hits=[RetrievalHit(record_type=kind, record_id="x", record=object())],
    )


# (RecallClass, Interface, expected record_type)
_CASES = [
    (NotesRecall, INotesRecall, "note"),
    (TaskRecall, ITaskRecall, "task"),
    (ArchitectureRecall, IArchitectureRecall, "architecture"),
]


class TestRecallConsumers(unittest.TestCase):
    def test_is_interface(self):
        for cls, iface, kind in _CASES:
            self.assertIsInstance(cls(_SpyRetriever(_canned(kind))), iface)

    def test_delegates_once(self):
        for cls, iface, kind in _CASES:
            spy = _SpyRetriever(_canned(kind))
            cls(spy).recall("q")
            self.assertEqual(len(spy.calls), 1, cls.__name__)

    def test_correct_record_type(self):
        for cls, iface, kind in _CASES:
            spy = _SpyRetriever(_canned(kind))
            cls(spy).recall("q")
            self.assertEqual(spy.calls[0][1], kind, cls.__name__)

    def test_query_forwarded_unchanged(self):
        for cls, iface, kind in _CASES:
            spy = _SpyRetriever(_canned(kind))
            cls(spy).recall("  Raw Query  ")
            self.assertEqual(spy.calls[0][0], "  Raw Query  ", cls.__name__)

    def test_no_tags(self):
        for cls, iface, kind in _CASES:
            spy = _SpyRetriever(_canned(kind))
            cls(spy).recall("q")
            self.assertIsNone(spy.calls[0][2], cls.__name__)

    def test_result_passed_through_unchanged(self):
        for cls, iface, kind in _CASES:
            result = _canned(kind)
            spy = _SpyRetriever(result)
            self.assertIs(cls(spy).recall("q"), result, cls.__name__)

    def test_returns_generic_result(self):
        for cls, iface, kind in _CASES:
            out = cls(_SpyRetriever(_canned(kind))).recall("q")
            self.assertIsInstance(out, WorkspaceRetrievalResult, cls.__name__)

    def test_deterministic(self):
        for cls, iface, kind in _CASES:
            spy = _SpyRetriever(_canned(kind))
            r = cls(spy)
            r.recall("q")
            r.recall("q")
            self.assertEqual(
                spy.calls, [("q", kind, None), ("q", kind, None)], cls.__name__
            )

    def test_read_only_no_snapshot_access(self):
        for cls, iface, kind in _CASES:
            spy = _SpyRetriever(_canned(kind))
            self.assertFalse(hasattr(spy, "snapshot"))
            self.assertFalse(hasattr(spy, "current"))
            cls(spy).recall("q")  # must not raise


class TestBoundaries(unittest.TestCase):
    def _imports(self, rel):
        src = (backend_dir / rel).read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        return modules

    def test_import_whitelist(self):
        modules = self._imports("brain/workspace/recall.py")
        allowed_prefixes = (
            "brain.workspace.interfaces",
            "brain.workspace.models",
            "typing",
            "__future__",
        )
        for m in modules:
            self.assertTrue(m.startswith(allowed_prefixes), f"unexpected import: {m}")

    def test_no_forbidden_coupling(self):
        modules = self._imports("brain/workspace/recall.py")
        forbidden = [
            "brain.workspace.memory",
            "brain.workspace.manager",
            "brain.workspace.store",
            "brain.workspace.sync",
            "brain.workspace.retriever",  # depends on INTERFACE only
            "core.bootstrap",
            "core.runtime_facade",
            "brain.core.brain_core",
            "brain.core.context_builder",
            "brain.reflection.engine",
            "server",
        ]
        for f in forbidden:
            self.assertNotIn(f, modules, f"recall must not import {f}")

    def test_no_duplicated_retrieval_logic(self):
        src = (backend_dir / "brain/workspace/recall.py").read_text(encoding="utf-8")
        for banned in [".lower(", ".snapshot(", ".current(", "for ", " in snapshot"]:
            self.assertNotIn(banned, src, f"recall must not contain retrieval logic: {banned}")


if __name__ == "__main__":
    unittest.main()
