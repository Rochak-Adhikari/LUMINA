# CLAUDE_CONTEXT.md
Version: 1.0
Status: Active
Location: Docs/TRUTH/

---

# Purpose

This document is the onboarding guide for AI coding agents working on Lumina.

It provides the minimum context required before making architectural or implementation decisions.

This document is NOT a specification.

It is a navigation guide.

The repository is always the primary source of truth.

---

# Project

Name:
Lumina

Description:

Lumina is a local-first AI desktop assistant designed to become an AI Operating System rather than a traditional chatbot.

The long-term goal is a modular architecture consisting of:

- Brain
- Memory
- Planner
- Reflection
- Skills
- Workspace
- Personality
- Tools

The core engine should remain stable while capabilities grow through reusable skills and services.

---

# Current Development Phase

Current Phase:

Phase 7 — Skill Creator: ✅ COMPLETE · FROZEN

Next phase: Phase 8 (Skill Runtime — awaiting kickoff)

Completed:

✅ Phase 1 — Runtime Foundation

✅ Phase 2 — Brain Runtime & State

✅ Phase 3 — Interface Refactor & Clean Architecture

✅ Phase 4 — Stable Runtime Recovery (see Docs/Phase_4_Completion_Report.md)

✅ Phase 5 — Cognitive Architecture (BrainCore, Planning, Skills, Workspace Memory, Reflection, Workspace Reasoning) · FROZEN

✅ Phase 6 — Evolution Engine (analysis-only, dormant) · FROZEN

✅ Phase 7 — Skill Creator (10-stage pipeline, dormant) · FROZEN

Future:

Phase 8 — Skill Runtime (consume RegistryEntry to use created skills) / Autonomous Planning

Phase 6 — Planning Engine

---

# Repository Source of Truth

Always read these documents before planning any implementation.

Required reading order:

1.
CURRENT_STATUS.md

Current implementation status.

2.
ROADMAP.md

Milestones and development order.

3.
DEVELOPMENT_RULES.md

Mandatory engineering rules.

4.
LUMINA_MASTER_SPEC.md

Full software design specification.

Ignore all archived documentation unless explicitly requested.

Docs/Archive exists only for historical reference.

---

# Engineering Workflow

Before writing code:

1.
Inspect the repository.

Never assume documentation is fully accurate.

Verify implementation.

2.
Compare implementation with CURRENT_STATUS.md.

3.
Produce:

- Gap Analysis
- Implementation Plan

4.

Wait for approval.

Do NOT implement code until approval is given.

5.

Implement ONE milestone only.

6.

Run or update regression tests.

7.

Update documentation.

8.

Commit.

Repeat.

---

# Architecture Principles

Follow these principles unless the specification explicitly changes them.

- Prefer Dependency Injection over direct construction.

- Prefer RuntimeFacade over direct container access.

- Prefer ServiceAccessor for shared runtime services.

- SessionManager owns AudioLoop lifecycle.

- EventBus should replace callback coupling.

- Avoid introducing new globals.

- Avoid duplicate services.

- Avoid speculative architecture.

- Keep modules loosely coupled.

---

# Current Architectural Goals

Phase 4 is complete — the new architecture is load-bearing:

- ✅ Single MemoryStore instance (DI-registered in Bootstrapper)

- ✅ Legacy runtime paths removed (`_get_memory_store()`, `memory_engine` global, `container.override` in start_audio)

- ✅ AudioLoop dependency injection complete

- ✅ Server globals eliminated (SessionManager ownership)

- ✅ Unified startup/shutdown lifecycle (ApplicationHost cleanup hooks)

- ⏸ Test consolidation deferred (pytest not provisioned in lumina env)

Do NOT begin Phase 8 (Skill Runtime) implementation without explicit approval. Phases 5–7 are complete and frozen — consume them, never redesign.

---

# Documentation Rules

If implementation changes architecture:

Update:

CURRENT_STATUS.md

and

ROADMAP.md

when necessary.

Only modify LUMINA_MASTER_SPEC.md when the architecture itself changes.

Do not rewrite specifications unnecessarily.

---

# Implementation Rules

Every milestone should include:

- Gap Analysis

- Implementation Plan

- Walkthrough

- Regression Tests

- Documentation Update

Do not combine multiple milestones into one large refactor unless explicitly approved.

---

# Coding Guidelines

Prefer:

Small, reviewable commits.

Minimal diffs.

Backward-compatible refactoring.

Maintainable abstractions.

Avoid:

Large rewrites.

Dead code.

Duplicate systems.

Unused abstractions.

Premature optimization.

---

# AI Agent Rules

Never rely on previous conversations.

Treat every session as a fresh repository inspection.

The repository is authoritative.

Documentation guides implementation.

Code verifies documentation.

If documentation and implementation disagree:

Report the discrepancy first.

Do not silently "fix" either one.

Wait for approval.

---

# Success Criteria

A successful milestone:

✓ Leaves the project compiling.

✓ Leaves tests passing.

✓ Updates documentation.

✓ Reduces technical debt.

✓ Preserves architectural consistency.

✓ Is understandable by another AI agent starting from scratch.

---

End of Context