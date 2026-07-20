"""
tests/test_phase_5_7_step3.py — Phase 5.7.3: ReflectionEngine DI (dormant)

Dormant DI registration + facade accessor. No BrainCore wiring, no consumer.
"""

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
from core.runtime_facade import RuntimeFacade
from brain.reflection.engine import ReflectionEngine
from brain.reflection.interfaces import IReflectionEngine


class TestReflectionDI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()
        cls.facade = RuntimeFacade(cls.container)

    def test_registered_under_concrete(self):
        e = self.container.resolve(ReflectionEngine)
        self.assertIsInstance(e, ReflectionEngine)

    def test_registered_under_interface(self):
        e = self.container.resolve(IReflectionEngine)
        self.assertIsInstance(e, ReflectionEngine)

    def test_singleton_same_instance(self):
        self.assertIs(self.container.resolve(ReflectionEngine),
                      self.container.resolve(ReflectionEngine))
        self.assertIs(self.container.resolve(IReflectionEngine),
                      self.container.resolve(ReflectionEngine))

    def test_facade_exposes_engine(self):
        self.assertIs(self.facade.reflection_engine,
                      self.container.resolve(ReflectionEngine))

    def test_metadata_registry_unchanged(self):
        from core.metadata import ServiceMetadataRegistry
        self.assertEqual(len(self.container.resolve(ServiceMetadataRegistry)), 11)

    def test_skill_registry_unchanged(self):
        from brain.skills.registry import SkillRegistry
        self.assertEqual(len(self.container.resolve(SkillRegistry)), 12)


class TestDormancy(unittest.TestCase):
    def test_brain_core_does_not_reference_reflection_engine(self):
        # BrainCore untouched: no ReflectionEngine consumer wired. (The word
        # "reflection" may appear in pre-existing docstrings / the BrainResult
        # slot; what must be absent is a ReflectionEngine import/use.)
        src = (backend_dir / "brain" / "core" / "brain_core.py").read_text(encoding="utf-8")
        self.assertNotIn("ReflectionEngine", src)
        self.assertNotIn("brain.reflection", src)

    def test_server_untouched(self):
        src = (backend_dir / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("ReflectionEngine", src)
        self.assertNotIn("reflection_engine", src)

    def test_context_builder_untouched(self):
        src = (backend_dir / "brain" / "core" / "context_builder.py").read_text(encoding="utf-8")
        self.assertNotIn("ReflectionEngine", src)
        self.assertNotIn("brain.reflection", src)


if __name__ == '__main__':
    unittest.main()
