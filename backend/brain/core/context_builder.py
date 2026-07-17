"""
brain/core/context_builder.py — Phase 5.1 ContextBuilder

Assembles a BrainContext from a BrainRequest plus read-only runtime state.

Phase 5.1 scope: only the BrainState snapshot is consulted (a small,
diagnostic-safe extract). Memory retrieval, workspace context, persona
state, and history enrichment arrive in later milestones — the fields
exist on BrainContext but stay empty here.

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

    Collaborators are injected; brain_state is optional so the builder can
    be constructed in isolation for tests.
    """

    def __init__(self, brain_state: Optional[IBrainState] = None) -> None:
        self._brain_state = brain_state

    def build(self, request: BrainRequest) -> BrainContext:
        """Return a frozen BrainContext for *request*."""
        return BrainContext(
            request=request,
            brain_snapshot=self._snapshot_extract(),
            # workspace_ctx / memories / persona_state / recent_history:
            # populated by later Phase 5 milestones; empty defaults here.
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
