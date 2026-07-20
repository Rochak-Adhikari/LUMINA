# Current Backend State

**Date:** 2026-07-20

## Where development stopped

Backend is at the **final pre-frontend checkpoint**. The last work was the
Phase 9.0 legacy runtime cleanup (removal of Kasa, Printer, CAD). No further
backend work is planned before frontend integration.

## Completed

- **Kasa removed** (9.0.3) — handlers, `KasaAgent`, `ISmartHomeAgent`, DI
  registration, socket handlers, tool decls, specs, tests.
- **Printer removed** (9.0.5) — handlers, `PrinterAgent`, `IPrinterAgent`,
  monitor loop, socket handlers, tool decls, specs, tests.
- **CAD removed** (9.0.6) — handlers, `CadAgent`, `ICadAgent`,
  `handle_cad_request`, socket handlers, tool decls, specs, tests.
- **Runtime verified** — `Bootstrapper.bootstrap()` succeeds; DI resolves;
  registry = 12, Tier-1 = 9, metadata = 11.
- **Tests passing** — 913 (Phase 5 + 6 + 7 + 8).
- **Backend frozen** — Phases 5–8 frozen; runtime core (DI/EventBus/pipeline/
  RuntimeFacade) unchanged.

## Bijection / mirror state

- `_TIER1_SKILLS` (9) == `ToolDispatcherRegistry.keys()` (9). Verified live.
- SkillRegistry count 12 pinned in `test_phase_5_4`, `test_phase_5_6_step4`,
  `test_phase_5_7_step3` (ADR-0028 mirror sync).

## Intentional compatibility shims (not bugs)

- `Bootstrapper.__init__(kasa_agent=None)` — vestigial ignored param (keeps ~20
  frozen Phase-1/4/5 test call sites green).
- `AudioLoop.__init__` params `on_cad_data` / `on_cad_status` / `on_cad_thought`
  / `on_device_update` + `self.cad_agent = None` — vestigial; server still passes
  the callbacks. Harmless.

## Policy

**The backend should not be modified unless a frontend integration bug requires
it.** No cleanup, refactor, or optimization is planned.
