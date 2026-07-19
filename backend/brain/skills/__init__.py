"""
brain/skills — Lumina Cognitive Architecture: Skill layer (Phase 5.2)

Phase 5.2 contents:
  - models.py    SkillSpec / SkillResult value objects
  - registry.py  SkillRegistry — metadata storage and discovery only
  - manager.py   SkillManager — task → executor dispatch
  - executors/   Executor adapters (legacy only in 5.2)
  - builtin.py   Metadata seed for existing capabilities

No skill implementations live here — providers point at existing runtime
capabilities via metadata only. Nothing is wired into any runtime path.
"""

from brain.skills.models import SkillSpec, SkillResult
from brain.skills.metadata import SkillMetadata
from brain.skills import sources
from brain.skills.registry import SkillRegistry
from brain.skills.interfaces import ISkillRegistry
from brain.skills.resolver import CapabilityResolver
from brain.skills.manager import SkillManager

__all__ = [
    "SkillSpec", "SkillResult", "SkillMetadata", "sources",
    "SkillRegistry", "ISkillRegistry", "CapabilityResolver", "SkillManager",
]
