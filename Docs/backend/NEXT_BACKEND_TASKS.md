# Next Backend Tasks

**Date:** 2026-07-20

## Status: backend work is COMPLETE

No planned backend work remains. The backend is frozen at 913 passing tests,
registry = 12, Tier-1 = 9, metadata = 11.

## Future backend work should happen ONLY if:

1. **Frontend integration reveals a bug** — a concrete defect surfaced while
   wiring the real UI to REST/Socket.IO. Fix the specific defect; do not
   generalize into cleanup.
2. **A new feature is intentionally added** — a deliberate, scoped capability
   (with its own plan/ADR), not incidental improvement.

## Explicitly NOT planned

- No further legacy cleanup.
- No refactoring.
- No renaming of vestigial compatibility shims (documented in
  `CURRENT_BACKEND_STATE.md`).
- No optimization of code that already works.
- No documentation churn beyond correctness.

## If a frontend-integration bug is found

- Reproduce against the live backend (`npm run dev` boots backend on :8000).
- Fix the minimal surface. Re-run `pytest tests/test_phase_5*.py
  tests/test_phase_6*.py tests/test_phase_7*.py tests/test_phase_8*.py`.
- Keep the catalog↔registry bijection and mirror counts synchronized (ADR-0028)
  if tools change.
