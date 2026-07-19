"""
tests/test_phase_5_6_step5.py — Phase 5.6.5: ContextBuilder workspace enrichment

Read-only Brain integration: ContextBuilder populates BrainContext.workspace_ctx
from the current workspace snapshot when a WorkspaceMemoryManager is injected;
otherwise workspace_ctx stays empty (unchanged). No writes, no mutation.
"""

import asyncio
import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper
from brain.core.context_builder import ContextBuilder
from brain.core.models import BrainRequest, BrainResult
from brain.core.interfaces import IBrainCore
from brain.workspace.manager import WorkspaceMemoryManager
from brain.workspace.memory import WorkspaceMemory
from brain.workspace.models import ProjectInfo, Decision, Note


class _StubManager:
    """Minimal manager exposing current().snapshot()."""
    def __init__(self, memory):
        self._m = memory
        self.writes = 0
    def current(self):
        return self._m


class TestEnrichment(unittest.TestCase):
    def test_manager_absent_workspace_ctx_empty(self):
        cb = ContextBuilder(brain_state=None)  # no manager
        ctx = cb.build(BrainRequest(text="x"))
        self.assertEqual(ctx.workspace_ctx, {})

    def test_manager_present_populates(self):
        m = WorkspaceMemory("Lumina")
        m.set_project_info(ProjectInfo(name="Lumina", description="asst"))
        m.add_decision(Decision(title="use json", id="d1"))
        m.add_note(Note(title="n", id="n1"))
        cb = ContextBuilder(brain_state=None,
                            workspace_memory_manager=_StubManager(m))
        ctx = cb.build(BrainRequest(text="x"))
        wc = ctx.workspace_ctx
        self.assertEqual(wc["workspace"], "Lumina")
        self.assertEqual(wc["info"]["name"], "Lumina")
        self.assertEqual(wc["decisions"][0]["id"], "d1")
        self.assertEqual(wc["notes"][0]["id"], "n1")

    def test_empty_workspace_stays_empty_records(self):
        cb = ContextBuilder(brain_state=None,
                            workspace_memory_manager=_StubManager(WorkspaceMemory("E")))
        wc = cb.build(BrainRequest(text="x")).workspace_ctx
        self.assertEqual(wc["workspace"], "E")
        self.assertEqual(wc["decisions"], [])
        self.assertEqual(wc["notes"], [])
        self.assertEqual(wc["tasks"], [])
        self.assertIsNone(wc["info"])

    def test_snapshot_is_a_copy_not_mutation(self):
        m = WorkspaceMemory("w")
        m.add_note(Note(title="n1"))
        cb = ContextBuilder(brain_state=None, workspace_memory_manager=_StubManager(m))
        ctx = cb.build(BrainRequest(text="x"))
        # Later mutation of source doesn't retro-change the built context.
        m.add_note(Note(title="n2"))
        self.assertEqual(len(ctx.workspace_ctx["notes"]), 1)

    def test_no_writes_occur(self):
        # Manager stub has no save/write; enrichment must only read current().
        m = WorkspaceMemory("w")
        before = m.snapshot().model_dump()
        cb = ContextBuilder(brain_state=None, workspace_memory_manager=_StubManager(m))
        cb.build(BrainRequest(text="x"))
        self.assertEqual(m.snapshot().model_dump(), before)  # unchanged

    def test_deterministic(self):
        m = WorkspaceMemory("w"); m.add_decision(Decision(title="d", id="fixed"))
        cb = ContextBuilder(brain_state=None, workspace_memory_manager=_StubManager(m))
        a = cb.build(BrainRequest(text="x")).workspace_ctx
        b = cb.build(BrainRequest(text="x")).workspace_ctx
        self.assertEqual(a, b)

    def test_failure_safe(self):
        class _Bad:
            def current(self): raise RuntimeError("boom")
        cb = ContextBuilder(brain_state=None, workspace_memory_manager=_Bad())
        self.assertEqual(cb.build(BrainRequest(text="x")).workspace_ctx, {})


class TestBootstrapIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()

    def test_context_builder_has_manager_injected(self):
        from brain.core.interfaces import IContextBuilder
        cb = self.container.resolve(IContextBuilder)
        self.assertIsNotNone(cb._workspace_memory_manager)
        self.assertIsInstance(cb._workspace_memory_manager, WorkspaceMemoryManager)

    def test_brain_core_still_pass_through(self):
        # workspace_ctx now populated (empty workspace) but BrainCore handled
        # semantics unchanged: unbound executor → declines.
        core = self.container.resolve(IBrainCore)
        result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
        self.assertIsInstance(result, BrainResult)
        self.assertFalse(result.handled)

    def test_workspace_ctx_present_but_empty_default(self):
        from brain.core.interfaces import IContextBuilder
        cb = self.container.resolve(IContextBuilder)
        ctx = cb.build(BrainRequest(text="x"))
        # Manager starts empty → snapshot of an empty WorkspaceMemory.
        self.assertIn("workspace", ctx.workspace_ctx)
        self.assertEqual(ctx.workspace_ctx["decisions"], [])


class TestNoForbiddenImports(unittest.TestCase):
    def test_context_builder_imports(self):
        import ast
        src = (backend_dir / "brain" / "core" / "context_builder.py").read_text(encoding="utf-8")
        mods = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
            elif isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
        # ContextBuilder must not hard-import planner/skills/server/lumina/
        # ProjectManager. The workspace manager arrives via injection (Any).
        for m in mods:
            self.assertNotIn("planning", m)
            self.assertNotIn("skills", m)
            self.assertNotIn("project_manager", m)
            self.assertNotIn(m.split(".")[0], ("server", "lumina"))


if __name__ == '__main__':
    unittest.main()
