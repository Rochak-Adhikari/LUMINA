"""
brain/skills/sources.py — Phase 5.5 Step 5: skill source constants

A skill's SOURCE is descriptive metadata about where it came from. It lets the
registry accept skills from multiple origins while presenting one unified
SkillMetadata view to the planner. The planner is source-agnostic; the
resolver may read source but must never prefer one over another.

No plugins / MCP / dynamic loading are implemented here — only the vocabulary
the registry tags registrations with.
"""

from __future__ import annotations

# Canonical source identifiers.
BUILTIN = "builtin"
PLUGIN = "plugin"
MCP = "mcp"
GENERATED = "generated"
REMOTE = "remote"

# Default when a registration omits source (preserves existing behavior).
DEFAULT_SOURCE = BUILTIN

KNOWN_SOURCES = (BUILTIN, PLUGIN, MCP, GENERATED, REMOTE)
