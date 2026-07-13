"""
core/interfaces.py — Lumina V2 Contract Layer

Abstract base class interfaces for every major subsystem.

Rules:
  - Interfaces expose BEHAVIOUR only — no implementation details.
  - Each interface is small and focused (Interface Segregation Principle).
  - All concrete classes are wired through container.py.
  - No interface may import from a concrete module in this codebase.

Naming convention:  IFoo  — interface for the Foo subsystem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


# ===========================================================================
# IBrainState
# Owned by: Server startup (singleton)
# Used by:  All subsystems that need to read or mutate runtime state
# Implemented by: brain/state.py::BrainState
# ===========================================================================

class IBrainState(ABC):
    """
    Interface for the central runtime state manager.

    Implementors:  BrainState (backend/brain/state.py)

    BrainState is the single source of truth for all mutable runtime state.
    Readers always receive a frozen snapshot; writers use a transaction
    context manager that provides atomicity and rollback-on-exception.

    Rules:
    - NEVER cache the snapshot object — call snapshot() each time.
    - NEVER mutate snapshot fields — they are frozen Pydantic models.
    - ALWAYS use transaction() to write — never poke private fields directly.
    """

    @abstractmethod
    def snapshot(self) -> Any:
        """
        Return an immutable frozen BrainSnapshot representing the current state.

        Thread-safe.  Multiple threads may call snapshot() concurrently.
        The returned object is permanently frozen (Pydantic frozen model).
        """

    @abstractmethod
    def transaction(self) -> Any:
        """
        Context manager for atomic state mutation.

        Usage::

            with brain_state.transaction() as draft:
                draft.session_id = "some-id"
                draft.current_project = "alpha"

        - Changes are committed only if no exception is raised.
        - Nested transactions on the same thread are safe (RLock).
        - Other threads see the OLD state until the transaction commits.
        """

    @abstractmethod
    def reset_session(self) -> None:
        """Reset all session-scoped fields to defaults (call on disconnect)."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return a diagnostic dict (no sensitive data)."""


# ===========================================================================
# IMemoryManager
# Owned by: Brain
# Used by:  server.py (read/write), lumina.py (AudioLoop.memory_store)
# ===========================================================================

class IMemoryManager(ABC):
    """
    Interface for the passive memory persistence layer.

    Implementors:  MemoryStore (backend/memory_store.py)

    The memory manager stores and retrieves user facts, preferences, session
    summaries, and identity anchors.  It MUST NOT trigger actions or modify
    system behaviour as a side-effect of reads.
    """

    # ---- Writes ----

    @abstractmethod
    def add_memory(
        self,
        memory_type: str,
        content: str,
        metadata: Optional[Dict] = None,
        state: str = "active",
        confidence: float = 1.0,
        priority: int = 50,
    ) -> int:
        """Persist a new memory. Returns the assigned database row id."""

    @abstractmethod
    def promote_memory(
        self,
        memory_id: int,
        new_state: str = "active",
        confidence: Optional[float] = None,
    ) -> bool:
        """Promote a memory record (e.g. pending → active)."""

    @abstractmethod
    def demote_memory(self, memory_id: int, new_state: str = "dormant") -> bool:
        """Demote a memory record (e.g. active → dormant)."""

    @abstractmethod
    def mark_used(self, memory_id: int, boost: int = 3) -> None:
        """Bump access count and priority for a recently-accessed record."""

    # ---- Reads ----

    @abstractmethod
    def get_memories(
        self,
        memory_type: Optional[str] = None,
        limit: int = 10,
        update_access: bool = True,
    ) -> List[Dict]:
        """Retrieve memories, optionally filtered by type."""

    @abstractmethod
    def get_identity_memories(self) -> List[Dict]:
        """Return identity-anchor memories that should always be injected."""

    @abstractmethod
    def get_latest_session_summary(self) -> Optional[Dict]:
        """Return the most-recent session summary for continuity injection."""

    @abstractmethod
    def get_active_for_injection(self, limit: int = 20) -> List[Dict]:
        """Return active memories ordered by priority for prompt injection."""

    @abstractmethod
    def get_pending_assumptions(self, limit: int = 5) -> List[Dict]:
        """Return pending assumptions for cautious injection or revisit."""

    @abstractmethod
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """Full-text search across memory content."""

    @abstractmethod
    def get_stats(self) -> Dict:
        """Return statistics about the memory store."""


# ===========================================================================
# IKnowledgeManager
# Owned by: MemoryManager
# Used by:  server.py (hybrid search on transcripts)
# ===========================================================================

