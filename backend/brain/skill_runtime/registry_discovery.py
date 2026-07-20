"""
brain/skill_runtime/registry_discovery.py — Phase 8.1: RegistryDiscovery

The first runtime consumer of the Phase 7 registry. Answers "what skills exist?"
by reading the frozen IBlueprintRegistry and projecting its RegistryEntry catalog
into read-only DiscoveredSkill records — so the Planner discovers skills through
this service instead of importing skills (or the Registry) directly.

Read-only and deterministic:
  - never registers, installs, mutates, or executes anything;
  - the registry is duck-typed (only ``.entries()`` is called), so there is no
    import of BlueprintRegistry and no upward dependency;
  - only "registered" entries are visible (skipped/unregistered are hidden);
  - supersession is honored WITHOUT mutating the catalog: when a registry_key
    has multiple appended entries, the most-recently appended registered entry
    wins (matching BlueprintRegistry.get semantics);
  - results are sorted by (skill_family, package_name, registry_key), so
    ordering is independent of registry insertion order.

Depends only on brain.skill_runtime.models, brain.skill_runtime.interfaces,
typing. No clocks, identifiers, entropy, hashing, environment, or I/O.
"""

from __future__ import annotations

from typing import Any, List

from brain.skill_runtime.interfaces import IRegistryDiscovery
from brain.skill_runtime.models import DiscoveredSkill, RegistrySearchResult


class RegistryDiscovery(IRegistryDiscovery):
    """Deterministic, read-only discovery over the installed-skill registry."""

    def __init__(self, registry: Any) -> None:
        # Duck-typed: only registry.entries() is used. No BlueprintRegistry import,
        # so Phase 8 never depends upward on the Phase 7 concrete class.
        self._registry = registry

    def discover(self, query: str = "") -> RegistrySearchResult:
        needle = query.strip().lower()

        # Supersession without mutation (matches BlueprintRegistry.get: the most
        # recently appended entry per key wins). Iterate in reverse, keep the
        # first seen per registry_key — regardless of status — so a later
        # skipped/unregistered entry correctly hides an earlier registered one.
        winners: dict[str, Any] = {}
        for entry in reversed(list(self._registry.entries())):
            key = entry.registry_key
            if key not in winners:
                winners[key] = entry

        matched: List[DiscoveredSkill] = []
        for entry in winners.values():
            if entry.registration_status != "registered":
                continue
            if needle and not self._matches(entry, needle):
                continue
            matched.append(
                DiscoveredSkill(
                    blueprint_id=entry.blueprint_id,
                    recommendation_id=entry.recommendation_id,
                    semantic_fingerprint=entry.semantic_fingerprint,
                    skill_family=entry.skill_family,
                    package_name=entry.package_name,
                    registry_key=entry.registry_key,
                    installed_location=entry.installed_location,
                    registration_status=entry.registration_status,
                )
            )

        matched.sort(key=lambda s: (s.skill_family, s.package_name, s.registry_key))
        return RegistrySearchResult(
            skills=matched, total_count=len(matched), query=query
        )

    @staticmethod
    def _matches(entry: Any, needle: str) -> bool:
        haystack = (
            entry.skill_family,
            entry.package_name,
            entry.semantic_fingerprint,
        )
        return any(needle in (field or "").lower() for field in haystack)
