"""
tests/test_phase_6_step2.py — Milestone 6.2 Verification (Strategy Improvement)

Verifies the deterministic analysis layer:

  - StrategyStat / StrategyAnalysis: frozen, primitive fields
  - StrategyEvaluator: reads ONLY EvolutionStore observations (never Reflection);
    deterministic per-strategy aggregation (success rate, avg latency, totals)
  - store unchanged after evaluate (append-only observations preserved)
  - deterministic ordering (first-seen strategy order)
  - dormant DI registration; no runtime consumer
  - no import cycle; evaluator imports no Reflection/runtime/cognitive modules

Stdlib unittest; no heavy deps.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import (
    EvolutionObservation,
    StrategyStat,
    StrategyAnalysis,
)
from brain.evolution.store import EvolutionStore
from brain.evolution.evaluator import StrategyEvaluator
from brain.evolution.interfaces import IStrategyEvaluator


def _obs(i, strategy, success, latency=None):
    return EvolutionObservation(
        id=f"o{i}", strategy_used=strategy, success=success, latency=latency
    )


def _store(*observations):
    s = EvolutionStore()
    for o in observations:
        s.append(o)
    return s


class TestModels(unittest.TestCase):
    def test_stat_frozen(self):
        st = StrategyStat(strategy="seq")
        with self.assertRaises(Exception):
            st.total = 5

    def test_analysis_frozen(self):
        a = StrategyAnalysis()
        with self.assertRaises(Exception):
            a.observations_analyzed = 3

    def test_analysis_defaults(self):
        a = StrategyAnalysis()
        self.assertEqual(a.observations_analyzed, 0)
        self.assertEqual(a.per_strategy, [])
        self.assertEqual(a.overall_success_rate, 0.0)


class TestEvaluator(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(StrategyEvaluator(EvolutionStore()), IStrategyEvaluator)

    def test_empty_store(self):
        a = StrategyEvaluator(EvolutionStore()).evaluate()
        self.assertEqual(a.observations_analyzed, 0)
        self.assertEqual(a.per_strategy, [])
        self.assertEqual(a.overall_success_rate, 0.0)

    def test_per_strategy_aggregation(self):
        s = _store(
            _obs(1, "seq", True, 10.0),
            _obs(2, "seq", False, 20.0),
            _obs(3, "dag", True, 30.0),
        )
        a = StrategyEvaluator(s).evaluate()
        self.assertEqual(a.observations_analyzed, 3)
        seq = next(x for x in a.per_strategy if x.strategy == "seq")
        dag = next(x for x in a.per_strategy if x.strategy == "dag")
        self.assertEqual((seq.total, seq.successes, seq.failures), (2, 1, 1))
        self.assertEqual(seq.success_rate, 0.5)
        self.assertEqual(seq.average_latency, 15.0)
        self.assertEqual((dag.total, dag.successes), (1, 1))
        self.assertEqual(dag.average_latency, 30.0)

    def test_overall_totals(self):
        s = _store(_obs(1, "seq", True), _obs(2, "seq", False), _obs(3, "dag", True))
        a = StrategyEvaluator(s).evaluate()
        self.assertEqual(a.total_successes, 2)
        self.assertEqual(a.total_failures, 1)
        self.assertAlmostEqual(a.overall_success_rate, 2 / 3)

    def test_average_latency_none_when_absent(self):
        s = _store(_obs(1, "seq", True))  # no latency
        a = StrategyEvaluator(s).evaluate()
        self.assertIsNone(a.per_strategy[0].average_latency)

    def test_deterministic_first_seen_order(self):
        s = _store(_obs(1, "dag", True), _obs(2, "seq", True), _obs(3, "dag", False))
        a = StrategyEvaluator(s).evaluate()
        self.assertEqual([x.strategy for x in a.per_strategy], ["dag", "seq"])

    def test_deterministic_repeat(self):
        s = _store(_obs(1, "seq", True), _obs(2, "dag", False))
        e = StrategyEvaluator(s)
        self.assertEqual(e.evaluate().model_dump(), e.evaluate().model_dump())

    def test_store_unchanged_after_evaluate(self):
        s = _store(_obs(1, "seq", True), _obs(2, "dag", False))
        before = [o.model_dump() for o in s.list()]
        before_count = s.count()
        StrategyEvaluator(s).evaluate()
        self.assertEqual(s.count(), before_count)
        self.assertEqual([o.model_dump() for o in s.list()], before)


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

    def test_evaluator_no_reflection_or_runtime_imports(self):
        modules = self._imports("brain/evolution/evaluator.py")
        for banned in [
            "brain.reflection.engine", "brain.reflection.interfaces",
            "brain.core.models", "brain.core.brain_core",
            "brain.planning.rule_planner", "brain.planning.llm_planner",
            "brain.workspace.memory", "core.bootstrap",
            "core.runtime_facade", "server",
        ]:
            self.assertNotIn(banned, modules, f"evaluator must not import {banned}")

    def test_evaluator_reads_store_only(self):
        # Collaborator exposing ONLY list() (store surface) — evaluate must work,
        # proving no Reflection/other access.
        class _MinimalStore:
            def list(self):
                return [_obs(1, "seq", True)]
        a = StrategyEvaluator(_MinimalStore()).evaluate()
        self.assertEqual(a.observations_analyzed, 1)

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IStrategyEvaluator))
        # Dormant: nothing observed => empty analysis at boot.
        self.assertEqual(c.resolve(IStrategyEvaluator).evaluate().observations_analyzed, 0)


if __name__ == "__main__":
    unittest.main()
