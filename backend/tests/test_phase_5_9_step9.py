"""
tests/test_phase_5_9_step9.py — Milestone 5.9.9 (Workspace Context Injection)

Verifies workspace recall is injected into the LLM planner prompt via the
frozen PromptWorkspaceContext contract, deterministically and byte-identically
when empty:

  - _format_workspace_context: empty/absent => "", populated => ordered section
  - sections skipped when empty; insertion order preserved; never sorted
  - prompt injection reaches _build_prompt; empty => no "Workspace Context"
  - planner reads context.prompt_workspace only (List[str] fields)
  - planner imports no workspace retrieval/manager/snapshot
  - deterministic; import graph acyclic

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
    PromptWorkspaceContext,
)
from brain.core.models import BrainContext, BrainRequest
from brain.planning.llm_planner import LLMPlanner
from brain.planning.prompt_builder import format_workspace_context as _format_workspace_context


class TestFormatter(unittest.TestCase):
    def test_none_yields_empty(self):
        self.assertEqual(_format_workspace_context(None), "")

    def test_all_empty_yields_empty(self):
        self.assertEqual(_format_workspace_context(PromptWorkspaceContext()), "")

    def test_populated_section(self):
        p = PromptWorkspaceContext(decisions=["Use pydantic", "Async loop"], tasks=["Wire it"])
        out = _format_workspace_context(p)
        self.assertIn("Workspace Context", out)
        self.assertIn("Decisions\n- Use pydantic\n- Async loop", out)
        self.assertIn("Tasks\n- Wire it", out)

    def test_empty_sections_skipped(self):
        p = PromptWorkspaceContext(decisions=["d"])
        out = _format_workspace_context(p)
        self.assertIn("Decisions", out)
        self.assertNotIn("Notes", out)
        self.assertNotIn("Tasks", out)
        self.assertNotIn("Architecture", out)

    def test_order_preserved_never_sorted(self):
        p = PromptWorkspaceContext(decisions=["zeta", "alpha", "mid"])
        out = _format_workspace_context(p)
        self.assertEqual(out.index("zeta") < out.index("alpha") < out.index("mid"), True)

    def test_deterministic(self):
        p = PromptWorkspaceContext(decisions=["a", "b"], notes=["n"])
        self.assertEqual(_format_workspace_context(p), _format_workspace_context(p))

    def test_no_truncation_no_dedup(self):
        p = PromptWorkspaceContext(decisions=["dup", "dup", "dup"])
        out = _format_workspace_context(p)
        self.assertEqual(out.count("- dup"), 3)


class TestPromptInjection(unittest.TestCase):
    def test_empty_prompt_has_no_workspace_section(self):
        planner = LLMPlanner()
        prompt = planner._build_prompt("hello", PromptWorkspaceContext())
        self.assertNotIn("Workspace Context", prompt)

    def test_absent_prompt_workspace_is_byte_identical(self):
        planner = LLMPlanner()
        # No workspace arg == empty workspace == no injection.
        self.assertEqual(
            planner._build_prompt("hello"),
            planner._build_prompt("hello", PromptWorkspaceContext()),
        )

    def test_populated_prompt_includes_section(self):
        planner = LLMPlanner()
        p = PromptWorkspaceContext(decisions=["Keep it frozen"])
        prompt = planner._build_prompt("hello", p)
        self.assertIn("Workspace Context", prompt)
        self.assertIn("- Keep it frozen", prompt)
        self.assertIn("User request:\nhello", prompt)

    def test_reads_prompt_workspace_from_context(self):
        # Build a full BrainContext carrying prompt_workspace, confirm planner
        # consumes it via _build_prompt path (inert gateway => plan None, but
        # prompt built from context.prompt_workspace).
        recall = WorkspaceRecallContext(
            decisions=WorkspaceRetrievalResult(
                query="q",
                hits=[RetrievalHit(record_type="decision", record_id="d1",
                                   record=Decision(id="d1", title="Titled"))],
            )
        )
        ctx = BrainContext(
            request=BrainRequest(text="q"),
            prompt_workspace=PromptWorkspaceContext.from_recall(recall),
        )
        planner = LLMPlanner()
        prompt = planner._build_prompt(ctx.request.text, ctx.prompt_workspace)
        self.assertIn("- Titled", prompt)


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

    def test_planner_no_workspace_imports(self):
        modules = self._imports("brain/planning/llm_planner.py")
        for banned in [
            "brain.workspace.memory", "brain.workspace.retriever",
            "brain.workspace.manager", "brain.workspace.store",
            "brain.workspace.sync", "brain.workspace.recall",
            "brain.workspace.models",
        ]:
            self.assertNotIn(banned, modules, f"planner must not import {banned}")

    def test_planner_no_snapshot_access(self):
        src = (backend_dir / "brain/planning/llm_planner.py").read_text(encoding="utf-8")
        self.assertNotIn(".snapshot(", src)
        self.assertNotIn(".recall(", src)
        self.assertNotIn(".retrieve(", src)

    def test_no_cycle_workspace_never_imports_core(self):
        for rel in ["brain/workspace/models.py", "brain/workspace/recall.py"]:
            for m in self._imports(rel):
                self.assertFalse(m.startswith("brain.core"), f"{rel} imports {m}")


if __name__ == "__main__":
    unittest.main()
