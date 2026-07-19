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
from brain.workspace.models import (
    WorkspaceRecallContext,
    WorkspaceRetrievalResult,
    PromptWorkspaceContext,
)


class ContextBuilder(IContextBuilder):
    """
    Read-only assembler of BrainContext.

    Collaborators are injected and all optional so the builder can be
    constructed in isolation for tests:
      brain_state              — BrainState snapshot extract (5.1).
      workspace_memory_manager — current workspace snapshot (5.6.5). When None,
                                 workspace_ctx stays empty (unchanged behavior).
      decision_recall / notes_recall / task_recall / architecture_recall
                               — recall services (5.9.7), duck-typed on
                                 recall(query). When absent, workspace_recall
                                 stays empty (unchanged behavior). ContextBuilder
                                 is the ONLY workspace enrichment point; it never
                                 retrieves itself — it delegates to these.
    """

    def __init__(
        self,
        brain_state: Optional[IBrainState] = None,
        workspace_memory_manager: Optional[Any] = None,
        decision_recall: Optional[Any] = None,
        notes_recall: Optional[Any] = None,
        task_recall: Optional[Any] = None,
        architecture_recall: Optional[Any] = None,
    ) -> None:
        self._brain_state = brain_state
        self._workspace_memory_manager = workspace_memory_manager
        self._decision_recall = decision_recall
        self._notes_recall = notes_recall
        self._task_recall = task_recall
        self._architecture_recall = architecture_recall

    def build(self, request: BrainRequest) -> BrainContext:
        """Return a frozen BrainContext for *request*."""
        recall = self._workspace_recall_extract(request)
        return BrainContext(
            request=request,
            brain_snapshot=self._snapshot_extract(),
            workspace_ctx=self._workspace_extract(),
            workspace_recall=recall,
            prompt_workspace=PromptWorkspaceContext.from_recall(recall),
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

    def _workspace_recall_extract(self, request: BrainRequest) -> WorkspaceRecallContext:
        """
        Prepare read-only workspace recall for the planner (Phase 5.9.7).

        Derives the recall query deterministically from the request text (used
        verbatim — no NLP, no heuristics) and delegates to each injected recall
        service. ContextBuilder never retrieves itself; recall services own all
        retrieval. Failure-safe and absence-safe: any missing service or error
        yields an empty result for that kind, so the field is ALWAYS a valid
        WorkspaceRecallContext (unchanged behavior when nothing is injected).
        """
        query = (request.text or "").strip()
        return WorkspaceRecallContext(
            decisions=self._recall_one(self._decision_recall, query),
            notes=self._recall_one(self._notes_recall, query),
            tasks=self._recall_one(self._task_recall, query),
            architecture=self._recall_one(self._architecture_recall, query),
        )

    @staticmethod
    def _recall_one(service: Optional[Any], query: str) -> WorkspaceRetrievalResult:
        """Delegate to one recall service; empty result on absence/failure."""
        if service is None:
            return WorkspaceRetrievalResult(query="")
        try:
            return service.recall(query)
        except Exception:
            return WorkspaceRetrievalResult(query="")

