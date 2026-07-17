"""
brain/skills/builtin.py — Phase 5.2 metadata seed

SkillSpec declarations for capabilities that ALREADY exist in the legacy
runtime. Metadata only — no implementations, no imports of agents/tools.
provider_ref names the legacy capability a future dispatch binding will
target; in 5.2 it is descriptive.
"""

from __future__ import annotations

from typing import List

from brain.skills.models import SkillSpec
from brain.skills.registry import SkillRegistry

BUILTIN_SKILLS: List[SkillSpec] = [
    SkillSpec(
        id="legacy.navigation", name="Panel Navigation",
        description="Navigate the Lumina UI to a named panel or view.",
        tags=["navigation", "ui"], permissions=[],
        provider="legacy", provider_ref="navigate_panel",
    ),
    SkillSpec(
        id="legacy.memory", name="Memory Operations",
        description="Remember, recall, and forget user facts and preferences.",
        tags=["memory"], permissions=["memory"],
        provider="legacy", provider_ref="memory_ops",
    ),
    SkillSpec(
        id="legacy.browser", name="Browser Control",
        description="Open URLs and control the local browser.",
        tags=["browser", "web"], permissions=["browser"],
        provider="legacy", provider_ref="browser_control",
    ),
    SkillSpec(
        id="legacy.filesystem", name="Workspace Files",
        description="Read and write files inside the active project workspace.",
        tags=["filesystem", "workspace"], permissions=["filesystem"],
        provider="legacy", provider_ref="workspace_files",
    ),
    SkillSpec(
        id="legacy.cad", name="CAD Generation",
        description="Generate and iterate 3D CAD prototypes from text.",
        tags=["cad", "3d"], permissions=["cad"],
        provider="legacy", provider_ref="cad_agent",
    ),
    SkillSpec(
        id="legacy.printer", name="3D Printing",
        description="Discover printers, slice STL files, and submit print jobs.",
        tags=["printer", "3d"], permissions=["printer"],
        provider="legacy", provider_ref="printer_agent",
    ),
    SkillSpec(
        id="legacy.kasa", name="Smart Home",
        description="Control TP-Link Kasa smart home devices.",
        tags=["smarthome", "kasa"], permissions=["smart_home"],
        provider="legacy", provider_ref="kasa_agent",
    ),
]


def seed_registry(registry: SkillRegistry) -> int:
    """Register all builtin SkillSpecs. Returns count registered."""
    for spec in BUILTIN_SKILLS:
        registry.register(spec)
    return len(BUILTIN_SKILLS)
