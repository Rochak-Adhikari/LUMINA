"""
brain/workspace/store.py — Phase 5.6.3: WorkspaceMemoryStore (persistence)

Owns persistence ONLY: load() and save() a WorkspaceMemory to/from a JSON
file. It does not know about the active workspace, ProjectManager, Brain,
Planner, or DI — the caller supplies the target file path.

Format: one human-readable JSON file per workspace (workspace_memory.json).
No SQLite, no database, no pickle.

Writes are atomic: serialize to a .tmp sibling, flush+fsync, then os.replace
onto the real file — never a partial overwrite. Loads never throw: a missing
or corrupt file yields a fresh empty WorkspaceMemory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Union

from brain.workspace.memory import WorkspaceMemory
from brain.workspace.models import (
    ProjectInfo,
    Decision,
    Note,
    WorkspaceTask,
)

_FILENAME = "workspace_memory.json"


class WorkspaceMemoryStore:
    """JSON persistence for WorkspaceMemory — load/save only."""

    filename = _FILENAME

    def _file_path(self, workspace_dir: Union[str, Path]) -> Path:
        return Path(workspace_dir) / self.filename

    # ---- save ---------------------------------------------------------

    def save(self, workspace_dir: Union[str, Path], memory: WorkspaceMemory) -> None:
        """
        Atomically persist *memory* into workspace_dir/workspace_memory.json.

        Serializes the frozen snapshot, writes a .tmp sibling, flushes+fsyncs,
        then os.replace() onto the real file (atomic on the same filesystem).
        """
        path = self._file_path(workspace_dir)
        path.parent.mkdir(parents=True, exist_ok=True)

        snap = memory.snapshot()
        payload = snap.model_dump()  # JSON-native dict (frozen models → data)
        text = json.dumps(payload, indent=2, ensure_ascii=False)

        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic rename

    # ---- load ---------------------------------------------------------

    def load(self, workspace_dir: Union[str, Path]) -> WorkspaceMemory:
        """
        Load a WorkspaceMemory from workspace_dir/workspace_memory.json.

        Never throws: a missing file or invalid/corrupt JSON returns a fresh
        empty WorkspaceMemory (labelled with the directory name). Insertion
        order of records is preserved.
        """
        path = self._file_path(workspace_dir)
        workspace_name = Path(workspace_dir).name

        if not path.exists():
            return WorkspaceMemory(workspace_name)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return WorkspaceMemory(workspace_name)
        except (json.JSONDecodeError, ValueError, OSError):
            return WorkspaceMemory(workspace_name)

        return self._hydrate(data, workspace_name)

    # ---- internal -----------------------------------------------------

    def _hydrate(self, data: dict, fallback_name: str) -> WorkspaceMemory:
        """Rebuild a WorkspaceMemory from a parsed dict; skip malformed records."""
        workspace = data.get("workspace") or fallback_name
        mem = WorkspaceMemory(workspace)

        info = data.get("info")
        if isinstance(info, dict):
            try:
                mem.set_project_info(ProjectInfo(**info))
            except Exception:
                pass

        for rec in data.get("decisions") or []:
            if isinstance(rec, dict):
                try:
                    mem.add_decision(Decision(**rec))
                except Exception:
                    pass

        for rec in data.get("notes") or []:
            if isinstance(rec, dict):
                try:
                    mem.add_note(Note(**rec))
                except Exception:
                    pass

        for rec in data.get("tasks") or []:
            if isinstance(rec, dict):
                try:
                    mem.add_task(WorkspaceTask(**rec))
                except Exception:
                    pass

        return mem
