"""
tests/test_phase_5_4.py — Phase 5.4 verification (grows step by step)

Step 0 (this revision): skill catalog truth-alignment.
  - Every BUILTIN_SKILLS provider_ref is a REAL key in the union of the two
    live legacy registries (ToolDispatcherRegistry ∪ ACTION_REGISTRY).
  - Skill ids unique; provider is 'legacy' for all builtins.
  - Bootstrap seeds the rewritten catalog; DI unchanged otherwise.
  - No runtime behavior change (BrainCore still pass-through; server.py
    still has zero Phase 5 references).

Stdlib unittest; heavy deps mocked (established pattern).
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
from brain.core.interfaces import IBrainCore
from brain.core.models import BrainRequest, BrainResult
from brain.skills.registry import SkillRegistry
from brain.skills.builtin import BUILTIN_SKILLS, _TIER1_SKILLS, _TIER2_SKILLS


def _live_registry_keys():
    """Union of both live legacy dispatch registries."""
    from core.registry import ToolDispatcherRegistry
    import core.tool_handlers  # noqa: F401 — populates the registry
    from actions import ACTION_REGISTRY
    tier1 = set(ToolDispatcherRegistry.keys())
    tier2 = set(ACTION_REGISTRY.keys())
    return tier1, tier2


class TestStep0_CatalogTruthAlignment(unittest.TestCase):
    """Every provider_ref must name a real, dispatchable legacy tool."""

    @classmethod
    def setUpClass(cls):
        cls.tier1, cls.tier2 = _live_registry_keys()
        cls.union = cls.tier1 | cls.tier2

    def test_every_provider_ref_is_real(self):
        for spec in BUILTIN_SKILLS:
            self.assertIn(
                spec.provider_ref, self.union,
                f"SkillSpec '{spec.id}' has provider_ref "
                f"'{spec.provider_ref}' which matches NO key in "
                f"ToolDispatcherRegistry or ACTION_REGISTRY",
            )

    def test_tier1_specs_point_at_tool_dispatcher(self):
        for spec in _TIER1_SKILLS:
            self.assertIn(spec.provider_ref, self.tier1,
                          f"'{spec.id}' should be a tier-1 tool")

    def test_tier2_specs_point_at_action_registry(self):
        for spec in _TIER2_SKILLS:
            self.assertIn(spec.provider_ref, self.tier2,
                          f"'{spec.id}' should be a tier-2 action")

    def test_full_tier1_coverage(self):
        """Every ToolDispatcherRegistry tool has a SkillSpec (16/16)."""
        covered = {s.provider_ref for s in _TIER1_SKILLS}
        self.assertEqual(covered, self.tier1,
                         f"Uncovered tier-1 tools: {self.tier1 - covered}")

    def test_ids_unique_and_legacy_provider(self):
        ids = [s.id for s in BUILTIN_SKILLS]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate skill ids")
        for spec in BUILTIN_SKILLS:
            self.assertEqual(spec.provider, "legacy")
            self.assertTrue(spec.id.startswith("legacy."))

    def test_no_memory_skill(self):
        """Blueprint D1: no memory tool exists in either registry, so no
        memory SkillSpec may exist until a real target does."""
        for spec in BUILTIN_SKILLS:
            self.assertNotIn("memory", spec.id)


class TestStep0_BootstrapSeeding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.container = DependencyContainer()
        Bootstrapper(container=cls.container, kasa_agent=None).bootstrap()

    def test_registry_seeded_with_rewritten_catalog(self):
        registry = self.container.resolve(SkillRegistry)
        self.assertEqual(len(registry), len(BUILTIN_SKILLS))
        self.assertIsNotNone(registry.get("legacy.navigate_ui"))
        self.assertIsNone(registry.get("legacy.navigation"),
                          "Old fictional id must be gone")
        self.assertIsNone(registry.get("legacy.memory"),
                          "Old fictional id must be gone")

    def test_runtime_still_unchanged(self):
        """BrainCore remains pass-through; no server wiring in Step 0."""
        core = self.container.resolve(IBrainCore)
        result = asyncio.run(core.handle(BrainRequest(text="open the quests panel")))
        self.assertIsInstance(result, BrainResult)
        self.assertFalse(result.handled)
        source = (backend_dir / "server.py").read_text(encoding='utf-8')
        for token in ("BrainCore", "brain.skills", "brain.planning",
                      "brain_core_enabled"):
            self.assertNotIn(token, source,
                             f"server.py must not reference {token} in Step 0")


if __name__ == '__main__':
    unittest.main()
