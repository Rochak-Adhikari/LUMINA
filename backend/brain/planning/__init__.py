"""
brain/planning — Lumina Cognitive Architecture: Planning layer (Phase 5.2)

Phase 5.2 contents:
  - rule_planner.py  RulePlanner — deterministic pattern → Plan mapping.

No LLM planner exists yet (Phase 5.3+). Nothing here is wired into any
runtime path; registration is DI-only, access is RuntimeFacade-only.
"""

from brain.planning.rule_planner import RulePlanner

__all__ = ["RulePlanner"]
