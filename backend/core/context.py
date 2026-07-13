"""
core/context.py — Lumina V2 Execution Context Layer (Phase 1.4)

ExecutionContext is a lightweight, immutable value object that carries the
identifiers needed to trace a single unit of work (a request, a tool call,
a background task) through the system: who it belongs to, what session it
runs under, and what correlation id ties it to any child work it spawns.

This layer is purely additive. It does not replace BrainState (which owns
mutable *runtime* state) or EventBus (which owns pub/sub) — it complements
them by giving any caller a small, typed, immutable bundle of "which
request is this" information that can be threaded through function calls
or attached to event payloads, without reaching into globals.

Design principles
------------------
1. IMMUTABLE
   ExecutionContext is a frozen dataclass. Once created it cannot be
   mutated. To change anything, derive a child context.

2. CHILD CONTEXTS, NOT MUTATION
   child() returns a new ExecutionContext with a fresh context_id, the
   same correlation_id (so all descendants can be traced back to the same
   root unit of work), and parent_id set to the current context_id.

3. NO GLOBAL STATE
   ExecutionContext instances are created via ExecutionContextFactory and
   passed explicitly. Nothing here stores a "current context" in a module
   global or thread-local — that would reintroduce the scattered-state
   problem this layer exists to avoid.

4. FUTURE-READY, NOT FUTURE-BUILT
   Fields like correlation_id and parent_id are sufficient scaffolding for
   later async/multi-agent/distributed tracing, but no such execution
   logic is implemented here — only the identifiers.

Lifecycle
---------
  Created: ExecutionContextFactory.create(...) for a new root unit of work
  Derived: existing_context.child(...) when work spawns sub-work
  Read:    any field access (frozen, thread-safe by construction)
  Destroyed: never explicitly — garbage collected when no longer referenced
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping, Optional

from core.interfaces import IExecutionContext


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True)
class ExecutionContext(IExecutionContext):
    """
    Immutable bundle of identifiers describing a single unit of execution.

    Fields
    ------
    context_id      Unique id for THIS context instance.
    correlation_id  Shared by a root context and all of its descendants —
                     use this to trace an entire chain of related work.
    parent_id       context_id of the context this one was derived from,
                     or None for a root context.
    session_id      Gemini Live session id, if known (mirrors
                     BrainState.session.session_id — not synced automatically).
    client_sid      Socket.IO client sid, if known.
    workspace_id    Active project/workspace name, if known.
    created_at      Unix timestamp of construction.
    metadata        Arbitrary read-only extra data (immutable mapping).
    """

    context_id: str = field(default_factory=_new_id)
    correlation_id: str = field(default_factory=_new_id)
    parent_id: Optional[str] = None
    session_id: Optional[str] = None
    client_sid: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def child(
        self,
        *,
        session_id: Optional[str] = None,
        client_sid: Optional[str] = None,
        workspace_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "ExecutionContext":
        """
        Derive a child context for sub-work spawned by this context.

        The child gets a fresh context_id and parent_id=self.context_id,
        but keeps the same correlation_id so the whole chain remains
        traceable. Any explicitly-passed field overrides the parent's
        value; omitted fields are inherited.
        """
        merged_metadata = dict(self.metadata)
        if metadata:
            merged_metadata.update(metadata)

        return replace(
            self,
            context_id=_new_id(),
            parent_id=self.context_id,
            session_id=session_id if session_id is not None else self.session_id,
            client_sid=client_sid if client_sid is not None else self.client_sid,
            workspace_id=workspace_id if workspace_id is not None else self.workspace_id,
            created_at=time.time(),
            metadata=MappingProxyType(merged_metadata),
        )


class ExecutionContextFactory:
    """
    Constructs root ExecutionContext instances.

    This is the only supported way to create a context with a brand-new
    correlation_id. Use ExecutionContext.child() to derive descendants of
    an existing context.
    """

    def create(
        self,
        *,
        session_id: Optional[str] = None,
        client_sid: Optional[str] = None,
        workspace_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionContext:
        """Create a new root ExecutionContext with a fresh correlation_id."""
        return ExecutionContext(
            session_id=session_id,
            client_sid=client_sid,
            workspace_id=workspace_id,
            metadata=MappingProxyType(dict(metadata)) if metadata else MappingProxyType({}),
        )

    def from_brain_snapshot(self, snapshot: Any) -> ExecutionContext:
        """
        Convenience constructor that seeds a root context from a
        BrainState snapshot (as returned by IBrainState.snapshot()).

        Read-only: does not mutate BrainState. Fields that don't exist on
        the snapshot are left as None/defaults rather than raising, since
        BrainState may evolve independently of this layer.
        """
        session = getattr(snapshot, "session", None)
        workspace = getattr(snapshot, "workspace", None)
        return self.create(
            session_id=getattr(session, "session_id", None) if session else None,
            client_sid=getattr(session, "client_sid", None) if session else None,
            workspace_id=getattr(workspace, "current_project", None) if workspace else None,
        )
