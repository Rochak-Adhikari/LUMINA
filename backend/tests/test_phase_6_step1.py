"""
tests/test_phase_6_step1.py — Milestone 6.1 Verification (Reflection Learning)

Verifies the Evolution observation layer:

  - EvolutionObservation: frozen, primitive fields
  - EvolutionStore: append-only (no update/delete), insertion order, get/count
  - EvolutionObserver: Reflection -> EvolutionObservation -> store; deterministic
    id (no UUID), caller-supplied timestamp, read-only over the reflection
  - DI registration is DORMANT (registered, but no runtime consumer)
  - no import cycle; evolution imports no runtime/cognitive modules
  - boot byte-identical (registration only)

Stdlib unittest; no heavy deps.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.core.models import Reflection
from brain.evolution.models import EvolutionObservation
from brain.evolution.store import EvolutionStore
from brain.evolution.observer import EvolutionObserver
from brain.evolution.interfaces import IEvolutionStore, IEvolutionObserver


def _reflection(request_id="r1", plan_id="p1", success=True, latency=12.0):
    return Reflection(
        request_id=request_id,
        plan_id=plan_id,
        success=success,
        latency_ms=latency,
    )


class TestObservationModel(unittest.TestCase):
    def test_frozen(self):
        o = EvolutionObservation(id="x")
        with self.assertRaises(Exception):
            o.success = True

    def test_defaults(self):
        o = EvolutionObservation(id="x")
        self.assertEqual((o.reflection_id, o.planner_used, o.success), ("", "", False))
        self.assertIsNone(o.timestamp)
        self.assertEqual(o.metadata, {})


class TestStore(unittest.TestCase):
    def test_append_and_count(self):
        s = EvolutionStore()
        s.append(EvolutionObservation(id="a"))
        s.append(EvolutionObservation(id="b"))
        self.assertEqual(s.count(), 2)

    def test_insertion_order(self):
        s = EvolutionStore()
        for i in "abc":
            s.append(EvolutionObservation(id=i))
        self.assertEqual([o.id for o in s.list()], ["a", "b", "c"])

    def test_get(self):
        s = EvolutionStore()
        s.append(EvolutionObservation(id="a", success=True))
        self.assertTrue(s.get("a").success)
        self.assertIsNone(s.get("missing"))

    def test_append_only_first_write_wins(self):
        s = EvolutionStore()
        s.append(EvolutionObservation(id="a", success=True))
        s.append(EvolutionObservation(id="a", success=False))  # ignored
        self.assertEqual(s.count(), 1)
        self.assertTrue(s.get("a").success)

    def test_list_is_copy(self):
        s = EvolutionStore()
        s.append(EvolutionObservation(id="a"))
        s.list().append(EvolutionObservation(id="z"))
        self.assertEqual(s.count(), 1)

    def test_no_mutation_methods(self):
        self.assertFalse(hasattr(EvolutionStore, "update"))
        self.assertFalse(hasattr(EvolutionStore, "delete"))


class TestObserver(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(EvolutionObserver(EvolutionStore()), IEvolutionObserver)

    def test_observe_stores(self):
        s = EvolutionStore()
        obs = EvolutionObserver(s).observe(_reflection())
        self.assertEqual(s.count(), 1)
        self.assertIs(s.get(obs.id), obs)

    def test_fields_copied_from_reflection(self):
        obs = EvolutionObserver(EvolutionStore()).observe(_reflection(success=True, latency=9.0))
        self.assertEqual(obs.reflection_id, "r1")
        self.assertEqual(obs.plan_id, "p1")
        self.assertTrue(obs.success)
        self.assertEqual(obs.latency, 9.0)

    def test_deterministic_id_no_uuid(self):
        a = EvolutionObserver(EvolutionStore()).observe(_reflection())
        b = EvolutionObserver(EvolutionStore()).observe(_reflection())
        self.assertEqual(a.id, b.id)  # same reflection => same id
        self.assertEqual(a.id, "obs:r1:p1")

    def test_timestamp_caller_supplied(self):
        obs = EvolutionObserver(EvolutionStore()).observe(_reflection(), timestamp=1000.0)
        self.assertEqual(obs.timestamp, 1000.0)

    def test_timestamp_none_by_default(self):
        obs = EvolutionObserver(EvolutionStore()).observe(_reflection())
        self.assertIsNone(obs.timestamp)

    def test_planner_strategy_hints(self):
        obs = EvolutionObserver(EvolutionStore()).observe(
            _reflection(), planner_used="RulePlanner", strategy_used="sequential"
        )
        self.assertEqual(obs.planner_used, "RulePlanner")
        self.assertEqual(obs.strategy_used, "sequential")

    def test_read_only_over_reflection(self):
        r = _reflection()
        before = r.model_dump()
        EvolutionObserver(EvolutionStore()).observe(r)
        self.assertEqual(r.model_dump(), before)  # reflection unchanged (frozen)


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

    def test_no_runtime_or_cognitive_imports(self):
        for rel in [
            "brain/evolution/models.py",
            "brain/evolution/interfaces.py",
            "brain/evolution/store.py",
            "brain/evolution/observer.py",
        ]:
            modules = self._imports(rel)
            for banned in [
                "brain.core.brain_core", "brain.core.context_builder",
                "brain.planning.rule_planner", "brain.planning.llm_planner",
                "brain.workspace.memory", "brain.workspace.retriever",
                "brain.reflection.engine", "core.bootstrap",
                "core.runtime_facade", "server",
            ]:
                self.assertNotIn(banned, modules, f"{rel} must not import {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        # Registered...
        self.assertTrue(c.is_registered(IEvolutionStore))
        self.assertTrue(c.is_registered(IEvolutionObserver))
        # ...but dormant: store empty, nothing observed at boot.
        self.assertEqual(c.resolve(IEvolutionStore).count(), 0)


if __name__ == "__main__":
    unittest.main()
