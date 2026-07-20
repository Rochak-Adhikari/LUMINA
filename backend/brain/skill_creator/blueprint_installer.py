"""
brain/skill_creator/blueprint_installer.py — Phase 7.7: BlueprintInstaller

Pipeline stage 06 (Installation). Consumes an approved ApprovalRecord plus its
GenerationResult and materializes the generated package's files under a
caller-supplied target root. This is the FIRST pipeline stage permitted to write
to the filesystem.

Rules:
  - Gated: installs only when ApprovalRecord.approved is True; otherwise returns
    an uninstalled record with a skipped_reason.
  - Installs ONLY the files already present in GenerationResult.files — never
    regenerates, executes, imports, activates, or registers.
  - Idempotent + deterministic: reinstalling the same GenerationResult to the
    same target yields the same filesystem state and a byte-identical
    InstallationRecord.

Determinism: no uuid, datetime, random, hashing, environment, network,
subprocess, or execution. The install location is derived deterministically from
the target root + the package name. installed_files are sorted for stable output.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
pathlib, typing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from brain.skill_creator.interfaces import IBlueprintInstaller
from brain.skill_creator.models import (
    ApprovalRecord,
    GenerationResult,
    InstallationRecord,
)

_INSTALL_MODE = "copy"

# Characters not safe for a directory name across platforms. Replaced with '_'
# deterministically so the install path is valid and reproducible.
_UNSAFE_PATH_CHARS = ':*?"<>|'


def _safe_dirname(name: str) -> str:
    """Deterministic filesystem-safe directory name for a package."""
    out = name
    for ch in _UNSAFE_PATH_CHARS:
        out = out.replace(ch, "_")
    return out or "skill"


class BlueprintInstaller(IBlueprintInstaller):
    """Deterministic, idempotent installer of an approved generated package."""

    def install(
        self,
        approval: ApprovalRecord,
        generation: GenerationResult,
        target_root: str,
    ) -> InstallationRecord:
        # Gate: never install without a granted approval.
        if not approval.approved:
            return InstallationRecord(
                blueprint_id=generation.blueprint_id,
                recommendation_id=generation.recommendation_id,
                installed=False,
                skipped_reason="not_approved",
            )

        if not generation.generated:
            return InstallationRecord(
                blueprint_id=generation.blueprint_id,
                recommendation_id=generation.recommendation_id,
                installed=False,
                skipped_reason="not_generated",
            )

        # Deterministic install location: <target_root>/<safe package name>.
        location = Path(target_root) / _safe_dirname(generation.package_name)
        location.mkdir(parents=True, exist_ok=True)

        installed_files: List[str] = []
        # Sort by relative path so materialization order is deterministic.
        for rel_path in sorted(generation.files):
            content = generation.files[rel_path]
            dest = location / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Idempotent write: same content -> same bytes. newline="" keeps the
            # generated text exact (no platform newline translation).
            dest.write_text(content, encoding="utf-8", newline="")
            installed_files.append(rel_path)

        return InstallationRecord(
            blueprint_id=generation.blueprint_id,
            recommendation_id=generation.recommendation_id,
            installed=True,
            installed_location=str(location),
            installed_files=installed_files,  # already sorted
            installation_mode=_INSTALL_MODE,
        )
