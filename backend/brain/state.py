"""
brain/state.py — Lumina V2 BrainState

Single thread-safe source of runtime truth for all Lumina subsystems.

Design principles
─────────────────
1. SINGLE SOURCE OF TRUTH
   All mutable runtime state lives here.  No other module keeps its own
   parallel copy of session-level state.

2. IMMUTABLE SNAPSHOTS
   Readers always receive a frozen Pydantic model (BrainSnapshot).
   Snapshots are safe to pass across threads without further locking.
   Snapshot fields cannot be mutated after construction.

3. ATOMIC MUTATIONS via context manager
   Writers use:
       with brain_state.transaction() as draft:
           draft.session_id = "abc"
           draft.current_project = "myproject"
   Changes are only committed if no exception is raised.
   Partial updates are never visible to concurrent readers.

4. THREAD SAFETY
   Internal RLock (re-entrant) permits nested transactions on the same
   thread without deadlock.  A write lock is held for the minimum time
   required to apply changes.

5. PYDANTIC MODELS
   State is represented as Pydantic models for:
   - Strong typing and validation
   - Clear field-level documentation
   - Serialization to JSON for persistence (future)
   - Frozen snapshots (model_config = ConfigDict(frozen=True))

6. BACKWARD COMPATIBILITY
   BrainState coexists with legacy global variables in server.py.
   Existing code is NOT modified.  Migration of legacy state into
   BrainState will happen incrementally in later phases.

Lifecycle
─────────
  Created: at server startup, registered in DI container
  Mutated: via transaction() context manager by any subsystem
  Read:    via snapshot() anywhere, any thread, lock-free after first copy
  Destroyed: never (process lifetime)
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from core.interfaces import IBrainState


# ===========================================================================
# Section 1: Pydantic field models (sub-objects inside the main state)
# Each model is intentionally small and focused on one responsibility.
# ===========================================================================


class SessionInfo(BaseModel):
    """Metadata about the active Gemini Live session."""

    model_config = ConfigDict(frozen=True)

    session_id: Optional[str] = Field(
        default=None,
        description="Opaque identifier for the current Gemini Live connection.",
    )
    connected_at: Optional[float] = Field(
        default=None,
        description="Unix timestamp (float) when the session connected.",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Gemini model name in use (e.g. 'gemini-2.5-flash-native-audio-...').",
    )
    client_sid: Optional[str] = Field(
        default=None,
        description="Socket.IO session ID of the connected frontend client.",
    )
    is_generating: bool = Field(
        default=False,
        description="True while Gemini is actively generating a response turn.",
    )


class WorkspaceInfo(BaseModel):
    """Active workspace and project context."""

    model_config = ConfigDict(frozen=True)

    current_project: str = Field(
        default="temp",
        description="Name of the currently active project workspace.",
    )
    project_root: Optional[str] = Field(
        default=None,
        description="Absolute filesystem path to the project root directory.",
    )


class ConversationMeta(BaseModel):
    """Conversation-level metadata for the current session."""

    model_config = ConfigDict(frozen=True)

    turn_index: int = Field(
        default=0,
        description="Number of completed user→assistant turns in this session.",
    )
    last_user_text: Optional[str] = Field(
        default=None,
        description="Last transcribed user utterance (plain text, no audio).",
    )
    last_assistant_text: Optional[str] = Field(
        default=None,
        description="Last generated assistant utterance (transcription).",
    )
    last_activity_ts: Optional[float] = Field(
        default=None,
        description="Unix timestamp of the last user utterance.",
    )
    mood_state: str = Field(
        default="calm",
        description=(
            "Lightweight sentiment state derived from recent messages. "
            "Values: calm | playful | focused | frustrated | low_energy."
        ),
    )


class RuntimeFlags(BaseModel):
    """Boolean flags that control runtime behaviour."""

    model_config = ConfigDict(frozen=True)

    audio_paused: bool = Field(
        default=False,
        description="True when the mic is intentionally muted by the user.",
    )
    camera_active: bool = Field(
        default=False,
        description="True when the camera / screen-capture feed is active.",
    )
    phone_connected: bool = Field(
        default=False,
        description="True when the remote phone dashboard is streaming audio.",
    )
    face_auth_passed: bool = Field(
        default=False,
        description="True after face authentication has been verified this session.",
    )


class ExecutionContext(BaseModel):
    """
    Ephemeral execution context for in-flight operations.

    Fields here are intentionally transient — they represent what is
    happening RIGHT NOW during tool execution.  They are not persisted.
    """

    model_config = ConfigDict(frozen=True)

    active_tool: Optional[str] = Field(
        default=None,
        description="Name of the tool currently executing, or None.",
    )
    tool_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the currently executing tool.",
    )
    pending_confirmation_id: Optional[str] = Field(
        default=None,
        description="UUID of a tool waiting for user confirmation, or None.",
    )


class PlannerContext(BaseModel):
    """
    Reserved for the Planner Engine (Phase 2).

    Placeholder fields are included here so that BrainState's shape is
    stable before the Planner is implemented.  Future phases will populate
    and consume these fields.
    """

    model_config = ConfigDict(frozen=True)

    current_plan_id: Optional[str] = Field(
        default=None,
        description="ID of the active execution plan, or None.",
    )
    pending_tasks: List[str] = Field(
        default_factory=list,
        description="Ordered list of pending task IDs in the current plan.",
    )
    completed_tasks: List[str] = Field(
        default_factory=list,
        description="List of task IDs completed in the current session.",
    )
    plan_depth: int = Field(
        default=0,
        description="Nesting depth of the current execution context.",
    )


# ===========================================================================
# Section 2: BrainSnapshot — the immutable read view
# ===========================================================================


class BrainSnapshot(BaseModel):
    """
    Frozen, immutable snapshot of BrainState.

    Created by BrainState.snapshot().  Once constructed, this model
    is permanently frozen — no field can be mutated.  Safe to pass
    between threads without any further synchronisation.

    Consumers should call brain_state.snapshot() each time they need
    fresh data rather than caching the snapshot object.
    """

    model_config = ConfigDict(frozen=True)

    # ── Core sub-models ────────────────────────────────────────────────
    session: SessionInfo = Field(default_factory=SessionInfo)
    workspace: WorkspaceInfo = Field(default_factory=WorkspaceInfo)
    conversation: ConversationMeta = Field(default_factory=ConversationMeta)
    flags: RuntimeFlags = Field(default_factory=RuntimeFlags)
    execution: ExecutionContext = Field(default_factory=ExecutionContext)
    planner: PlannerContext = Field(default_factory=PlannerContext)

    # ── Top-level timestamps ───────────────────────────────────────────
    created_at: float = Field(
        default_factory=time.time,
        description="Unix timestamp when this snapshot was taken.",
    )


# ===========================================================================
# Section 3: MutableDraft — used inside transaction()
# ===========================================================================


class _MutableDraft:
    """
    A mutable proxy for editing BrainState fields inside a transaction.

    Only the fields in BrainState._MUTABLE_FIELDS are accessible.  Any
    attempt to write an unknown field raises AttributeError immediately
    rather than silently swallowing typos.

    This object is private — it is only ever exposed inside the
    ``with brain_state.transaction() as draft:`` context manager.
    """

    __slots__ = (
        # Session
        "session_id", "connected_at", "model_name", "client_sid", "is_generating",
        # Workspace
        "current_project", "project_root",
        # Conversation
        "turn_index", "last_user_text", "last_assistant_text",
        "last_activity_ts", "mood_state",
        # Flags
        "audio_paused", "camera_active", "phone_connected", "face_auth_passed",
        # Execution
        "active_tool", "tool_args", "pending_confirmation_id",
        # Planner
        "current_plan_id", "pending_tasks", "completed_tasks", "plan_depth",
    )

    def __init__(self, snapshot: BrainSnapshot) -> None:
        # Populate from current snapshot so callers only override what changed
        snap = snapshot
        # Session
        object.__setattr__(self, "session_id", snap.session.session_id)
        object.__setattr__(self, "connected_at", snap.session.connected_at)
        object.__setattr__(self, "model_name", snap.session.model_name)
        object.__setattr__(self, "client_sid", snap.session.client_sid)
        object.__setattr__(self, "is_generating", snap.session.is_generating)
        # Workspace
        object.__setattr__(self, "current_project", snap.workspace.current_project)
        object.__setattr__(self, "project_root", snap.workspace.project_root)
        # Conversation
        object.__setattr__(self, "turn_index", snap.conversation.turn_index)
        object.__setattr__(self, "last_user_text", snap.conversation.last_user_text)
        object.__setattr__(self, "last_assistant_text", snap.conversation.last_assistant_text)
        object.__setattr__(self, "last_activity_ts", snap.conversation.last_activity_ts)
        object.__setattr__(self, "mood_state", snap.conversation.mood_state)
        # Flags
        object.__setattr__(self, "audio_paused", snap.flags.audio_paused)
        object.__setattr__(self, "camera_active", snap.flags.camera_active)
        object.__setattr__(self, "phone_connected", snap.flags.phone_connected)
        object.__setattr__(self, "face_auth_passed", snap.flags.face_auth_passed)
        # Execution
        object.__setattr__(self, "active_tool", snap.execution.active_tool)
        object.__setattr__(self, "tool_args", dict(snap.execution.tool_args))
        object.__setattr__(self, "pending_confirmation_id", snap.execution.pending_confirmation_id)
        # Planner
        object.__setattr__(self, "current_plan_id", snap.planner.current_plan_id)
        object.__setattr__(self, "pending_tasks", list(snap.planner.pending_tasks))
        object.__setattr__(self, "completed_tasks", list(snap.planner.completed_tasks))
        object.__setattr__(self, "plan_depth", snap.planner.plan_depth)

    def _to_snapshot(self) -> BrainSnapshot:
        """Materialise this draft into a new frozen BrainSnapshot."""
        return BrainSnapshot(
            session=SessionInfo(
                session_id=self.session_id,
                connected_at=self.connected_at,
                model_name=self.model_name,
                client_sid=self.client_sid,
                is_generating=self.is_generating,
            ),
            workspace=WorkspaceInfo(
                current_project=self.current_project,
                project_root=self.project_root,
            ),
            conversation=ConversationMeta(
                turn_index=self.turn_index,
                last_user_text=self.last_user_text,
                last_assistant_text=self.last_assistant_text,
                last_activity_ts=self.last_activity_ts,
                mood_state=self.mood_state,
            ),
            flags=RuntimeFlags(
                audio_paused=self.audio_paused,
                camera_active=self.camera_active,
                phone_connected=self.phone_connected,
                face_auth_passed=self.face_auth_passed,
            ),
            execution=ExecutionContext(
                active_tool=self.active_tool,
                tool_args=dict(self.tool_args),
                pending_confirmation_id=self.pending_confirmation_id,
            ),
            planner=PlannerContext(
                current_plan_id=self.current_plan_id,
                pending_tasks=list(self.pending_tasks),
                completed_tasks=list(self.completed_tasks),
                plan_depth=self.plan_depth,
            ),
        )


# ===========================================================================
# Section 4: BrainState — the authoritative stateful object
# ===========================================================================


class BrainState(IBrainState):
    """
    Thread-safe, single source of runtime truth for Lumina V2.

    Instantiate once at server startup and register in the DI container::

        from brain.state import BrainState
        from core.container import container
        from core.interfaces import IBrainState

        bs = BrainState()
        container.register_instance(IBrainState, bs)

    Reading state (lock-free after snapshot construction)::

        snap = brain_state.snapshot()
        print(snap.workspace.current_project)
        print(snap.session.is_generating)

    Writing state (atomic, under RLock)::

        with brain_state.transaction() as draft:
            draft.current_project = "my_project"
            draft.is_generating = True

    The transaction() context manager guarantees:
    - Changes are applied atomically.
    - If an exception is raised inside the block, no change is committed.
    - Nested transactions on the same thread are supported (RLock).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: BrainSnapshot = BrainSnapshot()
        print("[BrainState] Initialized — ready for transactions.")

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    def snapshot(self) -> BrainSnapshot:
        """
        Return an immutable snapshot of the current state.

        The snapshot is taken under the write lock so it always reflects
        a consistent committed state.  Once returned, the snapshot object
        is permanently frozen — it cannot be modified.

        Thread-safe: multiple threads may call snapshot() concurrently.
        """
        with self._lock:
            return self._state

    # ------------------------------------------------------------------
    # Public write API
    # ------------------------------------------------------------------

    @contextmanager
    def transaction(self) -> Generator[_MutableDraft, None, None]:
        """
        Atomic mutation context manager.

        Usage::

            with brain_state.transaction() as draft:
                draft.session_id = "some-id"
                draft.current_project = "project_alpha"
                draft.turn_index += 1

        - All changes are batched and applied atomically on context exit.
        - If an exception propagates out of the block, no changes are applied.
        - The RLock allows nested transactions on the same thread without
          deadlock (useful when a method calls another method that also
          uses a transaction).
        - Other threads calling snapshot() during the transaction will
          see the OLD state until the transaction commits.

        Raises:
            Any exception raised inside the ``with`` block.
        """
        with self._lock:
            draft = _MutableDraft(self._state)
            try:
                yield draft
                # Commit: materialise the draft into a new frozen snapshot
                self._state = draft._to_snapshot()
            except Exception:
                # Rollback: draft is discarded, state unchanged
                raise

    # ------------------------------------------------------------------
    # Convenience helpers (thin wrappers over transaction)
    # ------------------------------------------------------------------

    def set_session(
        self,
        session_id: Optional[str] = None,
        client_sid: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        """Convenience: update session fields atomically."""
        with self.transaction() as draft:
            if session_id is not None:
                draft.session_id = session_id
                draft.connected_at = time.time()
            if client_sid is not None:
                draft.client_sid = client_sid
            if model_name is not None:
                draft.model_name = model_name

    def set_generating(self, value: bool) -> None:
        """Mark whether Gemini is actively generating a response turn."""
        with self.transaction() as draft:
            draft.is_generating = value

    def set_project(self, project: str, root: Optional[str] = None) -> None:
        """Switch active project atomically."""
        with self.transaction() as draft:
            draft.current_project = project
            if root is not None:
                draft.project_root = root

    def record_user_turn(self, text: str, mood_state: str = "calm") -> None:
        """Record a completed user utterance and increment the turn counter."""
        with self.transaction() as draft:
            draft.last_user_text = text
            draft.last_activity_ts = time.time()
            draft.mood_state = mood_state
            draft.turn_index += 1

    def record_assistant_turn(self, text: str) -> None:
        """Record a completed assistant utterance."""
        with self.transaction() as draft:
            draft.last_assistant_text = text

    def set_tool_executing(
        self,
        tool_name: Optional[str],
        tool_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a tool as executing (or clear execution state with None)."""
        with self.transaction() as draft:
            draft.active_tool = tool_name
            draft.tool_args = tool_args or {}

    def set_pending_confirmation(self, confirmation_id: Optional[str]) -> None:
        """Set or clear a pending tool confirmation UUID."""
        with self.transaction() as draft:
            draft.pending_confirmation_id = confirmation_id

    def set_audio_paused(self, paused: bool) -> None:
        """Toggle the audio-paused flag."""
        with self.transaction() as draft:
            draft.audio_paused = paused

    def set_phone_connected(self, connected: bool) -> None:
        """Toggle the phone-connected flag."""
        with self.transaction() as draft:
            draft.phone_connected = connected

    def reset_session(self) -> None:
        """
        Reset all session-scoped fields to defaults.

        Call this when Gemini Live disconnects or a new session starts.
        Workspace and long-term fields are NOT cleared — only the
        transient session fields.
        """
        with self.transaction() as draft:
            draft.session_id = None
            draft.connected_at = None
            draft.client_sid = None
            draft.is_generating = False
            draft.turn_index = 0
            draft.last_user_text = None
            draft.last_assistant_text = None
            draft.last_activity_ts = None
            draft.mood_state = "calm"
            draft.active_tool = None
            draft.tool_args = {}
            draft.pending_confirmation_id = None
            draft.face_auth_passed = False

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a diagnostic dict describing current state (no sensitive data)."""
        snap = self.snapshot()
        return {
            "session_connected": snap.session.session_id is not None,
            "client_sid": snap.session.client_sid,
            "is_generating": snap.session.is_generating,
            "current_project": snap.workspace.current_project,
            "turn_index": snap.conversation.turn_index,
            "mood_state": snap.conversation.mood_state,
            "audio_paused": snap.flags.audio_paused,
            "phone_connected": snap.flags.phone_connected,
            "active_tool": snap.execution.active_tool,
            "plan_depth": snap.planner.plan_depth,
            "snapshot_age_s": round(time.time() - snap.created_at, 3),
        }
