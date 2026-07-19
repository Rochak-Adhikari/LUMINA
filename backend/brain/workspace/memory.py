"""
brain/workspace/memory.py — Phase 5.6.2: in-memory WorkspaceMemory

Pure in-memory implementation of IWorkspaceMemory. Holds structured records
(info, decisions, notes, tasks) and produces a frozen WorkspaceSnapshot.

No filesystem, no persistence, no runtime imports, no ProjectManager, no DI,
no singleton. It owns records only — nothing about the active workspace, its
path, or the Brain. Deterministic: records are kept in insertion order.

The workspace *name* is a label carried into the snapshot; this object does
NOT resolve or manage workspaces (that is the manager's job, a later
milestone).
"""

from __future__ import annotations

from typing import List, Optional

from brain.workspace.interfaces import IWorkspaceMemory
from brain.workspace.models import (
    ProjectInfo,
    Decision,
    Note,
    WorkspaceTask,
    WorkspaceSnapshot,
)


class WorkspaceMemory(IWorkspaceMemory):
    """In-memory structured project memory for a single workspace."""

    def __init__(self, workspace: str = "") -> None:
        self._workspace = workspace
        self._info: Optional[ProjectInfo] = None
        self._decisions: List[Decision] = []
        self._notes: List[Note] = []
        self._tasks: List[WorkspaceTask] = []

    # ---- project info -------------------------------------------------

    def set_project_info(self, info: ProjectInfo) -> None:
        self._info = info

    def project_info(self) -> Optional[ProjectInfo]:
        return self._info

    # ---- decisions ----------------------------------------------------

    def add_decision(self, decision: Decision) -> None:
        self._decisions.append(decision)

    def list_decisions(self) -> List[Decision]:
        return list(self._decisions)  # copy — callers can't mutate internals

    # ---- notes --------------------------------------------------------

    def add_note(self, note: Note) -> None:
        self._notes.append(note)

    def list_notes(self) -> List[Note]:
        return list(self._notes)

    # ---- tasks --------------------------------------------------------

    def add_task(self, task: WorkspaceTask) -> None:
        self._tasks.append(task)

    def list_tasks(self) -> List[WorkspaceTask]:
        return list(self._tasks)

    # ---- snapshot / reset ---------------------------------------------

    def snapshot(self) -> WorkspaceSnapshot:
        """Immutable view of the current state (insertion order preserved)."""
        return WorkspaceSnapshot(
            workspace=self._workspace,
            info=self._info,
            decisions=list(self._decisions),
            notes=list(self._notes),
            tasks=list(self._tasks),
        )

    def clear(self) -> None:
        self._info = None
        self._decisions = []
        self._notes = []
        self._tasks = []
