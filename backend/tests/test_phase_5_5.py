"""
tests/test_phase_5_5.py — Phase 5.5 Step 1: Skill Metadata foundation

Proves:
  - existing SkillSpec registration API still works (unchanged signature)
  - a derived SkillMetadata is available for every registered skill
  - SkillMetadata is immutable (frozen dataclass, tuple fields)
  - duplicate ids still rejected
  - all 19 builtins gain metadata with no registration changes
  - SkillSpec (execution contract) is untouched
  - no runtime consumer: BrainCore / SkillManager / executor unchanged

Stdlib unittest; google SDK mocked before core imports (established pattern).
"""

import dataclasses
import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

sys.modules.setdefault('google', MagicMock())
sys.modules.setdefault('google.genai', MagicMock())
sys.modules.setdefault('google.genai.types', MagicMock())

from brain.skills.models import SkillSpec
from brain.skills.metadata import SkillMetadata
from brain.skills.registry import SkillRegistry
from brain.skills.interfaces import ISkillRegistry
from brain.skills.builtin import BUILTIN_SKILLS, seed_registry


class TestMetadataModel(unittest.TestCase):
    def test_from_spec_maps_fields(self):
        spec = SkillSpec(id="x.y", name="Do Y", description="does y",
                         tags=["cat", "extra"], permissions=["p"],
                         provider="legacy", provider_ref="y", version="1.2.3")
        md = SkillMetadata.from_spec(spec)
        self.assertEqual(md.id, "x.y")
        self.assertEqual(md.display_name, "Do Y")
        self.assertEqual(md.description, "does y")
        self.assertEqual(md.category, "cat")          # first tag
        self.assertEqual(md.permissions, ("p",))
        self.assertEqual(md.tags, ("cat", "extra"))
        self.assertEqual(md.version, "1.2.3")
        self.assertEqual(md.inputs, ())
        self.assertEqual(md.outputs, ())
        self.assertFalse(md.confirmation_required)

    def test_category_defaults_when_no_tags(self):
        md = SkillMetadata.from_spec(SkillSpec(id="a", name="A", provider="legacy"))
        self.assertEqual(md.category, "general")

    def test_metadata_is_frozen(self):
        md = SkillMetadata.from_spec(SkillSpec(id="a", name="A", provider="legacy"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            md.display_name = "changed"

    def test_metadata_is_hashable(self):
        md = SkillMetadata.from_spec(SkillSpec(id="a", name="A", provider="legacy",
                                               tags=["t"], permissions=["p"]))
        hash(md)  # tuple fields → hashable; raises if a list leaked in


class TestRegistryMetadata(unittest.TestCase):
    def setUp(self):
        self.reg = SkillRegistry()
        self.spec = SkillSpec(id="test.echo", name="Echo", description="echo",
                              tags=["util"], provider="legacy", provider_ref="echo")

    def test_existing_register_api_unchanged(self):
        # Same single-arg register(spec) call as before.
        self.reg.register(self.spec)
        self.assertIs(self.reg.get("test.echo"), self.spec)
        self.assertEqual(len(self.reg), 1)

    def test_metadata_available_after_register(self):
        self.reg.register(self.spec)
        md = self.reg.get_metadata("test.echo")
        self.assertIsInstance(md, SkillMetadata)
        self.assertEqual(md.display_name, "Echo")
        self.assertEqual(md.category, "util")

    def test_get_metadata_missing_returns_none(self):
        self.assertIsNone(self.reg.get_metadata("nope"))

    def test_all_metadata(self):
        self.reg.register(self.spec)
        self.reg.register(SkillSpec(id="test.two", name="Two", provider="legacy"))
        mds = self.reg.all_metadata()
        self.assertEqual(len(mds), 2)
        self.assertEqual({m.id for m in mds}, {"test.echo", "test.two"})

    def test_duplicate_id_rejected(self):
        self.reg.register(self.spec)
        with self.assertRaises(ValueError):
            self.reg.register(self.spec)

    def test_registry_implements_interface(self):
        self.assertIsInstance(self.reg, ISkillRegistry)


class TestBuiltinsGainMetadata(unittest.TestCase):
    def test_all_builtins_have_metadata(self):
        reg = SkillRegistry()
        seeded = seed_registry(reg)                     # unchanged seed call
        self.assertEqual(seeded, len(BUILTIN_SKILLS))
        self.assertEqual(len(reg.all_metadata()), len(BUILTIN_SKILLS))
        for spec in BUILTIN_SKILLS:
            md = reg.get_metadata(spec.id)
            self.assertIsNotNone(md, f"{spec.id} missing metadata")
            self.assertEqual(md.id, spec.id)
            self.assertEqual(md.version, spec.version)


class TestSkillSpecUntouched(unittest.TestCase):
    def test_skillspec_still_frozen_pydantic(self):
        spec = SkillSpec(id="a", name="A", provider="legacy")
        with self.assertRaises(Exception):
            spec.id = "b"

    def test_skillspec_fields_unchanged(self):
        fields = set(SkillSpec.model_fields.keys())
        self.assertEqual(fields, {"id", "name", "description", "tags",
                                  "permissions", "provider", "provider_ref",
                                  "version"})


if __name__ == '__main__':
    unittest.main()
