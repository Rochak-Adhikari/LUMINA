"""
brain/evolution/recommender.py — Phase 6.5: RecommendationEngine (Self Evolution)

Decides WHAT should evolve — descriptive recommendations only. Consumes ONLY
the previous analysis layers' immutable outputs: PerformanceAnalysis (6.3) and
ConsolidationProposalSet (6.4). NEVER reads Reflection, EvolutionStore,
WorkspaceMemory, Planner, BrainCore, prompts, or runtime, and NEVER performs
evolution, writes memory, edits prompts, creates skills, or mutates anything.

Deterministic — pure function of the two inputs: no UUID, no timestamps, no
randomness. Recommendation ids derive from kind + target. Ordering is stable
(performance-derived recommendations first in a fixed rule order, then
consolidation-derived in first-seen proposal order). Same inputs → byte-
identical EvolutionRecommendationSet.

Phase 7 may consume these recommendations later behind approval; Phase 6 never
acts on them.
"""

from __future__ import annotations

from typing import List

from brain.evolution.interfaces import IRecommendationEngine
from brain.evolution.models import (
    PerformanceAnalysis,
    ConsolidationProposalSet,
    EvolutionRecommendation,
    EvolutionRecommendationSet,
)

# Deterministic thresholds (fixed constants — no runtime config, no randomness).
_RELIABILITY_MIN = 0.8      # below → improve the worst strategy
_STABILITY_MIN = 0.5        # below → execution unstable, review
_CONSISTENCY_MIN = 0.5      # below → strategy imbalance
_MIN_OBSERVATIONS = 1       # no strategies measured → observe more


class RecommendationEngine(IRecommendationEngine):
    """Deterministic evolution-recommendation producer. Owns no state."""

    def recommend(
        self,
        performance: PerformanceAnalysis,
        consolidation: ConsolidationProposalSet,
    ) -> EvolutionRecommendationSet:
        recs: List[EvolutionRecommendation] = []

        # --- performance-derived (fixed rule order) --------------------
        if performance.strategies_measured < _MIN_OBSERVATIONS:
            recs.append(self._rec(
                kind="observe_more",
                target="",
                reason="No strategies measured yet; gather more observations.",
                confidence=1.0,
                priority="low",
                source="performance",
            ))
        else:
            if performance.reliability < _RELIABILITY_MIN and performance.worst_strategy:
                recs.append(self._rec(
                    kind="improve_strategy",
                    target=performance.worst_strategy,
                    reason=(
                        f"Reliability {performance.reliability:.3f} below "
                        f"threshold {_RELIABILITY_MIN}; weakest strategy "
                        f"'{performance.worst_strategy}'."
                    ),
                    confidence=1.0 - performance.reliability,
                    priority="high",
                    source="performance",
                    related_ids=[performance.worst_strategy],
                ))
            else:
                if performance.best_strategy:
                    recs.append(self._rec(
                        kind="keep_strategy",
                        target=performance.best_strategy,
                        reason=(
                            f"Reliability {performance.reliability:.3f} meets "
                            f"threshold; best strategy '{performance.best_strategy}'."
                        ),
                        confidence=performance.reliability,
                        priority="low",
                        source="performance",
                        related_ids=[performance.best_strategy],
                    ))

            if performance.stability < _STABILITY_MIN:
                recs.append(self._rec(
                    kind="review_required",
                    target="",
                    reason=(
                        f"Stability {performance.stability:.3f} below "
                        f"threshold {_STABILITY_MIN}; execution is unstable."
                    ),
                    confidence=1.0 - performance.stability,
                    priority="high",
                    source="performance",
                ))

            if performance.consistency < _CONSISTENCY_MIN:
                recs.append(self._rec(
                    kind="review_required",
                    target="strategy_balance",
                    reason=(
                        f"Consistency {performance.consistency:.3f} below "
                        f"threshold {_CONSISTENCY_MIN}; strategy imbalance."
                    ),
                    confidence=1.0 - performance.consistency,
                    priority="medium",
                    source="performance",
                ))

        # --- consolidation-derived (first-seen proposal order) ---------
        for proposal in consolidation.proposals:
            recs.append(self._rec(
                kind="merge_memory",
                target=proposal.id,
                reason=proposal.reason or "Duplicate memory records can be merged.",
                confidence=1.0,
                priority="medium",
                source="consolidation",
                related_ids=list(proposal.record_ids),
            ))

        return EvolutionRecommendationSet(
            recommendations=recs,
            recommendation_count=len(recs),
        )

    @staticmethod
    def _rec(
        *,
        kind: str,
        target: str,
        reason: str,
        confidence: float,
        priority: str,
        source: str,
        related_ids: List[str] | None = None,
    ) -> EvolutionRecommendation:
        conf = max(0.0, min(1.0, confidence))
        return EvolutionRecommendation(
            id=f"rec:{kind}:{target}",
            kind=kind,
            target=target,
            reason=reason,
            confidence=conf,
            priority=priority,
            source=source,
            related_ids=list(related_ids or []),
        )
