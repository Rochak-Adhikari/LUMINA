"""
brain/evolution/evaluator.py — Phase 6.2: StrategyEvaluator

Deterministic analysis over stored observations (ADR-0008). Consumes ONLY
EvolutionObservation records via the injected EvolutionStore — never reads
Reflection directly, never bypasses the store. Produces an immutable
StrategyAnalysis: per-strategy success/failure aggregates and overall totals.

Analysis only: NO recommendations, NO mutation of the store or observations,
NO runtime/workspace/prompt/planner effect. The store stays append-only and
unchanged. Deterministic — no UUID, no internally-generated timestamps, no
nondeterministic iteration (strategy order follows first-seen insertion order).
"""

from __future__ import annotations

from typing import Dict, List

from brain.evolution.interfaces import IStrategyEvaluator, IEvolutionStore
from brain.evolution.models import StrategyStat, StrategyAnalysis


class StrategyEvaluator(IStrategyEvaluator):
    """Deterministic per-strategy analysis over the observation store."""

    def __init__(self, store: IEvolutionStore) -> None:
        self._store = store

    def evaluate(self) -> StrategyAnalysis:
        observations = self._store.list()  # copy — never mutated

        order: List[str] = []
        totals: Dict[str, int] = {}
        successes: Dict[str, int] = {}
        latency_sums: Dict[str, float] = {}
        latency_counts: Dict[str, int] = {}

        for obs in observations:
            strategy = obs.strategy_used
            if strategy not in totals:
                order.append(strategy)
                totals[strategy] = 0
                successes[strategy] = 0
                latency_sums[strategy] = 0.0
                latency_counts[strategy] = 0
            totals[strategy] += 1
            if obs.success:
                successes[strategy] += 1
            if obs.latency is not None:
                latency_sums[strategy] += obs.latency
                latency_counts[strategy] += 1

        per_strategy: List[StrategyStat] = []
        total_successes = 0
        for strategy in order:
            total = totals[strategy]
            succ = successes[strategy]
            fail = total - succ
            total_successes += succ
            avg_latency = (
                latency_sums[strategy] / latency_counts[strategy]
                if latency_counts[strategy] > 0
                else None
            )
            per_strategy.append(
                StrategyStat(
                    strategy=strategy,
                    total=total,
                    successes=succ,
                    failures=fail,
                    success_rate=(succ / total) if total > 0 else 0.0,
                    average_latency=avg_latency,
                )
            )

        analyzed = len(observations)
        total_failures = analyzed - total_successes
        overall_rate = (total_successes / analyzed) if analyzed > 0 else 0.0

        return StrategyAnalysis(
            observations_analyzed=analyzed,
            per_strategy=per_strategy,
            total_successes=total_successes,
            total_failures=total_failures,
            overall_success_rate=overall_rate,
        )
