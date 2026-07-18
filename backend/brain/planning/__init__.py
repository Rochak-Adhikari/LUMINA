"""
brain/planning — Lumina Cognitive Architecture: Planning layer (Phase 5.2)

Contents:
  - rule_planner.py  RulePlanner — deterministic pattern → Plan mapping (5.2).
  - llm_planner.py   LLMPlanner (model-backed, SDK-free via IModelGateway)
                     + PlannerChain (rule-first fallback) (5.3).

Nothing here is wired into any runtime path; registration is DI-only,
access is RuntimeFacade-only.
"""

from brain.planning.rule_planner import RulePlanner
from brain.planning.llm_planner import LLMPlanner, PlannerChain

__all__ = ["RulePlanner", "LLMPlanner", "PlannerChain"]
