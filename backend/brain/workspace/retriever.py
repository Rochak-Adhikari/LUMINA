"""
brain/workspace/retriever.py — Phase 5.9.1: WorkspaceRetriever

Deterministic, READ-ONLY retrieval layer over the active WorkspaceMemory.

The retriever receives WorkspaceMemoryManager by constructor injection and
reads exactly one surface: ``manager.current().snapshot()``. It never touches
private lists, never mutates, saves, switches, activates, persists, and never
imports the store, the sync coordinator, ProjectManager, the Planner,
BrainCore, ContextBuilder, Reflection, or any runtime module.

Phase 5.9 retrieval is intentionally simple and exhaustive. The CURRENT
implementation (not part of the permanent contract) uses:
  - case-insensitive substring matching over each record's text fields
  - exact tag matching (a record sharing any requested tag qualifies)
Future implementations may swap this for semantic / graph / hybrid retrieval
while preserving the same read-only, deterministic interface. No ranking,
relevance scoring, fuzzy/vector/LLM logic exists here.

Determinism: retrieval traverses the WorkspaceSnapshot in a defined sequence
and preserves each record's insertion order, so the same memory state + query
+ filters yields identical output. No randomness, no timestamps, no UUID
generation, no hash-dependent ordering.

The ``record_type`` on each hit is an opaque, caller-facing identifier; this
module places no constraint on the universe of record kinds.

DORMANT: no DI registration, no runtime consumer. Reserved for later 5.9
recall milestones, which build on this by supplying filters — the retriever
itself never changes.
"""

from __future__ import annotations

from typing import Any, List, Optional

from brain.workspace.interfaces import IWorkspaceRetriever
from brain.workspace.models import (
    RetrievalHit,
    WorkspaceRetrievalResult,
)


# Traversal-order record kinds (internal labels for the current impl).
_INFO = "info"
_DECISION = "decision"
_NOTE = "note"
_TASK = "task"


class WorkspaceRetriever(IWorkspaceRetriever):
    """Read-only, deterministic retriever over the active WorkspaceMemory."""

    def __init__(self, manager: Any) -> None:
        # Duck-typed: only manager.current().snapshot() is used. No hard
        # dependency on the concrete WorkspaceMemoryManager type.
        self._manager = manager

    def retrieve(
        self,
        query: str,
        *,
        record_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> WorkspaceRetrievalResult:
        """
        Return records matching *query* and optional filters.

        - ``query``: matched case-insensitively; empty (after trimming) matches
          every record, filters still apply.
        - ``record_type``: opaque caller-supplied kind; None imposes no
          constraint.
        - ``tags``: a record qualifies if it shares at least one tag; None/empty
          imposes no constraint. Records that carry no tags never match when a
          tag filter is supplied.

        Read-only: reads a fresh snapshot each call, mutates nothing. Matching
        strategy below is the current implementation, not part of the contract.
        """
        snapshot = self._manager.current().snapshot()
        # Normalize the query once — never re-lowercase inside the loops.
        needle = query.strip().lower()
        tag_filter = set(tags) if tags else None

        hits: List[RetrievalHit] = []

        # ProjectInfo (single, id-less) — kind "info".
        if self._wants(record_type, _INFO) and snapshot.info is not None:
            info = snapshot.info
            if tag_filter is None and self._text_match(
                needle, info.name, info.description, info.architecture
            ):
                hits.append(
                    RetrievalHit(record_type=_INFO, record_id="", record=info)
                )

        # Decisions — kind "decision" (has tags).
        if self._wants(record_type, _DECISION):
            for d in snapshot.decisions:
                if self._tag_ok(tag_filter, d.tags) and self._text_match(
                    needle, d.title, d.rationale, *d.tags
                ):
                    hits.append(
                        RetrievalHit(
                            record_type=_DECISION, record_id=d.id, record=d
                        )
                    )

        # Notes — kind "note" (has tags).
        if self._wants(record_type, _NOTE):
            for n in snapshot.notes:
                if self._tag_ok(tag_filter, n.tags) and self._text_match(
                    needle, n.title, n.body, *n.tags
                ):
                    hits.append(
                        RetrievalHit(
                            record_type=_NOTE, record_id=n.id, record=n
                        )
                    )

        # Tasks — kind "task" (no tags).
        if self._wants(record_type, _TASK):
            for t in snapshot.tasks:
                if tag_filter is None and self._text_match(
                    needle, t.title, t.status, t.notes
                ):
                    hits.append(
                        RetrievalHit(
                            record_type=_TASK, record_id=t.id, record=t
                        )
                    )

        return WorkspaceRetrievalResult(query=query, hits=hits)

    # ---- helpers (pure) -----------------------------------------------

    @staticmethod
    def _wants(record_type: Optional[str], kind: str) -> bool:
        return record_type is None or record_type == kind

    @staticmethod
    def _text_match(needle: str, *fields: str) -> bool:
        if needle == "":
            return True
        return any(needle in (f or "").lower() for f in fields)

    @staticmethod
    def _tag_ok(tag_filter: Optional[set], record_tags: List[str]) -> bool:
        if tag_filter is None:
            return True
        return bool(tag_filter.intersection(record_tags))
