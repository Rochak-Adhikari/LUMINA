"""
brain/workspace/sync.py — Phase 5.6.6: WorkspaceSync coordinator

Bridges ProjectManager (the workspace authority) to WorkspaceMemoryManager
(the follower). ProjectManager decides which workspace is active; this
coordinator observes it and syncs the structured memory:

    save current workspace memory  →  read active path from ProjectManager
                                   →  WorkspaceMemoryManager.switch(path)

Coordination only — no business logic, no filesystem traversal, no project
creation/deletion, no chat/CAD. ProjectManager is NOT imported (duck-typed:
only get_current_project_path() is called), so there is no upward dependency
and ProjectManager stays untouched. WorkspaceMemoryManager never depends on
ProjectManager.

DORMANT in 5.6.6: registered in DI but NOT wired into any runtime switch
path. Activation is a later explicit milestone.
"""

from __future__ import annotations

from typing import Any, Optional
from pathlib import Path

from brain.workspace.manager import WorkspaceMemoryManager
from brain.workspace.memory import WorkspaceMemory


class WorkspaceSync:
    """Follows ProjectManager; keeps WorkspaceMemoryManager in step."""

    def __init__(self, workspace_memory_manager: WorkspaceMemoryManager) -> None:
        self._wsm = workspace_memory_manager
        # Path the current workspace memory belongs to (for save-before-switch).
        self._current_path: Optional[Path] = None

    def sync_to(self, project_manager: Any) -> WorkspaceMemory:
        """
        Sync workspace memory to ProjectManager's active project.

        1. Save the current workspace memory to its path (if known).
        2. Read the active project path from ProjectManager (duck-typed).
        3. Switch WorkspaceMemoryManager to that path.

        Returns the new current WorkspaceMemory. ProjectManager is the source
        of truth; this never selects a workspace itself.
        """
        new_path = Path(project_manager.get_current_project_path())

        # Idempotency: if the requested workspace is already active, do nothing
        # (no re-switch, no re-load, no persistence). Deterministic no-op.
        if self._current_path is not None and self._current_path == new_path:
            return self._wsm.current()

        # 1. Save-before-switch (only if we already track a path and it differs).
        if self._current_path is not None and self._current_path != new_path:
            try:
                self._wsm.save(self._current_path)
            except Exception:
                # Persistence must never break switching.
                pass

        # 2 + 3. Follow ProjectManager to the new workspace.
        memory = self._wsm.switch(new_path)
        self._current_path = new_path
        return memory
