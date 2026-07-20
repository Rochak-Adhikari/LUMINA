"""
brain/skill_creator/rollback_manager.py — Phase 7.11: RollbackManager

Pipeline stage 10 (Rollback) — the FINAL stage. Consumes an InstallationRecord
plus its SkillBlueprint and produces ONE immutable RollbackRecord, reversing
ONLY the filesystem materialization performed by BlueprintInstaller.

Rules:
  - Gated: if installation.installed is False, returns rollback_performed=False,
    rollback_status="skipped", skipped_reason="not_installed" — NO filesystem ops.
  - Deletes ONLY the files the installer created (installation.installed_files),
    each resolved relative to installation.installed_location. Missing files are
    ignored (idempotent). Never touches unrelated files.
  - Never walks outside installed_location; after removing files, prunes
    directories it empties (deepest first), never removing a directory that still
    contains anything.
  - Never edits any prior artifact (registry/lifecycle/marketplace), regenerates,
    executes, or imports generated code.

Deterministic + idempotent: rolling back the same InstallationRecord twice yields
the same filesystem state and a byte-identical RollbackRecord. No timestamps,
uuids, randomness, hashing, network, or subprocess.

Depends only on brain.skill_creator.models, brain.skill_creator.interfaces,
pathlib, typing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from brain.skill_creator.interfaces import IRollbackManager
from brain.skill_creator.models import (
    InstallationRecord,
    SkillBlueprint,
    RollbackRecord,
)


class RollbackManager(IRollbackManager):
    """Deterministic, idempotent installer-reversal. Owns no state."""

    def rollback(
        self, installation: InstallationRecord, blueprint: SkillBlueprint
    ) -> RollbackRecord:
        # Gate: nothing to reverse if never installed.
        if not installation.installed:
            return RollbackRecord(
                blueprint_id=blueprint.id,
                recommendation_id=blueprint.recommendation_id,
                rollback_performed=False,
                rollback_strategy=blueprint.rollback_strategy,
                rollback_status="skipped",
                skipped_reason="not_installed",
            )

        location = Path(installation.installed_location)
        removed: List[str] = []
        touched_dirs = set()

        # Delete ONLY installer-created files, scoped under installed_location.
        for rel_path in sorted(installation.installed_files):
            dest = location / rel_path
            # Scope guard: never act outside installed_location.
            if not self._within(location, dest):
                continue
            if dest.is_file():
                dest.unlink()
                removed.append(rel_path)
            touched_dirs.add(dest.parent)

        # Prune emptied directories, deepest first, never past installed_location.
        for directory in sorted(touched_dirs, key=lambda p: len(p.parts), reverse=True):
            self._prune_empty(directory, location)
        # Finally prune the install location itself if now empty.
        self._prune_empty(location, location)

        return RollbackRecord(
            blueprint_id=blueprint.id,
            recommendation_id=blueprint.recommendation_id,
            rollback_performed=True,
            rollback_location=str(location),
            removed_files=removed,  # already sorted
            rollback_strategy=blueprint.rollback_strategy,
            rollback_status="rolled_back",
        )

    # ---- helpers ------------------------------------------------------

    @staticmethod
    def _within(root: Path, candidate: Path) -> bool:
        """True if *candidate* is root or nested under it (lexical scope check)."""
        try:
            candidate.resolve().relative_to(root.resolve())
            return True
        except (ValueError, OSError):
            return False

    def _prune_empty(self, directory: Path, root: Path) -> None:
        """Remove *directory* (and empty parents up to root) if empty."""
        current = directory
        while self._within(root, current) and current.is_dir():
            try:
                next(current.iterdir())
                return  # not empty
            except StopIteration:
                pass
            parent = current.parent
            current.rmdir()
            if current == root:
                return
            current = parent
