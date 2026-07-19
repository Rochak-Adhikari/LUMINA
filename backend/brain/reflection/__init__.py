"""
brain/reflection — Lumina Reflection Engine (Phase 5.7)

A read-only, deterministic post-execution evaluator. Given a completed
request (BrainRequest + Plan + skill results + BrainContext), it produces a
Reflection record (the existing value object in brain/core/models.py).

Owns no state. Never executes, mutates, plans, calls an LLM, or writes.
Independent of Planner, SkillManager, Executor, BrainCore, WorkspaceMemory,
ProjectManager, MemoryEngine, and the runtime.

Phase 5.7.2 contents:
  - interfaces.py  IReflectionEngine contract
  - engine.py      ReflectionEngine — pure deterministic evaluator
"""

from brain.reflection.interfaces import IReflectionEngine
from brain.reflection.engine import ReflectionEngine

__all__ = ["IReflectionEngine", "ReflectionEngine"]
