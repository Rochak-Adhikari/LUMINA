"""
brain/workspace/recall.py — Phase 5.9.3–5.9.6: Workspace recall consumers

Thin, read-only wrappers over the frozen WorkspaceRetriever (Phase 5.9.2).
Each recalls a single record kind by delegating to the retriever with a fixed
``record_type``:

  DecisionRecall      -> "decision"   (5.9.3)
  NotesRecall         -> "note"       (5.9.4)
  TaskRecall          -> "task"       (5.9.5)
  ArchitectureRecall  -> "architecture" (5.9.6)

None own retrieval logic: no substring/tag matching, no snapshot iteration, no
WorkspaceMemory / manager / snapshot access. The retriever remains the only
retrieval implementation. Each depends on the retriever interface (duck-typed),
never the concrete class. Deterministic and read-only by virtue of the
retriever they wrap.

Each returns the generic WorkspaceRetrievalResult unchanged — no bespoke result
types. DORMANT: no DI registration, no runtime consumer.
"""

from __future__ import annotations

from typing import Any

from brain.workspace.interfaces import (
    IDecisionRecall,
    INotesRecall,
    ITaskRecall,
    IArchitectureRecall,
)
from brain.workspace.models import WorkspaceRetrievalResult

_DECISION = "decision"
_NOTE = "note"
_TASK = "task"
_ARCHITECTURE = "architecture"


class DecisionRecall(IDecisionRecall):
    """Thin, read-only decision recall over IWorkspaceRetriever."""

    def __init__(self, retriever: Any) -> None:
        # Duck-typed on IWorkspaceRetriever.retrieve; no concrete dependency.
        self._retriever = retriever

    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Delegate to the retriever, narrowed to decision records."""
        return self._retriever.retrieve(query, record_type=_DECISION)


class NotesRecall(INotesRecall):
    """Thin, read-only note recall over IWorkspaceRetriever."""

    def __init__(self, retriever: Any) -> None:
        self._retriever = retriever

    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Delegate to the retriever, narrowed to note records."""
        return self._retriever.retrieve(query, record_type=_NOTE)


class TaskRecall(ITaskRecall):
    """Thin, read-only task recall over IWorkspaceRetriever."""

    def __init__(self, retriever: Any) -> None:
        self._retriever = retriever

    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Delegate to the retriever, narrowed to task records."""
        return self._retriever.retrieve(query, record_type=_TASK)


class ArchitectureRecall(IArchitectureRecall):
    """Thin, read-only architecture recall over IWorkspaceRetriever."""

    def __init__(self, retriever: Any) -> None:
        self._retriever = retriever

    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Delegate to the retriever, narrowed to architecture records."""
        return self._retriever.retrieve(query, record_type=_ARCHITECTURE)
