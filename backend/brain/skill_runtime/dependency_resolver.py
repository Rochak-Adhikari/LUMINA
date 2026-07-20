"""
brain/skill_runtime/dependency_resolver.py — Phase 8.3: DependencyResolver

The gate between matching and loading. Given the Phase 8.2 CapabilityMatchResult
plus the runtime's supplied grants, selects the highest-ranked candidate whose
dependencies are all satisfied and returns an immutable DependencyResolution.
Nothing may load or execute until resolution succeeds.

Boundary: depends ONLY on Phase 8.2 output (CapabilityMatchResult / its
DiscoveredSkill entries) and caller-supplied grants. Never imports the Registry,
RegistryEntry, BlueprintRegistry, or any skill_creator stage. Pure and
deterministic: no I/O, network, clocks, uuids, randomness, hashing, loading,
execution, reflection, or mutation.

Requirements checked (on the read-only DiscoveredSkill surface):
  - "registration"   the skill's registration_status is "registered";
  - "install"        installed_location is non-empty (materialized on disk);
  - "capability"     each entry in available_capabilities, when supplied, must
                     include the resolved capability (skill_family) — a runtime
                     may restrict which capability families it will run;
  - "runtime"        runtime_version, when supplied, is accepted (recorded as
                     satisfied — precise version constraints are deferred to
                     Phase 8.9, since the frozen RegistryEntry projection carries
                     no minimum-version field);
  - "permission"     each entry in granted_permissions is recorded as an allowed
                     grant; permission ENFORCEMENT against a skill's declared
                     needs is deferred to the Sandbox (Phase 8.4) because the
                     projection exposes no required_permissions.

Candidates are evaluated in the match ordering (already score-desc, then
family/package/key); the first fully-satisfied candidate wins — deterministic.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from brain.skill_runtime.interfaces import IDependencyResolver
from brain.skill_runtime.models import (
    CapabilityMatch,
    CapabilityMatchResult,
    DependencyRequirement,
    DependencyResolution,
)


class DependencyResolver(IDependencyResolver):
    """Deterministic, pure dependency gate over matched skills."""

    def resolve(
        self,
        matches: CapabilityMatchResult,
        *,
        granted_permissions: Optional[Tuple[str, ...]] = None,
        runtime_version: str = "",
        available_capabilities: Optional[Tuple[str, ...]] = None,
    ) -> DependencyResolution:
        caps = (
            tuple(c.strip().lower() for c in available_capabilities)
            if available_capabilities
            else None
        )
        perms = tuple(granted_permissions) if granted_permissions else ()

        if not matches.matches:
            return DependencyResolution(
                resolved=False, skill=None, reason="no_candidates"
            )

        # Evaluate candidates in the deterministic match order; first fully
        # satisfied wins. Keep the first candidate's checklist for reporting when
        # nothing resolves.
        first_reqs: List[DependencyRequirement] = []
        for match in matches.matches:
            reqs = self._requirements(match, caps, runtime_version, perms)
            if not first_reqs:
                first_reqs = reqs
            unsatisfied = tuple(r.value for r in reqs if not r.satisfied)
            if not unsatisfied:
                return DependencyResolution(
                    resolved=True,
                    skill=match.skill,
                    requirements=reqs,
                    unsatisfied=(),
                    reason="resolved",
                )

        first_unsatisfied = tuple(r.value for r in first_reqs if not r.satisfied)
        return DependencyResolution(
            resolved=False,
            skill=None,
            requirements=first_reqs,
            unsatisfied=first_unsatisfied,
            reason="unsatisfied_dependencies",
        )

    @staticmethod
    def _requirements(
        match: CapabilityMatch,
        caps: Optional[Tuple[str, ...]],
        runtime_version: str,
        perms: Tuple[str, ...],
    ) -> List[DependencyRequirement]:
        skill = match.skill
        reqs: List[DependencyRequirement] = []

        registered = skill.registration_status == "registered"
        reqs.append(DependencyRequirement(
            kind="registration", value="registered", satisfied=registered,
            detail="" if registered else f"status={skill.registration_status}",
        ))

        installed = bool(skill.installed_location)
        reqs.append(DependencyRequirement(
            kind="install", value="installed_location", satisfied=installed,
            detail="" if installed else "no installed_location",
        ))

        if caps is not None:
            fam = skill.skill_family.lower()
            ok = fam in caps
            reqs.append(DependencyRequirement(
                kind="capability", value=skill.skill_family, satisfied=ok,
                detail="" if ok else "family not in available_capabilities",
            ))

        if runtime_version:
            # Version constraints deferred to 8.9 — a supplied runtime version is
            # recorded as satisfied (no minimum in the projection to compare).
            reqs.append(DependencyRequirement(
                kind="runtime", value=runtime_version, satisfied=True,
                detail="version check deferred to Phase 8.9",
            ))

        for perm in perms:
            reqs.append(DependencyRequirement(
                kind="permission", value=perm, satisfied=True,
                detail="grant recorded; enforcement in Phase 8.4 sandbox",
            ))

        return reqs
