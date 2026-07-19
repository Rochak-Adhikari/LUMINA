"""
brain/core/context_builder.py — ContextBuilder (Phase 5.6.5: workspace enrichment)

Assembles a BrainContext from a BrainRequest plus read-only runtime state.

Consults the BrainState snapshot (5.1) and, when a WorkspaceMemoryManager is
injected, the current workspace's structured-memory snapshot (5.6.5). Both are
READ-ONLY: no mutation, no I/O, no writes. When the workspace manager is
absent, workspace_ctx stays empty exactly as before.

No mutation. No I/O. No side effects.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.interfaces import IBrainState
from brain.core.interfaces import IContextBuilder
from brain.core.models import BrainContext, BrainRequest


class ContextBuilder(IContextBuilder):
    """
    Read-only assembler of BrainContext.

    Collaborators are injected and all optional so the builder can be
    constructed in isolation for tests:
      brain_state              — BrainState snapshot extract (5.1).
      workspace_memory_manager — current workspace snapshot (5.6.5). When None,
                                 workspace_ctx stays empty (unchanged behavior).
    """

    def __init__(
        self,
        brain_state: Optional[IBrainState] = None,
        workspace_memory_manager: Optional[Any] = None,
    ) -> None:
        self._brain_state = brain_state
        self._workspace_memory_manager = workspace_memory_manager

    def build(self, request: BrainRequest) -> BrainContext:
        """Return a frozen BrainContext for *request*."""
        return BrainContext(
            request=request,
            brain_snapshot=self._snapshot_extract(),
            workspace_ctx=self._workspace_extract(),
            # memories / persona_state / recent_history: later milestones.
        )

    def _snapshot_extract(self) -> Dict[str, Any]:
        """
        Extract a small read-only dict from BrainState.snapshot().

        Uses get_status() (the diagnostic view) rather than the raw
        snapshot model so this layer stays decoupled from BrainSnapshot's
        field structure. Failure-safe: returns {} if state is unavailable.
        """
        if self._brain_state is None:
            return {}
        try:
            return dict(self._brain_state.get_status())
        except Exception:
            return {}

    def _workspace_extract(self) -> Dict[str, Any]:
        """
        Read-only extract of the current workspace's structured memory.

        Returns the current WorkspaceMemory snapshot as a plain dict, or {}
        when no manager is injected (unchanged behavior). Never mutates the
        workspace memory and never writes. Failure-safe.
        """
        if self._workspace_memory_manager is None:
            return {}
        try:
            return dict(self._workspace_memory_manager.current().snapshot().model_dump())
        except Exception:
            return {}

