"""
brain/workspace/manager.py — Phase 5.6.4: WorkspaceMemoryManager

Runtime owner of the CURRENT WorkspaceMemory. A pure coordinator between a
workspace path and the store:

    path → WorkspaceMemoryStore.load(path) → current WorkspaceMemory

It holds no project files, owns no persistence logic (delegates to the store),
performs no filesystem traversal, and knows nothing about ProjectManager, the
Planner, BrainCore, or the runtime. The caller supplies the workspace path;
this manager never resolves it.

Registered in DI as a dormant singleton (5.6.4). No consumer yet.
"""

from __future__ import annotations

from typing import Any, Optional, Union
from pathlib import Path

from brain.workspace.memory import WorkspaceMemory
from brain.workspace.store import WorkspaceMemoryStore


class WorkspaceMemoryManager:
    """Coordinates the active WorkspaceMemory via a store. No globals."""

    def __init__(self, store: Optional[WorkspaceMemoryStore] = None) -> None:
        self._store = store if store is not None else WorkspaceMemoryStore()
        self._current: WorkspaceMemory = WorkspaceMemory()

    def current(self) -> WorkspaceMemory:
        """Return the currently-active WorkspaceMemory (empty until switch)."""
        return self._current

    def save(self, workspace_path: Union[str, Path]) -> None:
        """
        Persist the current WorkspaceMemory to *workspace_path* via the store.

        Used for save-before-switch by the sync coordinator (5.6.6). The path
        is supplied by the caller — this manager never resolves it.
        """
        self._store.save(workspace_path, self._current)

    def switch(self, workspace_path: Union[str, Path]) -> WorkspaceMemory:
        """
        Load the WorkspaceMemory for *workspace_path* via the store and make
        it current. Returns the new current WorkspaceMemory. The store never
        throws (missing/corrupt → fresh empty), so switch is always safe.
        """
        self._current = self._store.load(workspace_path)
        return self._current

    def clear(self) -> None:
        """Reset the current WorkspaceMemory to an empty in-memory instance."""
        self._current = WorkspaceMemory()
