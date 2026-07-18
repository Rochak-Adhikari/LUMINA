# Verification Cache

Status: Active

The following files have already been verified during Phase 5.4.

Unless the user explicitly states they changed,

DO NOT read them again.

---

## Architecture

docs/architecture/README.md

docs/architecture/01_CURRENT_ARCHITECTURE.md

docs/architecture/02_ARCHITECTURE_ANALYSIS.md

docs/architecture/03_REFACTORING_PLAN.md

docs/architecture/04_V3_ARCHITECTURE.md

docs/architecture/05_IMPLEMENTATION_ROADMAP.md

docs/architecture/06_FUTURE_FEATURES.md

---

## Truth

Docs/TRUTH/

---

## Verified Runtime

backend/server.py

backend/lumina.py

backend/core/bootstrap.py

backend/core/runtime_facade.py

backend/brain/skills/builtin.py

---

## Rule

Do not re-read any verified file unless

1. the file changed

2. a modified file directly depends on it

3. the user explicitly requests re-verification

Otherwise assume verification remains valid.

---

## Repository Policy

Never perform full repository scans during implementation.

Read only files directly involved in the current roadmap step.

---

## Goal

Reduce unnecessary repository reads.

Reduce token usage.

Reduce API cost.

Preserve implementation correctness.