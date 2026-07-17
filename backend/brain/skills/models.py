"""
brain/skills/models.py — Phase 5.2 skill value objects

Pure pydantic data models, same conventions as brain/core/models.py:
frozen, no business logic, no I/O, no runtime imports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillSpec(BaseModel):
    """Metadata describing one skill. Descriptive only — no implementation."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique skill id, e.g. 'legacy.navigation'.")
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(
        default_factory=list,
        description="Permission keys required to run (informational in 5.2).",
    )
    provider: str = Field(
        default="legacy",
        description='Execution backend kind: "legacy" | "python" | "mcp" | '
        '"remote" (only "legacy" has an executor in 5.2).',
    )
    provider_ref: str = Field(
        default="",
        description="Provider-specific reference (e.g. legacy tool name).",
    )
    version: str = Field(default="0.1.0")


class SkillResult(BaseModel):
    """Outcome of one skill execution."""

    model_config = ConfigDict(frozen=True)

    skill_id: str
    ok: bool = False
    output: Any = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
