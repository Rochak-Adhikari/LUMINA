"""
brain/evolution — LUMINA Evolution Engine (Phase 6.0)

ANALYSIS layer (ADR-0008): observes, measures, analyzes, evaluates, recommends.
It NEVER mutates runtime, rewrites BrainCore/Planner, edits prompts, creates
skills, or changes execution. Phase 6 decides WHAT should evolve; Phase 7
performs the approved evolution.

Phase 6.1 — Reflection Learning (observation only)
--------------------------------------------------
  models.py      EvolutionObservation — frozen observation value object
  interfaces.py  IEvolutionStore, IEvolutionObserver
  store.py       EvolutionStore — in-memory, append-only
  observer.py    EvolutionObserver — Reflection → EvolutionObservation → store

Phase 6.2 — Strategy Improvement (deterministic analysis only)
--------------------------------------------------------------
  models.py      StrategyStat, StrategyAnalysis — frozen analysis value objects
  interfaces.py  IStrategyEvaluator
  evaluator.py   StrategyEvaluator — EvolutionStore → StrategyAnalysis
                 (reads observations only; never Reflection; never mutates)

Phase 6.3 — Performance Analysis (deterministic measurement only)
-----------------------------------------------------------------
  models.py      PerformanceAnalysis — frozen metrics value object
  interfaces.py  IPerformanceAnalyzer
  analyzer.py    PerformanceAnalyzer — StrategyAnalysis → PerformanceAnalysis
                 (consumes StrategyAnalysis only; measures, never recommends)

Phase 6.4 — Memory Consolidation (read-only proposals only)
-----------------------------------------------------------
  models.py       ConsolidationProposal, ConsolidationProposalSet — frozen
  interfaces.py   IMemoryConsolidator
  consolidator.py MemoryConsolidator — memory snapshot → proposals
                  (read-only; never writes memory; descriptive proposals only)

Phase 6.5 — Self Evolution (evolution recommendations only)
-----------------------------------------------------------
  models.py       EvolutionRecommendation, EvolutionRecommendationSet — frozen
  interfaces.py   IRecommendationEngine
  recommender.py  RecommendationEngine — PerformanceAnalysis +
                  ConsolidationProposalSet → EvolutionRecommendationSet
                  (decides WHAT should evolve; never performs evolution)

DORMANT: registered in DI but no runtime path consumes it. Boot is byte-
identical. Recommendations are consumed by Phase 7 later, behind approval.
"""

from brain.evolution.models import (
    EvolutionObservation,
    StrategyStat,
    StrategyAnalysis,
    PerformanceAnalysis,
    ConsolidationProposal,
    ConsolidationProposalSet,
    EvolutionRecommendation,
    EvolutionRecommendationSet,
)
from brain.evolution.interfaces import (
    IEvolutionStore,
    IEvolutionObserver,
    IStrategyEvaluator,
    IPerformanceAnalyzer,
    IMemoryConsolidator,
    IRecommendationEngine,
)
from brain.evolution.store import EvolutionStore
from brain.evolution.observer import EvolutionObserver
from brain.evolution.evaluator import StrategyEvaluator
from brain.evolution.analyzer import PerformanceAnalyzer
from brain.evolution.consolidator import MemoryConsolidator
from brain.evolution.recommender import RecommendationEngine

__all__ = [
    "EvolutionObservation",
    "StrategyStat",
    "StrategyAnalysis",
    "PerformanceAnalysis",
    "ConsolidationProposal",
    "ConsolidationProposalSet",
    "EvolutionRecommendation",
    "EvolutionRecommendationSet",
    "IEvolutionStore",
    "IEvolutionObserver",
    "IStrategyEvaluator",
    "IPerformanceAnalyzer",
    "IMemoryConsolidator",
    "IRecommendationEngine",
    "EvolutionStore",
    "EvolutionObserver",
    "StrategyEvaluator",
    "PerformanceAnalyzer",
    "MemoryConsolidator",
    "RecommendationEngine",
]
