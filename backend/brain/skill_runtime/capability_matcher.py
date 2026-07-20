"""
brain/skill_runtime/capability_matcher.py — Phase 8.2: CapabilityMatcher

Semantic layer over Registry Discovery. Where RegistryDiscovery answers "what
skills exist?", CapabilityMatcher answers "which of those skills satisfy this
capability request?" — so the Planner asks the matcher and never touches the
registry directly.

Boundary: depends ONLY on IRegistryDiscovery (injected). Never imports the
Registry, RegistryEntry, BlueprintRegistry, or any skill_creator stage. It reads
the read-only DiscoveredSkill projection produced by discovery and ranks it.

Pure and deterministic:
  - no I/O, disk, network, environment, subprocess;
  - no clocks, uuids, randomness, or hashing;
  - no loading, execution, reflection, or importing of generated skills;
  - no side effects, no globals, no registry mutation.

Matching operates on the projected DiscoveredSkill surface (skill_family,
package_name, semantic_fingerprint, registry_key). Priority, high → low:

    100  exact capability      capability == skill_family
     80  alias                 capability is a substring of semantic_fingerprint
                               or package_name
     60  tag                   any requested tag appears in family / package /
                               fingerprint

``family`` and ``package`` are hard restrictions (a mismatch excludes the skill
before scoring). With neither capability nor tags supplied, the request is a
pure filter: every skill surviving the restrictions is returned at score 0.

Ordering: score descending, then skill_family, package_name, registry_key.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from brain.skill_runtime.interfaces import ICapabilityMatcher, IRegistryDiscovery
from brain.skill_runtime.models import (
    CapabilityMatch,
    CapabilityMatchResult,
    CapabilityRequest,
    DiscoveredSkill,
)

_EXACT = 100
_ALIAS = 80
_TAG = 60


class CapabilityMatcher(ICapabilityMatcher):
    """Deterministic, pure capability matching over discovered skills."""

    def __init__(self, discovery: IRegistryDiscovery) -> None:
        # Depends only on the discovery contract — never the registry itself.
        self._discovery = discovery

    def match(self, request: CapabilityRequest) -> CapabilityMatchResult:
        capability = (request.capability or "").strip().lower()
        family = self._norm(request.family)
        package = self._norm(request.package)
        tags = tuple(t.strip().lower() for t in request.tags if t and t.strip())

        # Descriptive layer: the full registered catalog, already read-only.
        skills = self._discovery.discover().skills

        matches: List[CapabilityMatch] = []
        for skill in skills:
            # Hard restrictions first — a mismatch removes the skill entirely.
            if family is not None and skill.skill_family.lower() != family:
                continue
            if package is not None and skill.package_name.lower() != package:
                continue

            score, reason = self._score(skill, capability, tags)

            # A semantic request (capability or tags) that scores nothing is not
            # a candidate. A pure-filter request (neither given) keeps survivors.
            if score == 0 and (capability or tags):
                continue

            matches.append(CapabilityMatch(skill=skill, score=score, reason=reason))

        matches.sort(
            key=lambda m: (
                -m.score,
                m.skill.skill_family,
                m.skill.package_name,
                m.skill.registry_key,
            )
        )
        return CapabilityMatchResult(
            matches=matches,
            match_count=len(matches),
            capability=request.capability or "",
        )

    @staticmethod
    def _norm(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = value.strip().lower()
        return v or None

    @staticmethod
    def _score(
        skill: DiscoveredSkill, capability: str, tags: Tuple[str, ...]
    ) -> Tuple[int, str]:
        family = skill.skill_family.lower()
        package = skill.package_name.lower()
        fingerprint = skill.semantic_fingerprint.lower()

        if capability:
            if capability == family:
                return _EXACT, "exact capability"
            if (fingerprint and capability in fingerprint) or (
                package and capability in package
            ):
                return _ALIAS, "alias"

        if tags:
            haystack = (family, package, fingerprint)
            for tag in tags:
                if any(tag in field for field in haystack if field):
                    return _TAG, "tag"

        return 0, "filter" if not (capability or tags) else ""