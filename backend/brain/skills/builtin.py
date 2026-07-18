"""
brain/skills/builtin.py — Skill metadata seed (Phase 5.4 Step 0: truth-aligned)

SkillSpec declarations regenerated from the LIVE legacy registries so every
provider_ref names a real, dispatchable tool:

  tier 1 — core.registry.ToolDispatcherRegistry (async handler(fc, loop))
  tier 2 — actions.ACTION_REGISTRY            (sync fn(params, ...) in thread)

Metadata only — no implementations, no imports of registries/agents/tools.
`provider_ref` is the exact registry key a future bound dispatch will target.

NOTE (Phase 5.4 blueprint D1): there is NO memory tool in either registry —
memory verbs are handled inline in server.py's user_input flow. Therefore no
memory SkillSpec exists here; a memory skill arrives only when a real
dispatchable target exists.

The pinning test (tests/test_phase_5_4.py) asserts every provider_ref below
is a member of the union of both live registries.
"""

from __future__ import annotations

from typing import List

from brain.skills.models import SkillSpec
from brain.skills.registry import SkillRegistry

# ---------------------------------------------------------------------------
# Tier 1 — ToolDispatcherRegistry (core/tool_handlers.py)
# ---------------------------------------------------------------------------

_TIER1_SKILLS: List[SkillSpec] = [
    SkillSpec(
        id="legacy.navigate_ui", name="Panel Navigation",
        description="Navigate the Lumina UI to a named panel (quests, archive, "
                    "events, settings, home) with an optional view filter.",
        tags=["navigation", "ui"], permissions=[],
        provider="legacy", provider_ref="navigate_ui",
    ),
    SkillSpec(
        id="legacy.local_browser", name="Local Browser Control",
        description="Open URLs and control the local embedded browser.",
        tags=["browser", "web"], permissions=["local_browser_control"],
        provider="legacy", provider_ref="local_browser_control",
    ),
    SkillSpec(
        id="legacy.browser_control", name="Cloud Browser Control",
        description="Browser automation via the browser_control tool "
                    "(rerouted to local browser when enabled).",
        tags=["browser", "web"], permissions=["browser_control"],
        provider="legacy", provider_ref="browser_control",
    ),
    SkillSpec(
        id="legacy.write_file", name="Write Workspace File",
        description="Write a file inside the active project workspace.",
        tags=["filesystem", "workspace"], permissions=["write_file"],
        provider="legacy", provider_ref="write_file",
    ),
    SkillSpec(
        id="legacy.read_file", name="Read Workspace File",
        description="Read a file from the active project workspace.",
        tags=["filesystem", "workspace"], permissions=["read_file"],
        provider="legacy", provider_ref="read_file",
    ),
    SkillSpec(
        id="legacy.read_directory", name="List Workspace Directory",
        description="List files in the active project workspace.",
        tags=["filesystem", "workspace"], permissions=["read_directory"],
        provider="legacy", provider_ref="read_directory",
    ),
    SkillSpec(
        id="legacy.create_project", name="Create Project",
        description="Create a new project workspace.",
        tags=["workspace"], permissions=["create_project"],
        provider="legacy", provider_ref="create_project",
    ),
    SkillSpec(
        id="legacy.switch_project", name="Switch Project",
        description="Switch the active project workspace.",
        tags=["workspace"], permissions=["switch_project"],
        provider="legacy", provider_ref="switch_project",
    ),
    SkillSpec(
        id="legacy.list_projects", name="List Projects",
        description="List all existing project workspaces.",
        tags=["workspace"], permissions=["list_projects"],
        provider="legacy", provider_ref="list_projects",
    ),
    SkillSpec(
        id="legacy.generate_cad", name="Generate CAD Model",
        description="Generate a new 3D CAD prototype from a text description.",
        tags=["cad", "3d"], permissions=["generate_cad"],
        provider="legacy", provider_ref="generate_cad",
    ),
    SkillSpec(
        id="legacy.iterate_cad", name="Iterate CAD Model",
        description="Apply modifications to the most recent CAD design.",
        tags=["cad", "3d"], permissions=["iterate_cad"],
        provider="legacy", provider_ref="iterate_cad",
    ),
    SkillSpec(
        id="legacy.discover_printers", name="Discover 3D Printers",
        description="Scan the local network for 3D printers.",
        tags=["printer", "3d"], permissions=["discover_printers"],
        provider="legacy", provider_ref="discover_printers",
    ),
    SkillSpec(
        id="legacy.print_stl", name="Print STL",
        description="Slice an STL file and submit it to a 3D printer.",
        tags=["printer", "3d"], permissions=["print_stl"],
        provider="legacy", provider_ref="print_stl",
    ),
    SkillSpec(
        id="legacy.get_print_status", name="Print Status",
        description="Get the current status of a 3D print job.",
        tags=["printer", "3d"], permissions=["get_print_status"],
        provider="legacy", provider_ref="get_print_status",
    ),
    SkillSpec(
        id="legacy.list_smart_devices", name="List Smart Devices",
        description="List discovered TP-Link Kasa smart home devices.",
        tags=["smarthome", "kasa"], permissions=["list_smart_devices"],
        provider="legacy", provider_ref="list_smart_devices",
    ),
    SkillSpec(
        id="legacy.control_light", name="Control Light",
        description="Control TP-Link Kasa lights (on/off/brightness/color).",
        tags=["smarthome", "kasa"], permissions=["control_light"],
        provider="legacy", provider_ref="control_light",
    ),
]

# ---------------------------------------------------------------------------
# Tier 2 — ACTION_REGISTRY (actions/*.py). Initial conservative subset per
# the Phase 5.4 blueprint; remaining action tools can be added as data later.
# ---------------------------------------------------------------------------

_TIER2_SKILLS: List[SkillSpec] = [
    SkillSpec(
        id="legacy.web_search", name="Web Search",
        description="Search the web and return summarized results.",
        tags=["web", "search"], permissions=["web_search"],
        provider="legacy", provider_ref="web_search",
    ),
    SkillSpec(
        id="legacy.weather", name="Weather Report",
        description="Get the current weather report for a location.",
        tags=["weather"], permissions=["weather"],
        provider="legacy", provider_ref="weather",
    ),
    SkillSpec(
        id="legacy.open_app", name="Open Application",
        description="Launch a desktop application by name.",
        tags=["desktop"], permissions=["open_app"],
        provider="legacy", provider_ref="open_app",
    ),
]

BUILTIN_SKILLS: List[SkillSpec] = _TIER1_SKILLS + _TIER2_SKILLS


def seed_registry(registry: SkillRegistry) -> int:
    """Register all builtin SkillSpecs. Returns count registered."""
    for spec in BUILTIN_SKILLS:
        registry.register(spec)
    return len(BUILTIN_SKILLS)
