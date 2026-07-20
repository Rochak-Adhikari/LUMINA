"""
tests/test_phase_7_step9.py — Milestone 7.9 (Lifecycle)

Pipeline stage 08 — append-only lifecycle event log. LifecycleManager:
(RegistryEntry, transition) -> LifecycleEvent (appended when legal).

Verifies:
  - gate: unregistered entry -> skipped, not appended
  - legal transitions: registered->active, active->inactive, inactive->active,
    active->archived, active->superseded
  - illegal transition -> skipped (invalid_transition), not appended
  - append-only history; current_state() reflects latest; default "registered"
  - events() returns a copy
  - LifecycleEvent frozen, deterministic, inputs unchanged
  - full 8-stage chain
  - dormant DI, import allowlist, AST boundary checks
"""

import ast
import tempfile
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.evolution.models import EvolutionRecommendation, EvolutionRecommendationSet
from brain.skill_creator.models import RegistryEntry, LifecycleEvent
from brain.skill_creator.blueprint_builder import BlueprintBuilder
from brain.skill_creator.blueprint_verifier import BlueprintVerifier
from brain.skill_creator.blueprint_generator import BlueprintGenerator
from brain.skill_creator.blueprint_tester import BlueprintTester
from brain.skill_creator.blueprint_approver import BlueprintApprover
from brain.skill_creator.blueprint_installer import BlueprintInstaller
from brain.skill_creator.blueprint_registry import BlueprintRegistry
from brain.skill_creator.lifecycle_manager import LifecycleManager
from brain.skill_creator.interfaces import ILifecycleManager


def _entry(key="workspace.memory.notes.v1", status="registered"):
    return RegistryEntry(
        blueprint_id="bp:x", recommendation_id="r1",
        semantic_fingerprint=key, skill_family="workspace.memory",
        package_name="pkg", registry_key=key,
        installed_location="/skills/x", registration_status=status,
    )


class TestGate(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(LifecycleManager(), ILifecycleManager)

    def test_unregistered_skipped(self):
        m = LifecycleManager()
        e = m.transition(_entry(status="skipped"), "activate")
        self.assertEqual(e.status, "skipped")
        self.assertEqual(e.skipped_reason, "not_registered")
        self.assertEqual(m.events(), [])


class TestTransitions(unittest.TestCase):
    def setUp(self):
        self.m = LifecycleManager()
        self.e = _entry()

    def test_registered_to_active(self):
        ev = self.m.transition(self.e, "activate")
        self.assertEqual(ev.status, "transitioned")
        self.assertEqual((ev.previous_state, ev.new_state), ("registered", "active"))

    def test_active_to_inactive(self):
        self.m.transition(self.e, "activate")
        ev = self.m.transition(self.e, "deactivate")
        self.assertEqual((ev.previous_state, ev.new_state), ("active", "inactive"))

    def test_inactive_to_active(self):
        self.m.transition(self.e, "activate")
        self.m.transition(self.e, "deactivate")
        ev = self.m.transition(self.e, "activate")
        self.assertEqual((ev.previous_state, ev.new_state), ("inactive", "active"))

    def test_archive(self):
        self.m.transition(self.e, "activate")
        ev = self.m.transition(self.e, "archive")
        self.assertEqual(ev.new_state, "archived")

    def test_supersede(self):
        self.m.transition(self.e, "activate")
        ev = self.m.transition(self.e, "supersede")
        self.assertEqual(ev.new_state, "superseded")

    def test_invalid_transition_skipped(self):
        # deactivate from 'registered' is illegal
        ev = self.m.transition(self.e, "deactivate")
        self.assertEqual(ev.status, "skipped")
        self.assertEqual(ev.skipped_reason, "invalid_transition")
        self.assertEqual(self.m.events(), [])

    def test_unknown_transition_skipped(self):
        ev = self.m.transition(self.e, "explode")
        self.assertEqual(ev.skipped_reason, "invalid_transition")


class TestStateAndHistory(unittest.TestCase):
    def test_default_state_registered(self):
        self.assertEqual(LifecycleManager().current_state("k"), "registered")

    def test_current_state_tracks_latest(self):
        m = LifecycleManager()
        e = _entry()
        m.transition(e, "activate")
        m.transition(e, "deactivate")
        self.assertEqual(m.current_state(e.registry_key), "inactive")

    def test_append_only_history(self):
        m = LifecycleManager()
        e = _entry()
        m.transition(e, "activate")
        m.transition(e, "deactivate")
        m.transition(e, "activate")
        self.assertEqual([ev.new_state for ev in m.events()], ["active", "inactive", "active"])

    def test_events_is_copy(self):
        m = LifecycleManager()
        m.transition(_entry(), "activate")
        m.events().append("junk")
        self.assertEqual(len(m.events()), 1)


class TestImmutabilityDeterminism(unittest.TestCase):
    def test_event_frozen(self):
        ev = LifecycleManager().transition(_entry(), "activate")
        with self.assertRaises(Exception):
            ev.new_state = "x"

    def test_deterministic(self):
        e = _entry()
        ev1 = LifecycleManager().transition(e, "activate")
        ev2 = LifecycleManager().transition(e, "activate")
        self.assertEqual(ev1.model_dump(), ev2.model_dump())

    def test_inputs_unchanged(self):
        e = _entry()
        before = e.model_dump()
        LifecycleManager().transition(e, "activate")
        self.assertEqual(e.model_dump(), before)


class TestIntegration(unittest.TestCase):
    def test_full_chain(self):
        rec = EvolutionRecommendation(id="r1", kind="merge_memory", target="notes", confidence=0.5)
        s = EvolutionRecommendationSet(recommendations=[rec], recommendation_count=1)
        bp = BlueprintBuilder().create_blueprint(s).blueprints[0]
        v = BlueprintVerifier().verify(bp)
        g = BlueprintGenerator().generate(bp, v)
        t = BlueprintTester().test(bp, g)
        a = BlueprintApprover().review(t, approver="rochak", approve=True)
        with tempfile.TemporaryDirectory() as tmp:
            i = BlueprintInstaller().install(a, g, tmp)
            reg = BlueprintRegistry()
            entry = reg.register(i, bp)
            m = LifecycleManager()
            ev = m.transition(entry, "activate")
            self.assertEqual(ev.status, "transitioned")
            self.assertEqual(m.current_state(entry.registry_key), "active")


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

    def test_allowed_imports_only(self):
        allowed = (
            "brain.skill_creator.models",
            "brain.skill_creator.interfaces",
            "typing", "__future__",
        )
        for m in self._imports("brain/skill_creator/lifecycle_manager.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_forbidden_tokens(self):
        modules = self._imports("brain/skill_creator/lifecycle_manager.py")
        for banned in ["datetime", "uuid", "random", "os", "subprocess", "pathlib", "importlib"]:
            self.assertNotIn(banned, modules, f"forbidden import {banned}")
        src = (backend_dir / "brain/skill_creator/lifecycle_manager.py").read_text(encoding="utf-8")
        for banned in ["open(", "exec(", "eval(", "compile(", "__import__", ".now("]:
            self.assertNotIn(banned, src, f"forbidden {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(ILifecycleManager))
        self.assertEqual(c.resolve(ILifecycleManager).events(), [])


if __name__ == "__main__":
    unittest.main()
