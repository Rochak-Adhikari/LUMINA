"""
brain/evolution/interfaces.py — Phase 6.1: Evolution observation contracts

Behaviour-only contracts for the observation layer. No persistence detail, no
DI, no runtime knowledge. Imports only stdlib/typing/abc + evolution models.

IEvolutionStore: append-only persistence of observations.
IEvolutionObserver: converts a Reflection into a stored observation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from brain.evolution.models import (
    EvolutionObservation,
    StrategyAnalysis,
    PerformanceAnalysis,
    ConsolidationProposalSet,
    EvolutionRecommendationSet,
)


class IEvolutionStore(ABC):
    """Append-only store of EvolutionObservation records. No update/delete."""

    @abstractmethod
    def append(self, observation: EvolutionObservation) -> None:
        """Append one observation. Never overwrites an existing record."""

    @abstractmethod
    def get(self, observation_id: str) -> Optional[EvolutionObservation]:
        """Return the observation with *observation_id*, or None."""

    @abstractmethod
    def list(self) -> List[EvolutionObservation]:
        """Return all observations in insertion order (copy)."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored observations."""


class IEvolutionObserver(ABC):
    """Observes a Reflection and persists an immutable observation."""

    @abstractmethod
    def observe(
        self,
        reflection: Any,
        *,
        timestamp: Optional[float] = None,
        planner_used: str = "",
        strategy_used: str = "",
    ) -> EvolutionObservation:
        """Build + store an EvolutionObservation from *reflection*. Read-only
        over the reflection; returns the stored record. Never affects runtime."""


class IStrategyEvaluator(ABC):
    """
    Deterministic analysis over stored observations (Phase 6.2).

    Reads ONLY EvolutionObservation records (from IEvolutionStore); NEVER reads
    Reflection directly and NEVER bypasses the store. Produces an immutable
    StrategyAnalysis. Analysis only — no recommendations, no mutation.
    """

    @abstractmethod
    def evaluate(self) -> StrategyAnalysis:
        """Aggregate stored observations into a StrategyAnalysis. Read-only."""


class IPerformanceAnalyzer(ABC):
    """
    Deterministic performance measurement (Phase 6.3).

    Consumes ONLY a StrategyAnalysis (the previous layer's output). NEVER reads
    Reflection, EvolutionObservation, or EvolutionStore. Produces an immutable
    PerformanceAnalysis. Measurement only — no recommendations, no mutation.
    """

    @abstractmethod
    def analyze(self, strategy_analysis: StrategyAnalysis) -> PerformanceAnalysis:
        """Measure execution quality from *strategy_analysis*. Read-only."""


class IMemoryConsolidator(ABC):
    """
    Read-only memory consolidation proposer (Phase 6.4).

    Reads a memory snapshot (duck-typed: an iterable of records exposing ``id``
    and comparable content) and proposes consolidations (e.g. duplicates) as an
    immutable ConsolidationProposalSet. NEVER writes memory, never mutates any
    store. Proposals are descriptive only — Phase 7 may act on them later.
    """

    @abstractmethod
    def propose(self, records: Any) -> ConsolidationProposalSet:
        """Scan *records* (read-only) and return consolidation proposals."""


class IRecommendationEngine(ABC):
    """
    Deterministic evolution-recommendation producer (Phase 6.5 — Self Evolution).

    Consumes ONLY the previous analysis layers' immutable outputs:
    PerformanceAnalysis (6.3) and ConsolidationProposalSet (6.4). NEVER reads
    Reflection, EvolutionStore, WorkspaceMemory, Planner, BrainCore, prompts, or
    runtime. Decides WHAT should evolve — produces an immutable
    EvolutionRecommendationSet. Never performs evolution.
    """

    @abstractmethod
    def recommend(
        self,
        performance: PerformanceAnalysis,
        consolidation: ConsolidationProposalSet,
    ) -> EvolutionRecommendationSet:
        """Produce evolution recommendations from the two analysis inputs."""
