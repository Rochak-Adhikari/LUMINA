"""brain/__init__.py — Lumina V2 Brain package.

The brain package contains the core cognitive architecture modules.

Current modules:
  state   — BrainState: single thread-safe source of runtime truth
  events  — InProcessEventBus: lightweight in-memory pub/sub

Future modules (later phases):
  planner      — Task decomposition and execution graph
  context      — Short-term working context compilation
  reflection   — Post-turn evaluation and suggestions
  evolution    — Autonomous improvement proposals
"""
