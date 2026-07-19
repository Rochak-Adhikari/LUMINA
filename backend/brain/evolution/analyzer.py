"""
brain/evolution/analyzer.py — Phase 6.3: PerformanceAnalyzer

Deterministic performance measurement (ADR-0008). Consumes ONLY a
StrategyAnalysis (the previous layer's output) and produces an immutable
PerformanceAnalysis. NEVER reads Reflection, EvolutionObservation, or
EvolutionStore — every layer consumes only the output of the previous one.

Measurement only: reports aggregate execution quality (reliability, failure
ratio, consistency, stability, efficiency, best/worst strategy). It recommends
nothing, decides no evolution, and mutates nothing (the input StrategyAnalysis
is frozen and left untouched).

Deterministic — pure function of the input: no UUID, no random, no internally
generated timestamps. Same StrategyAnalysis in → byte-identical
PerformanceAnalysis out.
"""

from __future__ import annotations

from typing import List, Optional

from brain.evolution.interfaces import IPerformanceAnalyzer
from brain.evolution.models import StrategyAnalysis, PerformanceAnalysis


class PerformanceAnalyzer(IPerformanceAnalyzer):
    """Deterministic performance metrics over a StrategyAnalysis."""

    def analyze(self, strategy_analysis: StrategyAnalysis) -> PerformanceAnalysis:
        stats = list(strategy_analysis.per_strategy)

        reliability = strategy_analysis.overall_success_rate
        failure_ratio = 1.0 - reliability if stats else 0.0

        if not stats:
            return PerformanceAnalysis(
                strategies_measured=0,
                reliability=reliability,
                failure_ratio=0.0,
                consistency=0.0,
                stability=0.0,
                efficiency=None,
                best_strategy="",
                worst_strategy="",
            )

        rates = [s.success_rate for s in stats]
        # consistency: 1 - spread of per-strategy success rates (0..1).
        consistency = 1.0 - (max(rates) - min(rates))
        # stability: weakest per-strategy success rate.
        stability = min(rates)

        # efficiency: mean latency across strategies that reported one.
        latencies = [
            s.average_latency for s in stats if s.average_latency is not None
        ]
        efficiency: Optional[float] = (
            sum(latencies) / len(latencies) if latencies else None
        )

        # best / worst by success rate; deterministic first-seen tie-break.
        best = stats[0]
        worst = stats[0]
        for s in stats[1:]:
            if s.success_rate > best.success_rate:
                best = s
            if s.success_rate < worst.success_rate:
                worst = s

        return PerformanceAnalysis(
            strategies_measured=len(stats),
            reliability=reliability,
            failure_ratio=failure_ratio,
            consistency=consistency,
            stability=stability,
            efficiency=efficiency,
            best_strategy=best.strategy,
            worst_strategy=worst.strategy,
        )
