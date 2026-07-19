"""
brain/workspace — Lumina Workspace Memory subsystem (Phase 5.6, RELEASE COMPLETE)

Overview
--------
Structured, per-project persistent memory: project info, architecture,
implementation decisions, notes, tasks, and metadata. Switching workspaces
switches the active project memory. Independent of the Planner, SkillManager,
CapabilityResolver, and Executor. It may FOLLOW ProjectManager to locate the
active workspace path; ProjectManager never owns structured memory.

Layer ordering (strict, acyclic — each layer depends only on those above it)
----------------------------------------------------------------------------
  models.py      frozen value objects (ProjectInfo, Decision, Note,
                 WorkspaceTask, WorkspaceSnapshot)
  interfaces.py  IWorkspaceMemory contract
  memory.py      WorkspaceMemory — pure in-memory structured store
  store.py       WorkspaceMemoryStore — JSON persistence (atomic save, safe load)
  manager.py     WorkspaceMemoryManager — runtime owner of the current memory
                 (current / switch / save / clear)
  sync.py        WorkspaceSync — bridges ProjectManager → WorkspaceMemory

Responsibilities
----------------
  WorkspaceMemory        in-memory structured data only (no I/O, no runtime).
  WorkspaceMemoryStore   JSON load/save; caller supplies the path; owns no
                         runtime state; never selects a workspace.
  WorkspaceMemoryManager owns the current WorkspaceMemory; delegates
                         persistence to the store; never imports ProjectManager.
  WorkspaceSync          pure coordinator: save previous, read the active path
                         from ProjectManager (duck-typed), switch. No business
                         logic, no workspace selection, no ProjectManager import.
  ContextBuilder         the ONLY Brain consumer: read-only, snapshot-based,
                         failure-safe enrichment of BrainContext.workspace_ctx.
  ProjectManager         the ONLY workspace/filesystem authority (external to
                         this package; unchanged).

Lifecycle
---------
  Bootstrapper registers WorkspaceMemoryStore, WorkspaceMemoryManager, and
  WorkspaceSync as singletons, and injects the manager into ContextBuilder.
  WorkspaceMemoryManager starts with an empty in-memory WorkspaceMemory.

Dependency rules (enforced; verified by audit)
----------------------------------------------
  - No workspace module imports ProjectManager, the Planner, BrainCore,
    SkillManager, CapabilityResolver, Executor, server, or lumina.
  - No Planner / SkillManager / Resolver / Executor / BrainCore /
    ProjectManager imports this package. ContextBuilder receives the manager
    by injection (typed Any) — no hard import.
  - Acyclic: models → interfaces → memory → store → manager → sync.

Dormant runtime behavior
------------------------
  WorkspaceSync is registered but NOT wired into any runtime switch path.
  No runtime path invokes it; no automatic workspace switching occurs.
  ContextBuilder enrichment is read-only and defaults to the empty current
  workspace. Runtime behavior is identical to before Phase 5.6.

Future extension points (OUT OF SCOPE for Phase 5.6)
----------------------------------------------------
  - Workspace Search — deterministic lookup over WorkspaceMemory records
    (find_note / find_decision / find_task / find_metadata). No AI, no
    embeddings, no vector search. Reserved for a future milestone.
  - Runtime activation — invoking WorkspaceSync from the ProjectManager
    switch path so switching a project switches the active workspace memory.
  - Semantic retrieval / vector indexing / cross-workspace search — future
    phases; explicitly not part of this subsystem.

Public API: the names in __all__ below. Module-level helpers (e.g. id
generation, the persistence filename) are internal.
"""

from brain.workspace.models import (
    ProjectInfo,
    Decision,
    Note,
    WorkspaceTask,
    WorkspaceSnapshot,
)
from brain.workspace.interfaces import IWorkspaceMemory
from brain.workspace.memory import WorkspaceMemory
from brain.workspace.store import WorkspaceMemoryStore
from brain.workspace.manager import WorkspaceMemoryManager
from brain.workspace.sync import WorkspaceSync

__all__ = [
    "ProjectInfo",
    "Decision",
    "Note",
    "WorkspaceTask",
    "WorkspaceSnapshot",
    "IWorkspaceMemory",
    "WorkspaceMemory",
    "WorkspaceMemoryStore",
    "WorkspaceMemoryManager",
    "WorkspaceSync",
]

