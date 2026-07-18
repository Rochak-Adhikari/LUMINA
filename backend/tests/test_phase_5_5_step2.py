"""
tests/test_phase_5_5_step2.py — Phase 5.5 Step 2: Capability Discovery

Proves registry.search(...) works as a passive, deterministic, read-only
capability query over SkillMetadata. Nothing in the runtime consumes it.

Matching rules under test:
  category exact; permission contains; tags/inputs/outputs contain-all;
  confirmation_required exact bool; None ignores the filter.

Note: builtins carry inputs=()/outputs=()/confirmation_required=False
(Step 1 placeholders), so inputs/outputs/confirmation cases use hand-built
SkillMetadata registered via SkillSpec + a monkey-injected metadata where the
derived fields are empty. To exercise inputs/outputs we register specs whose
derived metadata we then assert against directly (empty), plus a dedicated
registry seeded with SkillMetadata-bearing specs is not possible (from_spec
sets inputs/outputs empty by design) — so inputs/outputs matching is proven
against a registry whose metadata we construct through a small subclass hook.
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

from brain.skills.models import SkillSpec
from brain.skills.metadata import SkillMetadata
from brain.skills.registry import SkillRegistry


class _MetadataRegistry(SkillRegistry):
    """Test helper: register a SkillMetadata directly so inputs/outputs/
    confirmation (which from_spec leaves empty/False by design) can be
    exercised. Only used by tests — production always derives via from_spec."""

    def register_md(self, md: SkillMetadata) -> None:
        with self._lock:
            if md.id in self._metadata:
                raise ValueError(f"dup {md.id}")
            # Keep a matching spec so len()/get stay consistent.
            self._specs[md.id] = SkillSpec(id=md.id, name=md.display_name,
                                           provider="legacy")
            self._metadata[md.id] = md


def _spec(id, name, tags=(), permissions=()):
    return SkillSpec(id=id, name=name, tags=list(tags),
                     permissions=list(permissions), provider="legacy",
                     provider_ref=id.split(".")[-1])


class TestSearchBySpecDerived(unittest.TestCase):
    def setUp(self):
        self.reg = SkillRegistry()
        # Registration ORDER is significant for determinism assertions.
        self.reg.register(_spec("browser.search", "Search", tags=["browser", "github"],
                                permissions=["internet"]))
        self.reg.register(_spec("browser.open", "Open", tags=["browser"],
                                permissions=["internet"]))
        self.reg.register(_spec("fs.write", "Write", tags=["filesystem"],
                                permissions=["disk"]))

    def test_search_by_category(self):
        # category := first tag (from_spec). browser.* have category "browser".
        got = [m.id for m in self.reg.search(category="browser")]
        self.assertEqual(got, ["browser.search", "browser.open"])

    def test_search_by_permission(self):
        got = [m.id for m in self.reg.search(permission="internet")]
        self.assertEqual(got, ["browser.search", "browser.open"])
        self.assertEqual([m.id for m in self.reg.search(permission="disk")],
                         ["fs.write"])

    def test_search_by_tags_all(self):
        self.assertEqual([m.id for m in self.reg.search(tags=["github"])],
                         ["browser.search"])
        self.assertEqual([m.id for m in self.reg.search(tags=["browser", "github"])],
                         ["browser.search"])
        # tag not present anywhere → empty
        self.assertEqual(self.reg.search(tags=["nope"]), [])

    def test_multiple_filters(self):
        got = [m.id for m in self.reg.search(category="browser", permission="internet",
                                             tags=["github"])]
        self.assertEqual(got, ["browser.search"])

    def test_empty_results(self):
        self.assertEqual(self.reg.search(category="does-not-exist"), [])

    def test_no_filters_returns_all_in_order(self):
        got = [m.id for m in self.reg.search()]
        self.assertEqual(got, ["browser.search", "browser.open", "fs.write"])

    def test_confirmation_false_matches_derived_default(self):
        # from_spec sets confirmation_required=False for all → all match False,
        # none match True.
        self.assertEqual(len(self.reg.search(confirmation_required=False)), 3)
        self.assertEqual(self.reg.search(confirmation_required=True), [])

    def test_returns_metadata_type(self):
        for m in self.reg.search(category="browser"):
            self.assertIsInstance(m, SkillMetadata)

    def test_deterministic_ordering_repeatable(self):
        a = [m.id for m in self.reg.search(permission="internet")]
        b = [m.id for m in self.reg.search(permission="internet")]
        self.assertEqual(a, b)


class TestSearchInputsOutputsConfirmation(unittest.TestCase):
    """Exercise inputs/outputs/confirmation via directly-registered metadata."""

    def setUp(self):
        self.reg = _MetadataRegistry()
        self.reg.register_md(SkillMetadata(
            id="a", display_name="A", category="c1",
            inputs=("query",), outputs=("results",),
            confirmation_required=True, tags=("t",)))
        self.reg.register_md(SkillMetadata(
            id="b", display_name="B", category="c1",
            inputs=("query", "limit"), outputs=("results",),
            confirmation_required=False, tags=("t",)))
        self.reg.register_md(SkillMetadata(
            id="c", display_name="C", category="c2",
            inputs=(), outputs=("path",), confirmation_required=False))

    def test_search_by_inputs_all(self):
        self.assertEqual([m.id for m in self.reg.search(inputs=["query"])], ["a", "b"])
        self.assertEqual([m.id for m in self.reg.search(inputs=["query", "limit"])], ["b"])

    def test_search_by_outputs_all(self):
        self.assertEqual([m.id for m in self.reg.search(outputs=["results"])], ["a", "b"])
        self.assertEqual([m.id for m in self.reg.search(outputs=["path"])], ["c"])

    def test_search_by_confirmation(self):
        self.assertEqual([m.id for m in self.reg.search(confirmation_required=True)], ["a"])
        self.assertEqual([m.id for m in self.reg.search(confirmation_required=False)],
                         ["b", "c"])

    def test_combined_inputs_confirmation(self):
        self.assertEqual(
            [m.id for m in self.reg.search(inputs=["query"], confirmation_required=False)],
            ["b"])


class TestRegistrationUnchanged(unittest.TestCase):
    def test_get_and_register_still_work(self):
        reg = SkillRegistry()
        spec = _spec("x.y", "XY", tags=["t"])
        reg.register(spec)
        self.assertIs(reg.get("x.y"), spec)
        self.assertEqual(len(reg), 1)

    def test_duplicate_still_rejected(self):
        reg = SkillRegistry()
        spec = _spec("x.y", "XY")
        reg.register(spec)
        with self.assertRaises(ValueError):
            reg.register(spec)

    def test_find_still_returns_specs(self):
        # Existing find() (Phase 5.2) is untouched and still returns SkillSpec.
        reg = SkillRegistry()
        reg.register(_spec("x.y", "XY", tags=["t"]))
        found = reg.find(tags=["t"])
        self.assertIsInstance(found[0], SkillSpec)


if __name__ == '__main__':
    unittest.main()
