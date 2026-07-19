"""
brain/evolution/consolidator.py — Phase 6.4: MemoryConsolidator

Read-only memory consolidation PROPOSER (ADR-0008, PHASE_6_ROADMAP). Scans a
memory snapshot (duck-typed) and proposes consolidations — descriptive
ConsolidationProposal records — without ever writing memory.

Reads only: takes an iterable of records supplied by the caller; never imports
WorkspaceMemory, the memory engine, any store, Reflection, Planner, BrainCore,
or runtime. NEVER mutates the records or any store. Proposals contain no
executable logic; Phase 7 may act on them later behind approval.

Deterministic — pure function of the input: no UUID, no timestamps, no
randomness. Duplicate detection groups records by a stable content signature;
groups of 2+ become one "duplicate" proposal, ordered by first-seen record.
Same snapshot in → byte-identical ConsolidationProposalSet out.
"""

from __future__ import annotations

from typing import Any, Dict, List

from brain.evolution.interfaces import IMemoryConsolidator
from brain.evolution.models import ConsolidationProposal, ConsolidationProposalSet


class MemoryConsolidator(IMemoryConsolidator):
    """Deterministic, read-only duplicate-consolidation proposer."""

    def propose(self, records: Any) -> ConsolidationProposalSet:
        items = list(records or [])

        order: List[str] = []              # signature order (first-seen)
        groups: Dict[str, List[str]] = {}  # signature -> record ids

        for record in items:
            signature = self._signature(record)
            record_id = str(self._get(record, "id", ""))
            if signature not in groups:
                order.append(signature)
                groups[signature] = []
            groups[signature].append(record_id)

        proposals: List[ConsolidationProposal] = []
        for signature in order:
            ids = groups[signature]
            if len(ids) < 2:
                continue  # nothing to consolidate
            proposals.append(
                ConsolidationProposal(
                    id=f"consolidate:duplicate:{signature}",
                    kind="duplicate",
                    reason=f"{len(ids)} records share identical content.",
                    record_ids=list(ids),
                )
            )

        return ConsolidationProposalSet(
            records_scanned=len(items),
            proposals=proposals,
            proposal_count=len(proposals),
        )

    # ---- pure helpers -------------------------------------------------

    @staticmethod
    def _get(record: Any, attr: str, default: Any) -> Any:
        if isinstance(record, dict):
            return record.get(attr, default)
        return getattr(record, attr, default)

    def _signature(self, record: Any) -> str:
        """Stable content signature from title + body-like fields (no id)."""
        parts = [
            str(self._get(record, "title", "") or ""),
            str(self._get(record, "body", "") or ""),
            str(self._get(record, "rationale", "") or ""),
            str(self._get(record, "notes", "") or ""),
        ]
        return "|".join(parts)
