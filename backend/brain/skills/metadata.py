"""
brain/skills/metadata.py — Phase 5.5 Step 1: Skill Metadata foundation

A structured, immutable capability descriptor that sits BESIDE SkillSpec.

Design note (single source of truth): SkillSpec (brain/skills/models.py)
remains the execution-path contract — the planner/manager/executor pipeline
is unchanged and does not read SkillMetadata. To avoid two independently-
authored models drifting apart, SkillMetadata is DERIVED from a registered
SkillSpec via SkillMetadata.from_spec(). No registration call site changes;
every already-registered skill gains metadata automatically.

Nothing consumes this yet — this phase only introduces the foundation.
Python objects only (no JSON).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:  # avoid a hard import cycle; only needed for typing
    from brain.skills.models import SkillSpec


@dataclass(frozen=True)
class SkillMetadata:
    """
    Immutable structured metadata for one skill.

    Frozen dataclass; sequence fields are tuples so instances are hashable and
    cannot be mutated in place.
    """

    id: str
    display_name: str
    description: str = ""
    category: str = "general"
    permissions: Tuple[str, ...] = field(default_factory=tuple)
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    outputs: Tuple[str, ...] = field(default_factory=tuple)
    confirmation_required: bool = False
    version: str = "0.1.0"
    tags: Tuple[str, ...] = field(default_factory=tuple)
    source: str = "builtin"

    @classmethod
    def from_spec(cls, spec: "SkillSpec", source: str = "builtin") -> "SkillMetadata":
        """
        Derive metadata from a registered SkillSpec.

        *source* records where the skill came from (builtin/plugin/mcp/
        generated/remote). Descriptive only — the resolver may read it but
        must not prefer any source.

        Field mapping (SkillSpec is authoritative):
          id                    <- spec.id
          display_name          <- spec.name
          description           <- spec.description
          category              <- first tag, else "general"
          permissions / tags    <- spec.permissions / spec.tags (as tuples)
          version               <- spec.version
          source                <- source (default "builtin")
          inputs / outputs      <- empty (declared in a later phase)
          confirmation_required <- False (declared in a later phase)
        """
        tags = tuple(spec.tags)
        return cls(
            id=spec.id,
            display_name=spec.name,
            description=spec.description,
            category=(tags[0] if tags else "general"),
            permissions=tuple(spec.permissions),
            inputs=(),
            outputs=(),
            confirmation_required=False,
            version=spec.version,
            tags=tags,
            source=source,
        )
