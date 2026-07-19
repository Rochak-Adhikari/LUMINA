"""
tests/test_phase_6_step3.py — Milestone 6.3 Verification (Performance Analysis)

Verifies the deterministic measurement layer:

  - PerformanceAnalysis: frozen, primitive fields
  - PerformanceAnalyzer: consumes ONLY StrategyAnalysis; deterministic metrics
    (reliability, failure_ratio, consistency, stability, efficiency, best/worst)
  - input StrategyAnalysis unchanged (frozen, not mutated)
  - no Reflection / EvolutionObservation / EvolutionStore dependency
  - dormant DI registration
  - no import cycle

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
)
from brain.evolution.analyzer import PerformanceAnalyzer
from brain.evolution.interfaces import IPerformanceAnalyzer


def _analysis(*stats, successes=0, failures=0):
    total = successes + failures
    return StrategyAnalysis(
        observations_analyzed=total,
        per_strategy=list(stats),
        total_successes=successes,
        total_failures=failures,
        overall_success_rate=(successes / total) if total else 0.0,
    )


def _stat(name, total, succ, avg_latency=None):
    return StrategyStat(
        strategy=name,
        total=total,
        successes=succ,
        failures=total - succ,
        success_rate=(succ / total) if total else 0.0,
        average_latency=avg_latency,
    )


class TestModel(unittest.TestCase):
    def test_frozen(self):
        p = PerformanceAnalysis()
        with self.assertRaises(Exception):
            p.reliability = 1.0

    def test_defaults(self):
        p = PerformanceAnalysis()
        self.assertEqual(p.strategies_measured, 0)
        self.assertIsNone(p.efficiency)
        self.assertEqual((p.best_strategy, p.worst_strategy), ("", ""))


class TestAnalyzer(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(PerformanceAnalyzer(), IPerformanceAnalyzer)

    def test_empty(self):
        p = PerformanceAnalyzer().analyze(_analysis())
        self.assertEqual(p.strategies_measured, 0)
        self.assertEqual(p.reliability, 0.0)
        self.assertEqual(p.failure_ratio, 0.0)
        self.assertIsNone(p.efficiency)

    def test_metrics(self):
        a = _analysis(
            _stat("seq", 4, 2, 10.0),   # rate 0.5
            _stat("dag", 2, 2, 30.0),   # rate 1.0
            successes=4, failures=2,
        )
        p = PerformanceAnalyzer().analyze(a)
        self.assertEqual(p.strategies_measured, 2)
        self.assertAlmostEqual(p.reliability, 4 / 6)
        self.assertAlmostEqual(p.failure_ratio, 2 / 6)
        self.assertAlmostEqual(p.consistency, 1.0 - (1.0 - 0.5))  # 0.5
        self.assertAlmostEqual(p.stability, 0.5)                  # weakest rate
        self.assertAlmostEqual(p.efficiency, 20.0)               # (10+30)/2
        self.assertEqual(p.best_strategy, "dag")
        self.assertEqual(p.worst_strategy, "seq")

    def test_efficiency_none_when_no_latency(self):
        p = PerformanceAnalyzer().analyze(_analysis(_stat("seq", 1, 1), successes=1))
        self.assertIsNone(p.efficiency)

    def test_consistency_full_when_equal(self):
        a = _analysis(_stat("a", 2, 1), _stat("b", 2, 1), successes=2, failures=2)
        p = PerformanceAnalyzer().analyze(a)
        self.assertEqual(p.consistency, 1.0)

    def test_deterministic_repeat(self):
        a = _analysis(_stat("seq", 3, 2, 5.0), _stat("dag", 1, 0, 9.0), successes=2, failures=2)
        an = PerformanceAnalyzer()
        self.assertEqual(an.analyze(a).model_dump(), an.analyze(a).model_dump())

    def test_tie_break_first_seen(self):
        # equal success rates → best/worst stay first-seen deterministic
        a = _analysis(_stat("x", 2, 1), _stat("y", 2, 1), successes=2, failures=2)
        p = PerformanceAnalyzer().analyze(a)
        self.assertEqual(p.best_strategy, "x")
        self.assertEqual(p.worst_strategy, "x")

    def test_input_unchanged(self):
        a = _analysis(_stat("seq", 2, 1, 4.0), successes=1, failures=1)
        before = a.model_dump()
        PerformanceAnalyzer().analyze(a)
        self.assertEqual(a.model_dump(), before)


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

    def test_analyzer_consumes_strategy_analysis_only(self):
        modules = self._imports("brain/evolution/analyzer.py")
        for banned in [
            "brain.evolution.store", "brain.evolution.observer",
            "brain.reflection.engine", "brain.core.models",
            "brain.core.brain_core", "brain.planning.rule_planner",
            "brain.workspace.memory", "core.bootstrap",
            "core.runtime_facade", "server",
        ]:
            self.assertNotIn(banned, modules, f"analyzer must not import {banned}")

    def test_analyzer_no_store_reference(self):
        # analyze takes StrategyAnalysis directly; no store/observation access.
        # (Authoritative check is the AST import ban above; here we only assert
        # no store-list call — the class names appear in explanatory docstrings.)
        src = (backend_dir / "brain/evolution/analyzer.py").read_text(encoding="utf-8")
        self.assertNotIn(".list(", src)

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IPerformanceAnalyzer))


if __name__ == "__main__":
    unittest.main()
