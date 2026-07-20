# Tool Registry

**Date:** 2026-07-20
Inspected live via `Bootstrapper(container).bootstrap()` + registry enumeration.

## Counts

| Registry | Count |
|----------|-------|
| SkillRegistry (`SkillSpec` mirror) | **12** |
| Tier-1 (`ToolDispatcherRegistry`) | **9** |
| Tier-2 (`ACTION_REGISTRY`) | **18** |
| ServiceMetadataRegistry | **11** |

The SkillRegistry mirrors the live legacy registries (ADR-0028): 9 Tier-1 specs
+ 3 Tier-2 specs = 12. The bijection `_TIER1_SKILLS == ToolDispatcherRegistry.keys()`
holds (9 == 9).

## Tier-1 handlers (ToolDispatcherRegistry, `core/tool_handlers.py`)

1. `navigate_ui` — UI panel navigation (DEFER for runtime migration).
2. `write_file` — write workspace file.
3. `read_file` — read workspace file.
4. `read_directory` — list workspace directory.
5. `create_project` — create + switch project.
6. `switch_project` — switch active project (sends context to Gemini session).
7. `list_projects` — list project workspaces.
8. `browser_control` — cloud browser intent (DEFER).
9. `local_browser_control` — local Brave control + confirmation gate (DEFER).

(Removed in Phase 9.0: `generate_cad`, `iterate_cad`, `discover_printers`,
`print_stl`, `get_print_status`, `list_smart_devices`, `control_light`.)

## Tier-2 actions (ACTION_REGISTRY, `actions/*.py`)

`browser_open`, `cmd_control`, `code_helper`, `computer_control`,
`computer_settings`, `desktop_control`, `dev_agent`, `file_controller`,
`file_processor`, `flight_finder`, `game_updater`, `open_app`, `screen_process`,
`send_message`, `spotify_control`, `system_reminder`, `weather`, `web_search`.

## SkillRegistry specs (12)

Tier-1 (9): `legacy.navigate_ui`, `legacy.local_browser`, `legacy.browser_control`,
`legacy.write_file`, `legacy.read_file`, `legacy.read_directory`,
`legacy.create_project`, `legacy.switch_project`, `legacy.list_projects`.

Tier-2 (3): `legacy.web_search`, `legacy.weather`, `legacy.open_app`.

Note: only 3 of 18 Tier-2 actions have SkillSpecs — the metadata catalog is a
deliberate conservative subset (Phase 5.4 blueprint), not full coverage. This is
by design, not a defect.

## ServiceMetadataRegistry (11)

`BrainState`, `EventBus`, `MemoryStore`, `ProjectManager`, `MemoryEngine`,
`ExecutionContextFactory`, `RequestPipeline`, `BrainStateAdapter`,
`EventBusAdapter`, `PipelineAdapter`, `ExecutionContextAdapter`.

## Dormant registries (not runtime-consumed)

- `AgentRegistry`, `ToolRegistry` (`core/registry.py`) — defined, unused.
- Skill Runtime (Phase 8) 13 services + Skill Creator (Phase 7) 10 stages —
  DI-registered, dormant.
