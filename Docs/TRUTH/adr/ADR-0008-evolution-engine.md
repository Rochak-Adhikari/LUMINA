# ADR-0008 — Evolution Engine

**Status:** Proposed (Phase 6.0 blueprint — design only, no implementation)
**Related:** ADR-0007 (Workspace Context Boundary), `Docs/TRUTH/ENGINEERING_ROADMAP.md`
(Phase 6.0 — Evolution Engine), `Docs/TRUTH/PHASE_6_ROADMAP.md`

## Motivation

Improve LUMINA's reasoning quality over time WITHOUT touching the stable
runtime. The frozen core (BrainCore, PlannerChain, ContextBuilder,
WorkspaceMemory, WorkspaceRetriever, Recall, Prompt Builder, RuntimeFacade, DI
Container, EventBus, Execution Pipeline) is authoritative and must not change.

**The Evolution Engine is an analysis layer, NOT a runtime mutation layer.** It
LEARNS FROM the runtime instead of rewriting it. It observes execution outcomes
(via Reflection), analyzes performance, evaluates strategies, and produces
RECOMMENDATIONS and evolved METADATA. It never mutates runtime state, never
rewrites planners, never changes execution. Phase 6 decides WHAT should evolve;
the approved evolution is performed later by Phase 7 (Skill Creator).

## Architecture

An observe → analyze → recommend loop that sits BESIDE the runtime, downstream
of Reflection, and writes only to an isolated evolution store (recommendations
and strategy metadata). Nothing it produces is consumed by the runtime unless a
future, explicitly-approved activation milestone wires it in behind a human
approval gate.

Layers:

1. **Observation** — read-only ingestion of Reflection records + execution
   metrics already emitted by the frozen pipeline.
2. **Analysis** — deterministic aggregation of metrics (success rate, latency,
   failure clustering, skill usage).
3. **Evaluation** — score planning/prompting strategies from observed outcomes.
4. **Recommendation** — emit immutable recommendation records (never applied
   automatically).
5. **Metadata Evolution** — maintain versioned, append-only strategy metadata in
   an isolated store, gated behind human approval.

## Component Responsibilities (design names — not implemented)

- **EvolutionObserver** — read-only collector of Reflection records + metrics.
  Subscribes to existing events / reads existing records; never emits runtime
  events, never mutates.
- **PerformanceAnalyzer** — deterministic metric aggregation over observed
  records. Pure function of its inputs. No I/O beyond the evolution store read.
- **StrategyEvaluator** — scores strategies (planner choice, prompt shape) from
  aggregated metrics. Deterministic. Produces evaluation records only.
- **RecommendationEngine** — converts evaluations into immutable recommendation
  records. Never applies them.
- **MemoryConsolidator** — proposes consolidation of workspace/long-term memory
  (dedup, summarize proposals) as recommendations; NEVER writes to
  WorkspaceMemory or the memory engine directly.
- **EvolutionStore** — isolated, append-only persistence for observations,
  analyses, recommendations, and versioned strategy metadata. Separate from all
  runtime stores.
- **EvolutionEngine** — orchestrates the observe→analyze→evaluate→recommend
  pipeline. Owns no runtime references it can mutate; holds read-only handles.
- **ApprovalGate** (future) — human-in-the-loop checkpoint; only approved
  strategy metadata may ever become runtime-visible, in a later phase.

## Dependency Graph

```
Execution Pipeline        (frozen — emits outcomes)
      ↓
Reflection Engine         (frozen — read-only evaluator)
      ↓
EvolutionObserver         (read-only ingestion)
      ↓
PerformanceAnalyzer       (deterministic aggregation)
      ↓
StrategyEvaluator         (deterministic scoring)
      ↓
RecommendationEngine  +  MemoryConsolidator
      ↓
EvolutionStore            (isolated, append-only)
      ↓
[ApprovalGate — future]   (human approval)
      ↓
Strategy metadata         (versioned; runtime-visible ONLY after approval, later phase)
```

The Evolution Engine NEVER directly changes runtime state. The only path from
evolution output back to the runtime is through the (future) ApprovalGate and
versioned metadata — never a direct write.

## Sequence

```
1. Execution completes            (frozen pipeline)
2. Reflection produced            (frozen ReflectionEngine, read-only)
3. EvolutionObserver ingests      (read-only)
4. PerformanceAnalyzer aggregates (deterministic)
5. StrategyEvaluator scores       (deterministic)
6. RecommendationEngine emits     (immutable recommendation records)
7. EvolutionStore persists        (append-only, isolated)
8. [future] ApprovalGate: human approves/rejects
9. [future] Approved metadata versioned; runtime may read it in a later phase
```

## Design Principles

- Observe, analyze, recommend — never rewrite the runtime.
- The Evolution Engine is an analysis layer, NOT a runtime mutation layer.
- **Evolution recommendations are immutable. Only future approved systems
  (Phase 7 Skill Creator, behind human approval) may consume them.**
- Read-only over all frozen components.
- Deterministic analysis (no hidden randomness; timestamps supplied, not generated inline).
- Append-only evolution records and metadata (versioned, never overwritten).
- Isolated store — no shared mutation with runtime stores.
- Dormant by default — no DI registration, no runtime consumer, until an explicit
  activation milestone.
- Human approval gates any runtime-visible change (future).
- Acyclic dependencies — evolution depends on frozen outputs, never the reverse.

## Allowed Interactions

- READ Reflection records.
- READ execution metrics already emitted.
- READ (not write) workspace/long-term memory for consolidation proposals.
- WRITE to the isolated EvolutionStore only.
- Emit immutable recommendation + evaluation records.

## Forbidden Interactions

- Modifying BrainCore, PlannerChain, ContextBuilder, WorkspaceMemory,
  WorkspaceRetriever, Recall, Prompt Builder, RuntimeFacade, DI Container,
  EventBus, or the Execution Pipeline.
- Writing to any runtime store (workspace memory, memory engine, session state).
- Auto-applying recommendations.
- Emitting runtime events that alter behavior.
- Introducing nondeterminism into analysis.

## Activation Flow

Phases 6.1–6.5 build the engine fully DORMANT: not registered in DI, no runtime
path consumes it, EvolutionStore separate. Runtime stays byte-identical. A later,
explicitly-approved milestone (beyond 6.6) may wire observation on and, behind
the ApprovalGate, allow approved metadata to be read by the runtime. Until then
the engine is inert.

## Dormant Behavior

With nothing registered and nothing consuming it, the engine has zero runtime
effect. Constructing it in isolation (tests) is possible; the live system never
instantiates or calls it during Phases 6.1–6.6.
