"""
tests/test_phase_6_step4.py — Milestone 6.4 Verification (Memory Consolidation)

Verifies the read-only consolidation-proposal layer:

  - ConsolidationProposal / ConsolidationProposalSet: frozen, primitive fields
  - MemoryConsolidator: read-only over records; proposes duplicate consolidations
  - never writes memory; input records unchanged
  - deterministic, stable ordering, stable ids
  - no WorkspaceMemory / memory-engine / store / Reflection / runtime imports
  - dormant DI registration; no cycle

Stdlib unittest; no heavy deps.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import (
    ConsolidationProposal,
    ConsolidationProposalSet,
)
from brain.evolution.consolidator import MemoryConsolidator
from brain.evolution.interfaces import IMemoryConsolidator


class _Rec:
    """Duck-typed memory record: id + title/body."""
    def __init__(self, rid, title="", body=""):
        self.id = rid
        self.title = title
        self.body = body


class TestModels(unittest.TestCase):
    def test_proposal_frozen(self):
        p = ConsolidationProposal(id="x")
        with self.assertRaises(Exception):
            p.kind = "other"

    def test_set_frozen(self):
        s = ConsolidationProposalSet()
        with self.assertRaises(Exception):
            s.proposal_count = 5

    def test_defaults(self):
        s = ConsolidationProposalSet()
        self.assertEqual(s.records_scanned, 0)
        self.assertEqual(s.proposals, [])
        self.assertEqual(s.proposal_count, 0)


class TestConsolidator(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(MemoryConsolidator(), IMemoryConsolidator)

    def test_empty(self):
        s = MemoryConsolidator().propose([])
        self.assertEqual(s.records_scanned, 0)
        self.assertEqual(s.proposals, [])

    def test_no_duplicates_no_proposals(self):
        recs = [_Rec("a", "A"), _Rec("b", "B"), _Rec("c", "C")]
        s = MemoryConsolidator().propose(recs)
        self.assertEqual(s.records_scanned, 3)
        self.assertEqual(s.proposal_count, 0)

    def test_detects_duplicates(self):
        recs = [_Rec("a", "Same", "x"), _Rec("b", "Same", "x"), _Rec("c", "Diff")]
        s = MemoryConsolidator().propose(recs)
        self.assertEqual(s.proposal_count, 1)
        p = s.proposals[0]
        self.assertEqual(p.kind, "duplicate")
        self.assertEqual(p.record_ids, ["a", "b"])

    def test_dict_records_supported(self):
        recs = [{"id": "a", "title": "T"}, {"id": "b", "title": "T"}]
        s = MemoryConsolidator().propose(recs)
        self.assertEqual(s.proposals[0].record_ids, ["a", "b"])

    def test_deterministic_and_stable_ids(self):
        recs = [_Rec("a", "T"), _Rec("b", "T")]
        c = MemoryConsolidator()
        s1 = c.propose(recs)
        s2 = c.propose(recs)
        self.assertEqual(s1.model_dump(), s2.model_dump())
        self.assertEqual(s1.proposals[0].id, s2.proposals[0].id)

    def test_stable_ordering_first_seen(self):
        recs = [_Rec("a", "X"), _Rec("b", "Y"), _Rec("c", "X"), _Rec("d", "Y")]
        s = MemoryConsolidator().propose(recs)
        # "X" group seen before "Y" group
        self.assertEqual([p.record_ids for p in s.proposals], [["a", "c"], ["b", "d"]])

    def test_records_unchanged(self):
        recs = [_Rec("a", "T"), _Rec("b", "T")]
        before = [(r.id, r.title, r.body) for r in recs]
        MemoryConsolidator().propose(recs)
        after = [(r.id, r.title, r.body) for r in recs]
        self.assertEqual(before, after)


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

    def test_no_memory_or_runtime_imports(self):
        modules = self._imports("brain/evolution/consolidator.py")
        for banned in [
            "brain.workspace.memory", "brain.workspace.manager",
            "brain.workspace.store", "brain.memory",
            "brain.reflection.engine", "brain.core.brain_core",
            "brain.evolution.store", "core.bootstrap",
            "core.runtime_facade", "server",
        ]:
            self.assertNotIn(banned, modules, f"consolidator must not import {banned}")

    def test_no_write_calls(self):
        src = (backend_dir / "brain/evolution/consolidator.py").read_text(encoding="utf-8")
        for banned in [".save(", ".add_", ".append(self", ".switch(", ".clear(", ".write("]:
            self.assertNotIn(banned, src, f"consolidator must not write: {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IMemoryConsolidator))
        # Dormant: proposing over nothing yields empty set; no runtime consumer.
        self.assertEqual(c.resolve(IMemoryConsolidator).propose([]).proposal_count, 0)


if __name__ == "__main__":
    unittest.main()
