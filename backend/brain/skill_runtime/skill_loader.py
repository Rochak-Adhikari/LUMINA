"""
brain/skill_runtime/skill_loader.py — Phase 8.5: SkillLoader

Turns an approved skill description into a loaded, ready-to-execute instance.
The first runtime stage that materializes a usable object from an installed
skill package. It does EXACTLY one thing:

    SandboxDecision → locate module → import → instantiate → validate → LoadedSkill

It NEVER executes the skill (that is Phase 8.6), calls tools, plans, schedules,
caches, hot-reloads, or manages lifecycle. Depends only on the Phase 8.4
SandboxDecision. Never imports Skill Creator internals.

Loading is inherently side-effecting (a module import from disk) — the single
permitted side effect at this stage. Everything is failure-safe: any locate/
import/instantiate/validate error yields loaded=False with a descriptive
``error`` and never raises.

Contract with generated packages: the installed skill's implementation file is
``<installed_location>/skill.py`` exposing a ``Skill`` class with a callable
``execute`` or ``run`` method. (Phase 7 currently emits an inert ``run``
scaffold; the loader validates the interface, it does not call it.)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Optional

from brain.skill_runtime.interfaces import ISkillLoader
from brain.skill_runtime.models import LoadedSkill, SandboxDecision

_IMPL_FILENAME = "skill.py"
_SKILL_CLASS = "Skill"
# Canonical runtime entrypoint (Phase 8.6). A single interface going forward:
# ``run(context)``. A skill exposing only a legacy ``execute`` is accepted via a
# minimal compatibility shim (recorded as entrypoint "run"); no dual interface.
_CANONICAL_ENTRYPOINT = "run"
_LEGACY_ENTRYPOINT = "execute"


class SkillLoader(ISkillLoader):
    """Loads an approved skill package into a validated instance. No execution."""

    def load(self, decision: SandboxDecision) -> LoadedSkill:
        if not decision.approved:
            return LoadedSkill(loaded=False, error="not_approved")

        skill = decision.skill
        if skill is None or not skill.installed_location:
            return LoadedSkill(
                loaded=False, skill=skill, error="no_installed_location"
            )

        module_path = Path(skill.installed_location) / _IMPL_FILENAME
        if not module_path.is_file():
            return LoadedSkill(
                loaded=False, skill=skill, module_path=str(module_path),
                error="module_not_found",
            )

        # Locate + import the module by file path (no package assumptions, no
        # sys.path mutation). Deterministic module name from the registry key.
        try:
            module = self._import_module(module_path, skill.registry_key)
        except Exception as e:  # noqa: BLE001 — failure-safe, never raises out
            return LoadedSkill(
                loaded=False, skill=skill, module_path=str(module_path),
                error=f"import_failed: {type(e).__name__}",
            )

        skill_cls = getattr(module, _SKILL_CLASS, None)
        if not isinstance(skill_cls, type):
            return LoadedSkill(
                loaded=False, skill=skill, module_path=str(module_path),
                error="missing_skill_class",
            )

        try:
            instance = skill_cls()
        except Exception as e:  # noqa: BLE001
            return LoadedSkill(
                loaded=False, skill=skill, module_path=str(module_path),
                error=f"instantiation_failed: {type(e).__name__}",
            )

        entrypoint = self._validate_interface(instance)
        if entrypoint is None:
            return LoadedSkill(
                loaded=False, skill=skill, module_path=str(module_path),
                error="missing_entrypoint",
            )

        return LoadedSkill(
            loaded=True, skill=skill, instance=instance,
            entrypoint=entrypoint, module_path=str(module_path),
        )

    @staticmethod
    def _import_module(module_path: Path, registry_key: str):
        mod_name = f"lumina_skill__{registry_key}".replace(".", "_").replace(":", "_")
        spec = importlib.util.spec_from_file_location(mod_name, str(module_path))
        if spec is None or spec.loader is None:
            raise ImportError("spec_unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _validate_interface(instance: object) -> Optional[str]:
        # Canonical interface is run(); a legacy execute() is tolerated (a thin
        # shim in the executor bridges it). Either way the entrypoint reported is
        # the canonical "run".
        if callable(getattr(instance, _CANONICAL_ENTRYPOINT, None)):
            return _CANONICAL_ENTRYPOINT
        if callable(getattr(instance, _LEGACY_ENTRYPOINT, None)):
            return _CANONICAL_ENTRYPOINT
        return None
