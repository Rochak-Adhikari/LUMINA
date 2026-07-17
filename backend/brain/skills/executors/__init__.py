"""
brain/skills/executors — Phase 5.2 executor adapters.

Only LegacyToolExecutor exists in 5.2. Python/MCP/remote executors are
later milestones.
"""

from brain.skills.executors.legacy_tool_executor import LegacyToolExecutor

__all__ = ["LegacyToolExecutor"]