class IKnowledgeManager(ABC):
    """
    Interface for the hybrid semantic + lexical retrieval engine.

    Implementors:  MemoryEngine (backend/memory_engine.py)
    """

    @abstractmethod
    async def search_memory(self, query: str, top_k: int = 8) -> List[Dict]:
        """
        Hybrid search (vector + keyword).
        Returns at most top_k ranked excerpt dicts.
        """

    @abstractmethod
    def search_memory_sync(self, query: str, top_k: int = 8) -> List[Dict]:
        """
        Synchronous fallback for search_memory.
        Used when an asyncio executor is not available.
        """

    @abstractmethod
    def store_transcript(
        self,
        role: str,
        content: str,
        project_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[int]:
        """Persist a conversation transcript line. Returns row id or None."""

    @abstractmethod
    async def index_text(
        self,
        source_type: str,
        source_id: str,
        text: str,
        project_name: Optional[str] = None,
    ) -> int:
        """Chunk, dedup, embed, and index text. Returns count of new chunks added."""

    @abstractmethod
    def detect_memory_signals(self, text: str, memory_store: Any) -> List[Dict]:
        """
        Detect intent and assumption signals.
        Returns list of detected memory dicts (each with 'response_hint').
        """

    @abstractmethod
    def get_revisit_candidates(self, memory_store: Any) -> List[Dict]:
        """Return stale pending memories that should be revisited."""

    @abstractmethod
    def build_revisit_hint(self, stale: List[Dict]) -> Optional[str]:
        """Build a natural-language revisit directive string, or None."""

    @abstractmethod
    def get_status(self) -> Dict:
        """Return statistics about the knowledge engine."""


# ===========================================================================
# IWorkspaceManager
# Owned by: SessionManager / Brain
# Used by:  lumina.py (AudioLoop.project_manager)
# ===========================================================================

class IWorkspaceManager(ABC):
    """
    Interface for project workspace management.

    Implementors:  ProjectManager (backend/project_manager.py)
    """

    @property
    @abstractmethod
    def current_project(self) -> str:
        """Name of the currently-active project."""

    @abstractmethod
    def create_project(self, name: str) -> tuple:
        """
        Create a new project workspace.
        Returns (success: bool, message: str).
        """

    @abstractmethod
    def switch_project(self, name: str) -> tuple:
        """
        Switch active project context.
        Returns (success: bool, message: str).
        """

    @abstractmethod
    def list_projects(self) -> List[str]:
        """Return names of all existing project workspaces."""

    @abstractmethod
    def get_current_project_path(self) -> Path:
        """Return the filesystem path of the active project workspace."""

    @abstractmethod
    def log_chat(self, sender: str, text: str) -> None:
        """Append a chat message to the active project's chat_history.jsonl."""

    @abstractmethod
    def save_cad_artifact(self, source_path: str, prompt: str) -> Optional[str]:
        """
        Copy a generated CAD file into the active project's cad/ folder.
        Returns the destination path string, or None on failure.
        """

    @abstractmethod
    def get_project_context(self, max_file_size: int = 10_000) -> str:
        """Return a formatted string describing the active project's file tree."""


# ===========================================================================
# ISmartHomeAgent
# Owned by: Brain / server.py (singletons)
# Used by:  tool_handlers.py, server.py (kasa_agent)
# ===========================================================================

class ISmartHomeAgent(ABC):
    """
    Interface for TP-Link Kasa smart device control.

    Implementors:  KasaAgent (backend/kasa_agent.py)
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Load and connect to known devices from saved configuration."""

    @abstractmethod
    async def discover_devices(self) -> List[Dict]:
        """Scan the local network and return a list of discovered device dicts."""

    @abstractmethod
    async def turn_on(self, target: str) -> bool:
        """Turn on a device identified by IP or alias. Returns success."""

    @abstractmethod
    async def turn_off(self, target: str) -> bool:
        """Turn off a device identified by IP or alias. Returns success."""

    @abstractmethod
    async def set_brightness(self, target: str, brightness: int) -> bool:
        """Set brightness (0–100). Returns success."""

    @abstractmethod
    async def set_color(self, target: str, color_input: Any) -> bool:
        """Set color by name string or (H, S, V) tuple. Returns success."""


# ===========================================================================
# ICadAgent
# Owned by: AudioLoop
# Used by:  tool_handlers.py
# ===========================================================================

class ICadAgent(ABC):
    """
    Interface for AI-assisted 3D CAD generation.

    Implementors:  CadAgent (backend/cad_agent.py)
    """

    @abstractmethod
    async def generate_prototype(
        self,
        prompt: str,
        output_dir: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Generate a new 3D model from a text description.
        Returns a dict with keys 'format', 'data' (b64 STL), 'file_path';
        or None on failure.
        """

    @abstractmethod
    async def iterate_prototype(
        self,
        prompt: str,
        output_dir: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Apply iterative modifications to the most-recent CAD design.
        Returns same shape as generate_prototype, or None on failure.
        """


# ===========================================================================
# IPrinterAgent
# Owned by: AudioLoop
# Used by:  tool_handlers.py
# ===========================================================================

class IPrinterAgent(ABC):
    """
    Interface for 3D printer discovery, slicing, and job submission.

    Implementors:  PrinterAgent (backend/printer_agent.py)
    """

    @abstractmethod
    async def discover_printers(self, timeout: float = 5.0) -> List[Dict]:
        """Scan the local network for 3D printers. Returns list of printer dicts."""

    @abstractmethod
    async def slice_stl(
        self,
        stl_path: str,
        output_path: Optional[str] = None,
        profile_path: Optional[str] = None,
        root_path: Optional[str] = None,
        printer_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Slice an STL to G-code via OrcaSlicer/PrusaSlicer CLI.
        Returns the path to the generated .gcode file, or None on failure.
        """

    @abstractmethod
    async def upload_gcode(
        self,
        target: str,
        gcode_path: str,
        start_print: bool = False,
    ) -> bool:
        """
        Upload G-code to a printer and optionally start the job.
        Returns success.
        """

    @abstractmethod
    async def get_status(self, target: str) -> Optional[Dict]:
        """Return current status dict for the named printer, or None."""


# ===========================================================================
# IModelGateway
# Owned by: Brain / Orchestrator
# (Placeholder — Gemini Live client is currently embedded in AudioLoop)
# ===========================================================================

class IModelGateway(ABC):
    """
    Interface for LLM / multimodal model API access.

    NOTE: Lumina currently uses the Gemini Live API directly inside
    AudioLoop.  This interface is defined here so future refactors can
    wrap or swap providers without touching orchestration code.

    Implementors:  (future) GeminiLiveGateway
    """

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 1.0,
    ) -> str:
        """Generate a text response for a given prompt. Returns the response string."""

    @abstractmethod
    async def generate_embeddings(self, text: str) -> List[float]:
        """Compute and return a float embedding vector for the given text."""


# ===========================================================================
# IEventBus
# Owned by: (singleton, created at server init)
# Used by:  all subsystems that publish or subscribe to events
# (Placeholder — Event Bus is a future Phase 2 deliverable)
# ===========================================================================

class IEventBus(ABC):
    """
    Interface for the async publish/subscribe Event Bus.

    NOTE: The Event Bus implementation will be delivered in Phase 2
    (refactor/event-bus-foundation).  This interface is defined here so
    all module contracts are complete before any module is implemented.

    Implementors:  (future) InProcessEventBus
    """

    @abstractmethod
    async def publish(self, topic: str, payload: Dict, priority: str = "MEDIUM") -> None:
        """Publish an event payload to a topic string."""

    @abstractmethod
    async def subscribe(self, topic: str, callback: Any) -> Any:
        """
        Subscribe to a topic pattern (supports wildcards).
        Returns a SubscriptionToken that can be passed to unsubscribe().
        """

    @abstractmethod
    async def unsubscribe(self, token: Any) -> None:
        """Remove a subscription by its token."""


# ===========================================================================
# IExecutionContext
# Owned by: caller (created via ExecutionContextFactory)
# Used by:  any subsystem that wants typed request/unit-of-work identifiers
# Implemented by: core/context.py::ExecutionContext
# ===========================================================================

class IExecutionContext(ABC):
    """
    Interface for an immutable execution-context value object.

    Implementors:  ExecutionContext (backend/core/context.py)

    Carries identifiers for a single unit of work (request, tool call,
    background task) so callers can trace it and its descendants without
    reaching into globals. Concrete field access is implementation detail;
    this interface only guarantees the ability to derive a child context.
    """

    @abstractmethod
    def child(self, **overrides: Any) -> "IExecutionContext":
        """
        Derive a new child context for sub-work spawned by this context.

        The child keeps the parent's correlation_id (for end-to-end
        tracing) but gets its own context_id and records parent_id.
        Any keyword override replaces the corresponding inherited field.
        """
