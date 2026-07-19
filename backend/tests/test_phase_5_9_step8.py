"""
tests/test_phase_5_9_step8.py — Milestone 5.9.8 Verification (Workspace-aware Prompting)

Verifies the prompt-safe projection layer:

  - PromptWorkspaceContext: frozen, deterministic, append-only, prompt-safe
    (only lists of strings; no retrieval/runtime objects)
  - Built ONLY from WorkspaceRecallContext (via from_recall)
  - ContextBuilder populates BrainContext.prompt_workspace from the same recall
  - runtime unchanged (empty by default)
  - import graph acyclic; prompt-safe model carries no retrieval leakage

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
    Note,
    WorkspaceTask,
    RetrievalHit,
    WorkspaceRetrievalResult,
    WorkspaceRecallContext,
    PromptWorkspaceContext,
)
from brain.core.models import BrainContext, BrainRequest
from brain.core.context_builder import ContextBuilder


def _recall_with_hits() -> WorkspaceRecallContext:
    return WorkspaceRecallContext(
        decisions=WorkspaceRetrievalResult(
            query="q",
            hits=[
                RetrievalHit(record_type="decision", record_id="d1",
                             record=Decision(id="d1", title="Use pydantic")),
                RetrievalHit(record_type="decision", record_id="d2",
                             record=Decision(id="d2", title="Async loop")),
            ],
        ),
        notes=WorkspaceRetrievalResult(
            query="q",
            hits=[RetrievalHit(record_type="note", record_id="n1",
                               record=Note(id="n1", title="Cleanup"))],
        ),
        tasks=WorkspaceRetrievalResult(
            query="q",
            hits=[RetrievalHit(record_type="task", record_id="t1",
                               record=WorkspaceTask(id="t1", title="Wire it"))],
        ),
    )


class TestPromptModel(unittest.TestCase):
    def test_frozen(self):
        p = PromptWorkspaceContext()
        with self.assertRaises(Exception):
            p.decisions = ["x"]

    def test_defaults_empty_lists(self):
        p = PromptWorkspaceContext()
        self.assertEqual((p.decisions, p.notes, p.tasks, p.architecture), ([], [], [], []))

    def test_distinct_default_instances(self):
        self.assertIsNot(PromptWorkspaceContext().decisions, PromptWorkspaceContext().decisions)

    def test_only_string_lists(self):
        p = PromptWorkspaceContext.from_recall(_recall_with_hits())
        for lst in (p.decisions, p.notes, p.tasks, p.architecture):
            self.assertTrue(all(isinstance(x, str) for x in lst))

    def test_from_recall_projects_titles(self):
        p = PromptWorkspaceContext.from_recall(_recall_with_hits())
        self.assertEqual(p.decisions, ["Use pydantic", "Async loop"])
        self.assertEqual(p.notes, ["Cleanup"])
        self.assertEqual(p.tasks, ["Wire it"])
        self.assertEqual(p.architecture, [])

    def test_deterministic(self):
        r = _recall_with_hits()
        self.assertEqual(
            PromptWorkspaceContext.from_recall(r).model_dump(),
            PromptWorkspaceContext.from_recall(r).model_dump(),
        )

    def test_order_preserved(self):
        p = PromptWorkspaceContext.from_recall(_recall_with_hits())
        self.assertEqual(p.decisions, ["Use pydantic", "Async loop"])  # insertion order

    def test_empty_recall_empty_prompt(self):
        p = PromptWorkspaceContext.from_recall(WorkspaceRecallContext())
        self.assertEqual((p.decisions, p.notes, p.tasks, p.architecture), ([], [], [], []))


class TestContextBuilder(unittest.TestCase):
    def test_field_present_default_empty(self):
        bc = ContextBuilder().build(BrainRequest(text="hi"))
        self.assertIsInstance(bc.prompt_workspace, PromptWorkspaceContext)
        self.assertEqual(bc.prompt_workspace.decisions, [])

    def test_prompt_derived_from_same_recall(self):
        class _Spy:
            def recall(self, q):
                return WorkspaceRetrievalResult(
                    query=q,
                    hits=[RetrievalHit(record_type="decision", record_id="d1",
                                       record=Decision(id="d1", title="Titled"))],
                )
        bc = ContextBuilder(decision_recall=_Spy()).build(BrainRequest(text="q"))
        # prompt_workspace projection matches workspace_recall content
        self.assertEqual(bc.prompt_workspace.decisions, ["Titled"])
        self.assertEqual(bc.workspace_recall.decisions.hits[0].record.title, "Titled")


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

    def test_no_cycle_workspace_never_imports_core(self):
        for rel in [
            "brain/workspace/models.py",
            "brain/workspace/interfaces.py",
            "brain/workspace/retriever.py",
            "brain/workspace/recall.py",
        ]:
            for m in self._imports(rel):
                self.assertFalse(m.startswith("brain.core"), f"{rel} imports {m}")

    def test_prompt_model_is_prompt_safe(self):
        # PromptWorkspaceContext fields resolve to List[str] — no retrieval types.
        import typing
        hints = typing.get_type_hints(PromptWorkspaceContext)
        for name in ("decisions", "notes", "tasks", "architecture"):
            self.assertEqual(hints[name], typing.List[str])

    def test_planner_no_workspace_imports(self):
        for rel in ["brain/planning/rule_planner.py", "brain/planning/llm_planner.py"]:
            modules = self._imports(rel)
            for banned in [
                "brain.workspace.memory", "brain.workspace.retriever",
                "brain.workspace.manager", "brain.workspace.store",
                "brain.workspace.sync", "brain.workspace.recall",
            ]:
                self.assertNotIn(banned, modules, f"{rel} must not import {banned}")


if __name__ == "__main__":
    unittest.main()
