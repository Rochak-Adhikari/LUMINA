# 02 · Architecture & Debt Analysis

> **Purpose:** Consolidated assessment of architectural debt, technical debt, coupling, and latent production bugs in the Lumina platform. Combines the standing debt register with the pre-production bug hunt.
> **Status:** Verified against code at **Phase 5.4 Step 0** (2026-07-18).
> **Related:** [01 · Current Architecture](01_CURRENT_ARCHITECTURE.md) · [03 · Refactoring Plan](03_REFACTORING_PLAN.md) · [README](README.md)

---

## Executive Summary

The Lumina foundation is sound: single-owner dependency injection, a unified lifecycle, an acyclic dependency graph, a stateless orchestrator, and interface-mediated access. The debt is concentrated in three areas: a monolithic runtime shell, fragmented session state, and a set of latent runtime bugs in the legacy tool/lifecycle paths that become production-blocking as the Brain is wired in.

This document has two parts:

1. **Debt Register** — architectural and technical debt, code smells, coupling, ranked.
2. **Bug Hunt** — latent runtime defects (races, lifecycle, dispatch edge cases), ranked by severity with evidence.

> [!IMPORTANT]
> No circular imports were found (acyclic verified). No god-object DI container, no test flakiness beyond one timing assertion already resolved.

---

## Part 1 — Debt Register

### Severity Matrix

| # | Issue | Class | Severity | Likelihood | Fix effort |
|---|---|---|---|---|---|
| D1 | `LLMPlanner` uses `asyncio.run()` inside a potential running loop | asyncio | **Critical** | Certain on wiring | Low |
| D2 | `core/__init__` → `tool_handlers` → `google.genai` import chain | arch / DI | **High** | Certain | Low-Med |
| D3 | Confirmation futures leak on session death | leak / race | **High** | Medium | Low |
| D4 | `_pending_text_queue` unbounded + recursive flush | race / leak | **High** | Medium | Low |
| D5 | `server.py` god-module (~3,600 lines, 3 layers fused) | arch | **High** | Certain (drag) | High |
| D6 | RulePlanner emits retired skill ids / wrong param contract | tech | **High** | Certain if wired | Low |
| D7 | Stale AudioLoop / session reference pattern | coupling / race | **High** | Medium | Med |
| D8 | Session state scattered across four homes | ownership | **High** | Certain | Med-High |
| D9 | Navigation intent triple-duplication | duplication | Medium | Certain | Med |
| D10 | Skill layer registered by concrete type, no ABCs | DI | Medium | Grows | Low |
| D11 | Stringly-typed event topics, no constants | smell | Medium | Medium | Low |
| D12 | `sio` object as ad-hoc state carrier | coupling | Medium | Medium | Low-Med |
| D13 | SkillManager permission field decorative | tech / security-adjacent | Medium | Certain at wiring | Low-Med |
| D14 | pytest absent; three test-directory conventions | testing | Medium | Certain | Med |
| D15 | Count-pinned tests brittle (metadata=11, builtin count) | testing | Medium | High | Low |
| D16 | `sys.modules` google mock duplicated per test file | testing / dup | Medium | Certain | Low |
| D17 | Memory DB global — no workspace isolation | arch | Medium | Low today | High |
| D18 | `bootstrapper._app_host` attribute injection | smell | Medium | Low | Med |
| D19 | Tier-2 `to_thread` handlers share mutable `memory_store` | thread safety | Medium | Low-Med | Med |
| D20 | Cross-module attribute reach (`_voice_nav_handled`) | coupling | Medium | Medium | Med |
| D21 | Dual facade accessor styles | smell | Low | Low | Low |
| D22 | ContextBuilder swallows all exceptions silently | smell | Low | Low | Low |
| D23 | ServiceMetadataRegistry describes only pre-5.x world | tech | Low | Low | Low |
| D24 | SIGINT path unverified on real Windows console | testing gap | Low | Low | Low |
| D25 | `PlannerChain` sequential-only; no LLM timeout | scalability | Low | Low today | Low |
| D26 | Background loops lack supervision/restart | reliability | Medium | Low-Med | Med |

### Selected Detail

> [!WARNING]
> **D1 — `asyncio.run()` in LLMPlanner (Critical).** The sync `_generate_sync` path calls `asyncio.run()`, which raises `RuntimeError` inside a running event loop. It passes in tests (no loop) but degrades to **silent planner death** in the server, because the enclosing `try/except` returns `None`. Fix before any wiring (see [03](03_REFACTORING_PLAN.md) Step 3).

**D2 — SDK import chain (High).** `core/__init__` transitively imports the Gemini SDK, inverting dependency direction at the package spine and forcing the `sys.modules` mock ritual in every test. Also the most probable future circular-import seed.

**D5 — `server.py` monolith (High).** 3,600 lines fusing UI transport, session lifecycle, three text dispatch systems, memory lifecycle, and REST. Highest-traffic, least-structured file. **Do not decompose before BrainCore routing is proven** — premature extraction churns the exact lines the refactor must edit.

**D8 — Session state fragmentation (High).** Eight session-scoped facts across four homes (AudioLoop attributes, `sio`, BrainState, module globals). No single reset point; root of an entire bug family and the main obstacle to ContextBuilder enrichment.

---

## Part 2 — Production Bug Hunt

### Bug Severity Matrix

