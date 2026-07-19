"""
brain/workspace/models.py — Phase 5.6.1: Workspace Memory value objects

Frozen, serializable pydantic models. No business logic, no I/O, no runtime
imports — same conventions as brain/core/models.py and brain/skills/models.py.

These are the structured records a workspace's memory holds. Persistence
(5.6.3), the in-memory store (5.6.2), and Brain enrichment (5.6.5) build on
these; this milestone only defines the shapes.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _new_id() -> str:
    """Opaque unique identifier for a workspace record."""
    return uuid.uuid4().hex


class ProjectInfo(BaseModel):
    """High-level description of the project a workspace represents."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str = ""
    architecture: str = Field(
        default="", description="Free-text architecture summary."
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    """A recorded implementation / design decision."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    title: str
    rationale: str = ""
    tags: List[str] = Field(default_factory=list)


class Note(BaseModel):
    """A free-form project note."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    title: str
    body: str = ""
    tags: List[str] = Field(default_factory=list)


class WorkspaceTask(BaseModel):
    """A project task / TODO item (workspace-scoped, distinct from quests)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    title: str
    status: str = Field(
        default="open", description='"open" | "in_progress" | "done".'
    )
    notes: str = ""


class WorkspaceSnapshot(BaseModel):
    """
    Immutable read-only view of a workspace's structured memory.

    This is what ContextBuilder will read (5.6.5) to populate
    BrainContext.workspace_ctx. Frozen — safe to hand to the read-only
    cognitive layer.
    """

    model_config = ConfigDict(frozen=True)

    workspace: str
    info: Optional[ProjectInfo] = None
    decisions: List[Decision] = Field(default_factory=list)
    notes: List[Note] = Field(default_factory=list)
    tasks: List[WorkspaceTask] = Field(default_factory=list)
