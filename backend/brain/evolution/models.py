"""
brain/evolution/models.py — Phase 6.1: Evolution observation value object

Frozen, serializable pydantic model. No business logic, no I/O, no runtime
imports — same conventions as brain/core/models.py and brain/workspace/models.py.

Part of the Evolution Engine ANALYSIS layer (ADR-0008). Observation only: this
records what a completed request's Reflection reported. It carries NO runtime,
BrainCore, Workspace, or prompt references — only primitive values.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvolutionObservation(BaseModel):
    """
    Immutable record of one observed Reflection (Phase 6.1).

    Deterministic: built purely from supplied inputs. ``id`` is derived from the
    reflection's identifiers (no UUID generation). ``timestamp`` is caller-
    supplied and never generated inline (determinism rule, ADR-0008).
    Append-only history — never mutated after creation.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    timestamp: Optional[float] = None
    reflection_id: str = ""
    plan_id: Optional[str] = None
    planner_used: str = ""
    strategy_used: str = ""
    success: bool = False
    latency: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StrategyStat(BaseModel):
    """
    Immutable aggregated statistics for one strategy (Phase 6.2).

    Deterministic aggregate over observations sharing ``strategy``. All values
    derived purely from stored observations; no runtime references.
    """

    model_config = ConfigDict(frozen=True)

    strategy: str
    total: int = 0
    successes: int = 0
    failures: int = 0
    success_rate: float = 0.0
    average_latency: Optional[float] = None


class StrategyAnalysis(BaseModel):
    """
    Immutable result of a StrategyEvaluator pass (Phase 6.2).

    A deterministic snapshot: per-strategy stats plus overall totals, computed
    from stored observations only. Analysis, not recommendation — it names no
    action and mutates nothing. ``per_strategy`` is ordered deterministically
    (first-seen strategy order over the observations' insertion order).
    """

    model_config = ConfigDict(frozen=True)

    observations_analyzed: int = 0
    per_strategy: List[StrategyStat] = Field(default_factory=list)
    total_successes: int = 0
    total_failures: int = 0
    overall_success_rate: float = 0.0


class PerformanceAnalysis(BaseModel):
    """
    Immutable performance metrics derived from a StrategyAnalysis (Phase 6.3).

    Measurement only — reports aggregate execution quality. Names no action,
    recommends nothing, decides no evolution. All values computed purely from a
    StrategyAnalysis; no runtime/Reflection/observation references.

    Fields:
      strategies_measured   distinct strategies present.
      reliability           overall success rate (0..1) — how often execution succeeds.
      failure_ratio         overall failure rate (0..1) = 1 - reliability.
      consistency           1 - spread of per-strategy success rates (0..1); 1.0
                            means every strategy performs equally (max consistency).
      stability             lowest per-strategy success rate (0..1) — weakest link.
      efficiency            aggregate mean latency across measured strategies, or
                            None when no latency data was present.
      best_strategy         strategy with the highest success rate (deterministic
                            first-seen tie-break), or "" when none.
      worst_strategy        strategy with the lowest success rate (deterministic
                            first-seen tie-break), or "" when none.
    """

    model_config = ConfigDict(frozen=True)

    strategies_measured: int = 0
    reliability: float = 0.0
    failure_ratio: float = 0.0
    consistency: float = 0.0
    stability: float = 0.0
    efficiency: Optional[float] = None
    best_strategy: str = ""
    worst_strategy: str = ""


class ConsolidationProposal(BaseModel):
    """
    Immutable proposal to consolidate memory records (Phase 6.4).

    A PROPOSAL only — descriptive, never executed. Names a set of memory record
    ids that appear consolidatable (e.g. duplicates) and why. It contains no
    executable logic and performs no write. All values derived purely from a
    read-only memory snapshot; no runtime references.

    ``kind`` is a stable descriptive label ("duplicate" for Phase 6.4).
    ``record_ids`` are the ids of the memory records the proposal concerns,
    in the snapshot's insertion order.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str = "duplicate"
    reason: str = ""
    record_ids: List[str] = Field(default_factory=list)


class ConsolidationProposalSet(BaseModel):
    """
    Immutable set of consolidation proposals (Phase 6.4).

    Deterministic snapshot produced from a read-only memory view. Proposals are
    ordered deterministically (first-seen record order). Descriptive only —
    nothing here mutates memory; the memory store is untouched.
    """

    model_config = ConfigDict(frozen=True)

    records_scanned: int = 0
    proposals: List[ConsolidationProposal] = Field(default_factory=list)
    proposal_count: int = 0


class EvolutionRecommendation(BaseModel):
    """
    Immutable evolution recommendation (Phase 6.5).

    Decides WHAT should evolve — descriptive only. Contains no executable
    logic, no callables, no runtime/Planner/BrainCore/Workspace/Prompt
    references. Phase 7 may consume these later behind approval; Phase 6 never
    acts on them.

    Fields:
      id            deterministic, derived from kind + target (no UUID).
      kind          descriptive label ("improve_strategy", "merge_memory",
                    "retire_memory", "keep_strategy", "observe_more",
                    "review_required", "future_skill_candidate", ...).
      target        the strategy name / memory record group the rec concerns.
      reason        human-readable justification.
      confidence    0..1 deterministic score.
      priority      "low" | "medium" | "high" (descriptive, first-seen tie-break).
      source        which analysis produced it ("performance" | "consolidation").
      related_ids   ids of source records this rec references.
      metadata      primitive-only extra fields.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    target: str = ""
    reason: str = ""
    confidence: float = 0.0
    priority: str = "low"
    source: str = ""
    related_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvolutionRecommendationSet(BaseModel):
    """
    Immutable set of evolution recommendations (Phase 6.5).

    Deterministic snapshot produced from PerformanceAnalysis +
    ConsolidationProposalSet. Recommendations are ordered deterministically
    (performance-derived first, then consolidation-derived; first-seen within
    each). Descriptive only — nothing here mutates or executes.
    """

    model_config = ConfigDict(frozen=True)

    recommendations: List[EvolutionRecommendation] = Field(default_factory=list)
    recommendation_count: int = 0
