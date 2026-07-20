"""
brain/skill_creator/blueprint_tester.py — Phase 7.5: BlueprintTester

Pipeline stage 04 (Testing). Consumes ONE GenerationResult plus its
SkillBlueprint and produces ONE immutable TestResult. Statically evaluates the
generated package against the test categories the blueprint declared
(verification_contract.required_test_categories), applying
minimum_pass_requirements.

Gated: testing only proceeds when generation.generated is True; otherwise it
returns an untested result with a skipped_reason. It NEVER executes generated
code, imports it, writes files, or installs anything — every category is a
static inspection of the generated file contents.

Deterministic: pure function of (blueprint, generation). No UUID, timestamps,
randomness, hashing, filesystem, network, or LLM. Same inputs -> byte-identical
TestResult.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
typing.
"""

from __future__ import annotations

from typing import Dict, List

from brain.skill_creator.interfaces import IBlueprintTester
from brain.skill_creator.models import (
    SkillBlueprint,
    GenerationResult,
    TestResult,
)

# Tokens that would make a generated skill non-deterministic or unsafe. Static
# inspection only — the strings are searched in generated file text, never run.
_NONDETERMINISM_TOKENS = ("uuid", "random", "datetime", "time.time", "os.urandom")
_UNSAFE_TOKENS = ("subprocess", "os.system", "eval(", "exec(", "compile(", "__import__")


class BlueprintTester(IBlueprintTester):
    """Deterministic static tester of a generated skill package."""

    def test(
        self, blueprint: SkillBlueprint, generation: GenerationResult
    ) -> TestResult:
        # Gate: nothing to test if generation produced no package.
        if not generation.generated:
            return TestResult(
                blueprint_id=blueprint.id,
                recommendation_id=blueprint.recommendation_id,
                tested=False,
                skipped_reason="not_generated",
            )

        contract = blueprint.verification_contract
        categories: Dict[str, bool] = {}
        failures: List[str] = []

        for category in contract.required_test_categories:
            ok, reason = self._run_category(category, blueprint, generation)
            categories[category] = ok
            if not ok:
                failures.append(reason)

        return TestResult(
            blueprint_id=blueprint.id,
            recommendation_id=blueprint.recommendation_id,
            tested=True,
            passed=not failures,
            categories=categories,
            failures=failures,
        )

    # ---- static category evaluations (pure) ---------------------------

    def _run_category(self, category: str, bp: SkillBlueprint, gen: GenerationResult):
        if category == "unit":
            return self._cat_unit(bp, gen)
        if category == "determinism":
            return self._cat_determinism(bp, gen)
        if category == "safety":
            return self._cat_safety(bp, gen)
        return False, f"unknown_category:{category}"

    @staticmethod
    def _cat_unit(bp: SkillBlueprint, gen: GenerationResult):
        tests_path = bp.package_layout["tests"]
        content = gen.files.get(tests_path, "")
        if not content.strip():
            return False, "unit: no tests file generated"
        if "def test_" not in content:
            return False, "unit: no test function found"
        return True, ""

    @staticmethod
    def _cat_determinism(bp: SkillBlueprint, gen: GenerationResult):
        impl_path = bp.package_layout["implementation"]
        content = gen.files.get(impl_path, "")
        hit = [t for t in _NONDETERMINISM_TOKENS if t in content]
        if hit:
            return False, f"determinism: nondeterministic tokens {sorted(hit)}"
        return True, ""

    @staticmethod
    def _cat_safety(bp: SkillBlueprint, gen: GenerationResult):
        impl_path = bp.package_layout["implementation"]
        content = gen.files.get(impl_path, "")
        hit = [t for t in _UNSAFE_TOKENS if t in content]
        if hit:
            return False, f"safety: unsafe tokens {sorted(hit)}"
        if not bp.approval_required:
            return False, "safety: approval_required must be True"
        return True, ""