| ID | Issue | Class | Severity | Probability |
|---|---|---|---|---|
| B1 | Tools outside both gate-sets silently dropped; turn stalls | dispatch edge case | **Critical** | High |
| B2 | `stop_audio` kills entire application lifecycle | shutdown | **Critical** | High |
| B3 | Confirmation await blocks tool loop; NameError headless | asyncio / wedge | **Critical** | Med-High |
| B4 | Confirmation futures orphaned on teardown | leak / state | **High** | Medium |
| B5 | `heartbeat`/`idle` task global races → duplicates | race | **High** | Medium |
| B6 | Printer monitor exits permanently / duplicate spawns | resource | **High** | High |
| B7 | Session summary 2s timeout → data loss + abandoned thread | shutdown / data | **High** | Medium |
| B8 | MemoryStore per-call connections, no lock/busy_timeout | DB consistency | **High** | Low-Med |
| B9 | Cross-thread `asyncio.create_task` in callbacks | asyncio / thread | **High** | Medium |
| B10 | `shutdown` socket event never exits uvicorn | shutdown | Medium | High |
| B11 | Recursive `_pending_text_queue` flush unbounded | race / leak | Medium | Medium |
| B12 | `sio._ar_last_ids` grows forever | leak | Medium | Certain |
| B13 | `browser_control` reroute contract fragility | dispatch | Low | Low |
| B15 | Exception swallowing conceals planner/executor faults | observability | Medium | Certain |
| B16 | `connected_clients` dict changed size during iteration | race | Medium | Low-Med |

### Critical Bug Evidence

> [!CAUTION]
> **B1 — Dispatch gate hole (Critical).** In `lumina.py` (~1208–1348) the entire dispatch block (tier-1 at ~1309, tier-2 at ~1326) is nested inside `if fc.name in _ACTION_TOOLS_AUTOCONFIRM or fc.name in _ACTION_TOOL_NAMES:`. `navigate_ui` is a registered tier-1 tool present in **neither** set. A Gemini-issued `navigate_ui` therefore produces no `FunctionResponse` → Gemini waits for a response that never arrives → turn stalls. Masked today only because the text nav fast-path handles most navigation before Gemini.
> **Fix:** separate the allow/deny/confirm decision from dispatch; dispatch runs for all registered names; unknown names get an explicit response. Add a coverage test.

> [!CAUTION]
> **B2 — `stop_audio` disarms lifecycle (Critical).** `stop_audio` calls `_app_host.stop()`, which sets `_started = False` permanently and consumes all cleanup hooks. `start()` is called once at import. A later real shutdown hits `if not self._started: return` and **silently no-ops** — no session summary, no task cancellation.
> **Fix:** `stop_audio` performs session-scoped teardown only; `ApplicationHost.stop()` reserved for process exit.

> [!CAUTION]
> **B3 — Confirmation wedge + headless NameError (Critical).** `confirmed = await future` sits inside the per-function-call loop; an unanswered dialog wedges the turn indefinitely. When `on_tool_confirmation` is absent (headless), `request_id` is only assigned inside `if self.on_tool_confirmation:` while later lines use it → `NameError`.
> **Fix:** `asyncio.wait_for` timeout with deny-on-timeout; create `request_id`/`future` unconditionally.

### Data & Concurrency

**B8 — MemoryStore consistency (High).** Fresh `sqlite3.connect` per method, no shared lock, no `busy_timeout`. Read-modify-write operations (`mark_used`, `promote_memory`) can lose updates across concurrent callers (main-loop CRUD, tier-2 threads, background indexing); concurrent writers can raise `database is locked`. **Fix:** set `busy_timeout`, use in-SQL arithmetic updates, optional single-writer lock.

**B9 — Cross-thread emit (High).** Several `on_*` callbacks invoke `asyncio.create_task(sio.emit(...))`. Callbacks fired from `to_thread` bodies or PyAudio threads have no running loop → `RuntimeError`. **Fix:** `asyncio.run_coroutine_threadsafe` with the main loop captured at `start_audio`, or `sio.start_background_task`.

---

## Dependencies

Analysis draws on: `server.py`, `lumina.py`, `core/application.py`, `core/session.py`, `core/container.py`, `memory_store.py`, `brain/planning/llm_planner.py`, and the two legacy registries.

---

## Risks

- **Silent failure classes** dominate the critical list (B1, B2, D1): green in tests, broken in production. These are the highest-priority because they resist detection.
- **Compounding debt:** the doc/reality gap (TRUTH docs unaware of Phases 5.1–5.4) is the fastest-growing untracked risk.

---

## Recommendations (fix order)

Release-blocking bugs first, then debt that gates the migration:

1. **B1** dispatch gate hole; **B2** shutdown disarm — dedicated hotfix (break current behavior).
2. **D1 / B3** planner asyncio + confirmation wedge — before any wiring.
3. **D2** SDK import removal; **D14–D16** pytest + conftest — cheap multipliers.
4. **B4/B5/B6 + D7/D19** lifecycle & thread-safety — bundle with session bind/unbind milestone.
5. **B8** MemoryStore concurrency hardening.
6. **B10/B11/B12/B16** shutdown exit, queue cap, pruning, dict-copy.
7. Structural: **D8** session consolidation, **D17** workspace isolation, **D5** `server.py` decomposition — last, on a proven Brain path.

See [05 · Implementation Roadmap](05_IMPLEMENTATION_ROADMAP.md) for the consolidated ordering.
