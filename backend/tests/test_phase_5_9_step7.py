"""
tests/test_phase_5_9_step7.py — Milestone 5.9.7 Verification (Workspace-aware Planning)

Verifies the read-only enrichment path that carries prepared workspace recall
to the planner via BrainContext:

  - WorkspaceRecallContext: frozen, four fields, each ALWAYS a valid
    WorkspaceRetrievalResult (no None), append-only defaults
  - BrainContext.workspace_recall present, defaults empty (unchanged behavior)
  - ContextBuilder is the sole enrichment point: injects recall services,
    delegates (never retrieves itself), failure-safe / absence-safe
  - query derived verbatim from request text (deterministic)
  - planner never imports workspace retrieval / memory
  - no import cycle (brain.workspace must not import brain.core)
  - deterministic, frozen, read-only

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
    WorkspaceRecallContext,
)
from brain.core.models import BrainContext, BrainRequest
from brain.core.context_builder import ContextBuilder


class _SpyRecall:
    """Recall service stand-in; records the query, returns a canned result."""

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self.queries = []

    def recall(self, query: str) -> WorkspaceRetrievalResult:
        self.queries.append(query)
        return WorkspaceRetrievalResult(
            query=query,
            hits=[RetrievalHit(record_type=self._kind, record_id="x", record=object())],
        )


class _BoomRecall:
    def recall(self, query: str):
        raise RuntimeError("recall blew up")


class TestRecallContextModel(unittest.TestCase):
    def test_defaults_are_empty_valid_results(self):
        ctx = WorkspaceRecallContext()
        for field in (ctx.decisions, ctx.notes, ctx.tasks, ctx.architecture):
            self.assertIsInstance(field, WorkspaceRetrievalResult)
            self.assertEqual(field.hits, [])
            self.assertEqual(field.query, "")

    def test_no_none_state(self):
        ctx = WorkspaceRecallContext()
        # Consumers access .decisions.hits with no None checks.
        self.assertEqual(ctx.decisions.hits, [])

    def test_frozen(self):
        ctx = WorkspaceRecallContext()
        with self.assertRaises(Exception):
            ctx.decisions = WorkspaceRetrievalResult(query="x")

    def test_distinct_default_instances(self):
        a = WorkspaceRecallContext()
        b = WorkspaceRecallContext()
        self.assertIsNot(a.decisions, b.decisions)  # default_factory, not shared


class TestBrainContextField(unittest.TestCase):
    def test_field_present_default_empty(self):
        bc = BrainContext(request=BrainRequest(text="hi"))
        self.assertIsInstance(bc.workspace_recall, WorkspaceRecallContext)
        self.assertEqual(bc.workspace_recall.decisions.hits, [])


class TestContextBuilderEnrichment(unittest.TestCase):
    def test_absence_safe_default_empty(self):
        # No recall services injected → unchanged behavior.
        bc = ContextBuilder().build(BrainRequest(text="anything"))
        self.assertEqual(bc.workspace_recall.decisions.hits, [])
        self.assertEqual(bc.workspace_recall.architecture.hits, [])

    def test_delegates_to_each_service(self):
        d, n, t, a = _SpyRecall("decision"), _SpyRecall("note"), _SpyRecall("task"), _SpyRecall("architecture")
        cb = ContextBuilder(
            decision_recall=d, notes_recall=n, task_recall=t, architecture_recall=a
        )
        bc = cb.build(BrainRequest(text="find auth"))
        self.assertEqual(bc.workspace_recall.decisions.hits[0].record_type, "decision")
        self.assertEqual(bc.workspace_recall.notes.hits[0].record_type, "note")
        self.assertEqual(bc.workspace_recall.tasks.hits[0].record_type, "task")
        self.assertEqual(bc.workspace_recall.architecture.hits[0].record_type, "architecture")

    def test_query_derived_verbatim(self):
        d = _SpyRecall("decision")
        ContextBuilder(decision_recall=d).build(BrainRequest(text="  Find Auth  "))
        self.assertEqual(d.queries, ["Find Auth"])  # stripped, otherwise verbatim

    def test_empty_text_yields_empty_query(self):
        d = _SpyRecall("decision")
        ContextBuilder(decision_recall=d).build(BrainRequest(text=None))
        self.assertEqual(d.queries, [""])

    def test_failure_safe(self):
        cb = ContextBuilder(decision_recall=_BoomRecall())
        bc = cb.build(BrainRequest(text="x"))  # must not raise
        self.assertEqual(bc.workspace_recall.decisions.hits, [])

    def test_deterministic(self):
        d = _SpyRecall("decision")
        cb = ContextBuilder(decision_recall=d)
        a = cb.build(BrainRequest(text="q"))
        b = cb.build(BrainRequest(text="q"))
        self.assertEqual(
            [h.record_type for h in a.workspace_recall.decisions.hits],
            [h.record_type for h in b.workspace_recall.decisions.hits],
        )


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

    def test_no_import_cycle_workspace_never_imports_core(self):
        for rel in [
            "brain/workspace/models.py",
            "brain/workspace/interfaces.py",
            "brain/workspace/retriever.py",
            "brain/workspace/recall.py",
            "brain/workspace/manager.py",
        ]:
            modules = self._imports(rel)
            for m in modules:
                self.assertFalse(
                    m.startswith("brain.core"),
                    f"{rel} imports {m} — would create a cycle",
                )

    def test_planner_never_imports_workspace(self):
        for rel in ["brain/planning/rule_planner.py", "brain/planning/llm_planner.py"]:
            modules = self._imports(rel)
            for banned in [
                "brain.workspace.memory",
                "brain.workspace.retriever",
                "brain.workspace.manager",
                "brain.workspace.store",
                "brain.workspace.sync",
                "brain.workspace.recall",
            ]:
                self.assertNotIn(banned, modules, f"{rel} must not import {banned}")

    def test_planner_no_workspace_snapshot_access(self):
        for rel in ["brain/planning/rule_planner.py", "brain/planning/llm_planner.py"]:
            src = (backend_dir / rel).read_text(encoding="utf-8")
            self.assertNotIn(".snapshot(", src, f"{rel} must not touch snapshots")


if __name__ == "__main__":
    unittest.main()
