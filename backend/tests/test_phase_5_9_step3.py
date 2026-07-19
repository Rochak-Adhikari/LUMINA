"""
tests/test_phase_5_9_step3.py — Milestone 5.9.3 Verification (DecisionRecall)

Verifies the first consumer of the frozen WorkspaceRetriever:

  - delegates exactly once to retriever.retrieve
  - passes record_type="decision"
  - query forwarded unchanged
  - no direct WorkspaceMemory / manager / snapshot access
  - no duplicated retrieval logic (substring/tag/iteration)
  - return value passed through unchanged (generic result reused)
  - deterministic
  - read-only
  - import whitelist
  - acyclic architecture

Stdlib unittest; no heavy deps.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.workspace.models import (
    Decision,
    RetrievalHit,
    WorkspaceRetrievalResult,
)
from brain.workspace.interfaces import IDecisionRecall
from brain.workspace.recall import DecisionRecall


class _SpyRetriever:
    """IWorkspaceRetriever stand-in recording calls; returns a canned result."""

    def __init__(self, result: WorkspaceRetrievalResult) -> None:
        self._result = result
        self.calls = []  # list of (query, record_type, tags)

    def retrieve(self, query, *, record_type=None, tags=None):
        self.calls.append((query, record_type, tags))
        return self._result


def _canned() -> WorkspaceRetrievalResult:
    d = Decision(id="d1", title="Use pydantic", rationale="frozen", tags=["arch"])
    return WorkspaceRetrievalResult(
        query="pydantic",
        hits=[RetrievalHit(record_type="decision", record_id="d1", record=d)],
    )


class TestDelegation(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(DecisionRecall(_SpyRetriever(_canned())), IDecisionRecall)

    def test_delegates_once(self):
        spy = _SpyRetriever(_canned())
        DecisionRecall(spy).recall("pydantic")
        self.assertEqual(len(spy.calls), 1)

    def test_passes_record_type_decision(self):
        spy = _SpyRetriever(_canned())
        DecisionRecall(spy).recall("pydantic")
        query, record_type, tags = spy.calls[0]
        self.assertEqual(record_type, "decision")

    def test_query_forwarded_unchanged(self):
        spy = _SpyRetriever(_canned())
        DecisionRecall(spy).recall("  Exact Query  ")
        self.assertEqual(spy.calls[0][0], "  Exact Query  ")

    def test_no_tags_supplied(self):
        spy = _SpyRetriever(_canned())
        DecisionRecall(spy).recall("q")
        self.assertIsNone(spy.calls[0][2])

    def test_result_passed_through_unchanged(self):
        result = _canned()
        spy = _SpyRetriever(result)
        out = DecisionRecall(spy).recall("q")
        self.assertIs(out, result)

    def test_returns_generic_result_type(self):
        out = DecisionRecall(_SpyRetriever(_canned())).recall("q")
        self.assertIsInstance(out, WorkspaceRetrievalResult)

    def test_deterministic(self):
        spy = _SpyRetriever(_canned())
        recall = DecisionRecall(spy)
        a = recall.recall("q")
        b = recall.recall("q")
        self.assertIs(a, b)  # same canned result; no internal state drift
        self.assertEqual(spy.calls, [("q", "decision", None), ("q", "decision", None)])


class TestReadOnly(unittest.TestCase):
    def test_no_snapshot_or_memory_access(self):
        # Retriever spy exposes no snapshot/current/memory; recall must still work,
        # proving DecisionRecall touches only retrieve().
        spy = _SpyRetriever(_canned())
        self.assertFalse(hasattr(spy, "current"))
        self.assertFalse(hasattr(spy, "snapshot"))
        DecisionRecall(spy).recall("q")  # must not raise


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
            "brain.workspace.retriever",  # depends on the INTERFACE, not concrete
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
        # No substring/tag/iteration machinery — pure delegation.
        for banned in [".lower(", ".snapshot(", ".current(", "for ", " in snapshot"]:
            self.assertNotIn(banned, src, f"recall must not contain retrieval logic: {banned}")


if __name__ == "__main__":
    unittest.main()
