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


class RetrievalHit(BaseModel):
    """
    A single record matched by the WorkspaceRetriever (Phase 5.9.1).

    ``record_type`` is an opaque, free-form identifier supplied by the caller
    / producer — NOT an enum and NOT a closed set. Any future record kind fits
    without changing this model. ``record_id`` is the matched record's id ("" for
    records without one). ``record`` is the frozen source value object.
    """

    model_config = ConfigDict(frozen=True)

    record_type: str
    record_id: str = ""
    record: Any


class WorkspaceRetrievalResult(BaseModel):
    """
    Immutable, serializable result of a retrieval query (Phase 5.9.1).

    ``hits`` are ordered deterministically: retrieval traverses the
    WorkspaceSnapshot in a defined sequence and preserves each record's
    insertion order. Same memory state + query + filters always yields
    identical output.
    """

    model_config = ConfigDict(frozen=True)

    query: str
    hits: List[RetrievalHit] = Field(default_factory=list)


class WorkspaceRecallContext(BaseModel):
    """
    Prepared, read-only workspace recall carried on BrainContext (Phase 5.9.7).

    One field per recall kind, each a frozen WorkspaceRetrievalResult. Every
    field ALWAYS holds a valid result (default: empty query, empty hits) — there
    is no "not executed" state, so consumers read ``ctx.workspace_recall.
    decisions.hits`` with no None checks. "Ran, no matches" and "not enriched"
    both present as empty hits; both are deterministic.

    Append-only: future recall kinds ADD a new field defaulting to an empty
    result. Existing fields are never renamed, reordered, or removed.
    """

    model_config = ConfigDict(frozen=True)

    decisions: WorkspaceRetrievalResult = Field(
        default_factory=lambda: WorkspaceRetrievalResult(query="")
    )
    notes: WorkspaceRetrievalResult = Field(
        default_factory=lambda: WorkspaceRetrievalResult(query="")
    )
    tasks: WorkspaceRetrievalResult = Field(
        default_factory=lambda: WorkspaceRetrievalResult(query="")
    )
    architecture: WorkspaceRetrievalResult = Field(
        default_factory=lambda: WorkspaceRetrievalResult(query="")
    )


def _prompt_line(hit: "RetrievalHit") -> str:
    """
    Reduce a RetrievalHit to a single prompt-safe line, deterministically.

    Prefers the record's title, then name, then body/rationale/notes, else the
    record id. Pure string extraction — never leaks the record object.
    """
    record = hit.record
    for attr in ("title", "name"):
        value = getattr(record, attr, None)
        if value:
            return str(value)
    for attr in ("rationale", "body", "notes", "architecture"):
        value = getattr(record, attr, None)
        if value:
            return str(value)
    return str(hit.record_id)


class PromptWorkspaceContext(BaseModel):
    """
    Prompt-safe projection of WorkspaceRecallContext (Phase 5.9.8).

    ==== ARCHITECTURE BOUNDARY (permanent — see ADR-0007) ====
    This model is the ONLY object allowed to cross into prompt generation.
    Prompt builders may consume ONLY PromptWorkspaceContext. They MUST NEVER
    receive any of:
        WorkspaceMemory, WorkspaceSnapshot, WorkspaceRetriever, RetrievalHit,
        WorkspaceMemoryManager / Store, Recall services, WorkspaceRecallContext,
        WorkspaceSync / Activation, or any runtime/mutable object.
    Retrieval and recall stay strictly below ContextBuilder; nothing about them
    leaks past this boundary.
    ==========================================================

    The PERMANENT contract handed to prompt builders. Contains ONLY prompt-safe
    primitive values — lists of plain strings, one per recalled record.

    Frozen, deterministic (insertion order preserved), append-only: future
    recall kinds ADD a new list field; existing fields never change.

    Built ONLY from a WorkspaceRecallContext via ``from_recall`` — never from a
    retriever, memory, or snapshot.
    """

    model_config = ConfigDict(frozen=True)

    decisions: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    tasks: List[str] = Field(default_factory=list)
    architecture: List[str] = Field(default_factory=list)

    @classmethod
    def from_recall(cls, recall: "WorkspaceRecallContext") -> "PromptWorkspaceContext":
        """Deterministically project a WorkspaceRecallContext into prompt lines."""
        return cls(
            decisions=[_prompt_line(h) for h in recall.decisions.hits],
            notes=[_prompt_line(h) for h in recall.notes.hits],
            tasks=[_prompt_line(h) for h in recall.tasks.hits],
            architecture=[_prompt_line(h) for h in recall.architecture.hits],
        )
