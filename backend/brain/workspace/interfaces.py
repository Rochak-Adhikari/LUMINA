"""
brain/workspace/interfaces.py — Phase 5.6.2: WorkspaceMemory contract

IWorkspaceMemory: the structured project-memory contract. Behaviour only —
no persistence, no DI, no filesystem, no knowledge of the active workspace,
ProjectManager, Brain, Planner, or runtime. Those belong to later milestones.

Deterministic: the same sequence of operations always yields the same
snapshot.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from brain.workspace.models import (
    ProjectInfo,
    Decision,
    Note,
    WorkspaceTask,
    WorkspaceSnapshot,
    WorkspaceRetrievalResult,
)


class IWorkspaceMemory(ABC):
    """Structured, in-memory project-memory contract."""

    @abstractmethod
    def set_project_info(self, info: ProjectInfo) -> None:
        """Set (replace) the project info record."""

    @abstractmethod
    def project_info(self) -> Optional[ProjectInfo]:
        """Return the current project info, or None if unset."""

    @abstractmethod
    def add_decision(self, decision: Decision) -> None:
        """Append a decision record."""

    @abstractmethod
    def list_decisions(self) -> List[Decision]:
        """Return decisions in insertion order."""

    @abstractmethod
    def add_note(self, note: Note) -> None:
        """Append a note record."""

    @abstractmethod
    def list_notes(self) -> List[Note]:
        """Return notes in insertion order."""

    @abstractmethod
    def add_task(self, task: WorkspaceTask) -> None:
        """Append a task record."""

    @abstractmethod
    def list_tasks(self) -> List[WorkspaceTask]:
        """Return tasks in insertion order."""

    @abstractmethod
    def snapshot(self) -> WorkspaceSnapshot:
        """Return an immutable WorkspaceSnapshot of the current state."""

    @abstractmethod
    def clear(self) -> None:
        """Reset all records (info, decisions, notes, tasks)."""


class IWorkspaceRetriever(ABC):
    """
    Read-only retrieval contract over the active WorkspaceMemory (Phase 5.9.1).

    Names WHAT it guarantees, not HOW. Guarantees:
      - deterministic: the same memory state + query + filters always yields
        the same result;
      - read-only: retrieval never mutates, persists, or switches anything.

    The retrieval mechanism is an implementation detail (current impl,
    future semantic/graph/hybrid impls) and is intentionally NOT part of this
    contract. One generic method only — no record-type-specific methods.
    Consumers narrow results by supplying opaque ``record_type`` / ``tags``
    filters.
    """

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        record_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> WorkspaceRetrievalResult:
        """
        Return records matching *query* and optional filters, read-only.

        ``record_type`` is an opaque, caller-supplied identifier; the contract
        places no constraint on its values. ``tags`` narrows to records sharing
        the requested tags. None filters impose no constraint.
        """


class IDecisionRecall(ABC):
    """
    Read-only recall of decision records (Phase 5.9.3).

    First consumer of the frozen WorkspaceRetriever. A thin wrapper: it holds
    no retrieval logic of its own, delegating entirely to the retriever with a
    fixed record_type. Deterministic and read-only by virtue of the retriever.
    """

    @abstractmethod
    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Return decision records matching *query*."""


class INotesRecall(ABC):
    """
    Read-only recall of note records (Phase 5.9.4).

    Thin wrapper over the frozen WorkspaceRetriever; no retrieval logic of its
    own. Deterministic and read-only by virtue of the retriever.
    """

    @abstractmethod
    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Return note records matching *query*."""


class ITaskRecall(ABC):
    """
    Read-only recall of task records (Phase 5.9.5).

    Thin wrapper over the frozen WorkspaceRetriever; no retrieval logic of its
    own. Deterministic and read-only by virtue of the retriever.
    """

    @abstractmethod
    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Return task records matching *query*."""


class IArchitectureRecall(ABC):
    """
    Read-only recall of architecture records (Phase 5.9.6).

    Thin wrapper over the frozen WorkspaceRetriever; no retrieval logic of its
    own. Deterministic and read-only by virtue of the retriever.
    """

    @abstractmethod
    def recall(self, query: str) -> WorkspaceRetrievalResult:
        """Return architecture records matching *query*."""
