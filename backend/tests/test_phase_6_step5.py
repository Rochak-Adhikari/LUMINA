"""
tests/test_phase_6_step5.py — Milestone 6.5 Verification (Self Evolution)

Verifies the evolution-recommendation layer:

  - EvolutionRecommendation / EvolutionRecommendationSet: frozen, primitive
  - RecommendationEngine consumes ONLY PerformanceAnalysis + ConsolidationProposalSet
  - deterministic ids + ordering; byte-identical repeated execution
  - inputs unchanged; no runtime/memory/planner/prompt mutation
  - no Reflection / EvolutionStore / Workspace imports
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
    StrategyStat,
    StrategyAnalysis,
    PerformanceAnalysis,
    ConsolidationProposal,
    ConsolidationProposalSet,
    EvolutionRecommendation,
    EvolutionRecommendationSet,
)
from brain.evolution.recommender import RecommendationEngine
from brain.evolution.interfaces import IRecommendationEngine


def _perf(**kw):
    base = dict(
        strategies_measured=1, reliability=1.0, failure_ratio=0.0,
        consistency=1.0, stability=1.0, efficiency=None,
        best_strategy="seq", worst_strategy="seq",
    )
    base.update(kw)
    return PerformanceAnalysis(**base)


def _consol(*proposals):
    return ConsolidationProposalSet(
        records_scanned=0, proposals=list(proposals), proposal_count=len(proposals)
    )


class TestModels(unittest.TestCase):
    def test_recommendation_frozen(self):
        r = EvolutionRecommendation(id="x", kind="observe_more")
        with self.assertRaises(Exception):
            r.kind = "other"

    def test_set_frozen(self):
        s = EvolutionRecommendationSet()
        with self.assertRaises(Exception):
            s.recommendation_count = 3

    def test_defaults(self):
        s = EvolutionRecommendationSet()
        self.assertEqual(s.recommendations, [])
        self.assertEqual(s.recommendation_count, 0)


class TestEngine(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(RecommendationEngine(), IRecommendationEngine)

    def test_observe_more_when_no_strategies(self):
        s = RecommendationEngine().recommend(_perf(strategies_measured=0), _consol())
        kinds = [r.kind for r in s.recommendations]
        self.assertIn("observe_more", kinds)

    def test_keep_strategy_when_healthy(self):
        s = RecommendationEngine().recommend(_perf(), _consol())
        self.assertEqual([r.kind for r in s.recommendations], ["keep_strategy"])
        self.assertEqual(s.recommendations[0].target, "seq")

    def test_improve_strategy_when_unreliable(self):
        s = RecommendationEngine().recommend(
            _perf(reliability=0.4, worst_strategy="dag"), _consol()
        )
        r = next(x for x in s.recommendations if x.kind == "improve_strategy")
        self.assertEqual(r.target, "dag")
        self.assertEqual(r.priority, "high")

    def test_review_when_unstable(self):
        s = RecommendationEngine().recommend(_perf(stability=0.2), _consol())
        self.assertTrue(any(r.kind == "review_required" for r in s.recommendations))

    def test_merge_memory_from_consolidation(self):
        prop = ConsolidationProposal(id="consolidate:duplicate:sig", kind="duplicate",
                                     reason="dupes", record_ids=["a", "b"])
        s = RecommendationEngine().recommend(_perf(), _consol(prop))
        merge = next(x for x in s.recommendations if x.kind == "merge_memory")
        self.assertEqual(merge.related_ids, ["a", "b"])
        self.assertEqual(merge.source, "consolidation")

    def test_deterministic_ids(self):
        s = RecommendationEngine().recommend(_perf(reliability=0.4, worst_strategy="dag"), _consol())
        self.assertEqual(s.recommendations[0].id, "rec:improve_strategy:dag")

    def test_ordering_performance_then_consolidation(self):
        prop = ConsolidationProposal(id="p", record_ids=["a", "b"])
        s = RecommendationEngine().recommend(_perf(), _consol(prop))
        sources = [r.source for r in s.recommendations]
        self.assertEqual(sources, ["performance", "consolidation"])

    def test_byte_identical_repeat(self):
        e = RecommendationEngine()
        p = _perf(reliability=0.3, stability=0.1, worst_strategy="x")
        c = _consol(ConsolidationProposal(id="p", record_ids=["a", "b"]))
        self.assertEqual(e.recommend(p, c).model_dump(), e.recommend(p, c).model_dump())

    def test_inputs_unchanged(self):
        p = _perf(reliability=0.4, worst_strategy="dag")
        c = _consol(ConsolidationProposal(id="p", record_ids=["a"]))
        pb, cb = p.model_dump(), c.model_dump()
        RecommendationEngine().recommend(p, c)
        self.assertEqual(p.model_dump(), pb)
        self.assertEqual(c.model_dump(), cb)

    def test_confidence_bounded(self):
        s = RecommendationEngine().recommend(_perf(reliability=0.0, worst_strategy="x"), _consol())
        for r in s.recommendations:
            self.assertGreaterEqual(r.confidence, 0.0)
            self.assertLessEqual(r.confidence, 1.0)


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

    def test_consumes_only_analysis_layers(self):
        modules = self._imports("brain/evolution/recommender.py")
        for banned in [
            "brain.reflection.engine", "brain.evolution.store",
            "brain.evolution.observer", "brain.evolution.evaluator",
            "brain.workspace.memory", "brain.workspace.manager",
            "brain.core.brain_core", "brain.planning.rule_planner",
            "brain.planning.llm_planner", "core.bootstrap",
            "core.runtime_facade", "server",
        ]:
            self.assertNotIn(banned, modules, f"recommender must not import {banned}")

    def test_no_write_or_mutation_calls(self):
        src = (backend_dir / "brain/evolution/recommender.py").read_text(encoding="utf-8")
        for banned in [".save(", ".switch(", ".add_", ".write(", ".append(store", ".clear("]:
            self.assertNotIn(banned, src, f"recommender must not mutate: {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IRecommendationEngine))
        # Dormant: empty inputs => observe_more only; no runtime consumer.
        out = c.resolve(IRecommendationEngine).recommend(
            _perf(strategies_measured=0), _consol()
        )
        self.assertTrue(all(isinstance(r, EvolutionRecommendation) for r in out.recommendations))


if __name__ == "__main__":
    unittest.main()
