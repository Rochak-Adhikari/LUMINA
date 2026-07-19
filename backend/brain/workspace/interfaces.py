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
