# Socket.IO Integration Plan (Frontend ↔ Backend)

**Date:** 2026-07-20
Maps frontend components to Socket.IO events (`SOCKET_EVENTS.md`). Single
connection: `const socket = io('http://localhost:8000')` in `AppTest.jsx`.

## Emits (frontend → backend)

| Component / action | Emit | Payload |
|--------------------|------|---------|
| Start voice | `start_audio` | `{device_index?}` |
| Stop voice | `stop_audio` | — |
| Mute / unmute | `pause_audio` / `resume_audio` | — |
| Send text | `user_input` | `{text}` |
| Confirm/deny tool | `confirm_tool` | `{id, confirmed}` |
| Heartbeat | `hb_pong` | — |
| App close | `shutdown` | `{}` |
| Load settings | `get_settings` | — |
| Save settings | `update_settings` | `{...}` |
| Tool permissions | `get_tool_permissions` / `update_tool_permissions` | map |
| File upload | `process_file` | `{file_path, file_name}` |
| Memory upload/save/add | `upload_memory` / `save_memory` / `add_memory` | `{...}` |
| Memory fetch/stats | `get_memories` / `get_memory_stats` | `{...?}` |
| Memory decision | `memory_decision` | `{...}` |
| Reminder dismiss | `reminder_alarm_dismissed` | `{...}` |
| Quests panel | `list_quests` / `create_quest` / `update_quest` / `delete_quest` | quest dict |
| Events panel | `list_events` / `create_event` / `update_event` / `delete_event` | event dict |
| Archive panel | `list_archive_notes` / `create_archive_note` / `update_archive_note` / `delete_archive_note` | note dict |
| Browser panel | `kill_browser_tools`, `revoke_remote_devices` | — |
| Web agent | `prompt_web_agent` | `{prompt}` |
| Video frame | `video_frame` | `{data}` |

## Listeners (backend → frontend)

| Component | Listen | Payload | Purpose |
|-----------|--------|---------|---------|
| Connection banner | `connection_status` | `{status}` | Connection state. |
| Status header | `model_status` | `{status}` | Gemini Live state. |
| Status line | `status` | `{msg}` | Human status. |
| Error toast | `error` | `{msg}` | Error. |
| Settings panel | `settings` | `{...}` | Settings snapshot. |
| Visualizer/audio | `audio_data` | `{data}` | AI audio playback. |
| Chat | `transcription`, `chat_message` | `{...}` | Speech + messages. |
| Confirmation popup | `tool_confirmation_request` | `{id, tool, args}` | Gate. |
| Sidebar / project | `project_update` | `{...}` | Active project. |
| Navigation | `navigate_panel` | `{panel, view}` | Voice nav. |
| Reminder overlay | `reminder_alarm` | `{event}` | Fire alarm. |
| Memory prompt | `memory_lifecycle_event` | `{...}` | State change. |
| Browser window | `browser_frame` | `{...}` | Stream frame. |
| Heartbeat | `hb_ping` | — | Reply `hb_pong`. |

## GAPS — remove during integration (backend no longer supports)

| Current frontend code | Action |
|-----------------------|--------|
| `socket.emit('discover_kasa')` | **Remove** — Kasa handler gone. |
| `socket.emit('discover_printers')` | **Remove** — Printer handler gone. |
| `socket.on('cad_data', ...)` | **Remove** — CAD emit gone. |
| `socket.on('cad_status', ...)` | **Remove** — CAD emit gone. |
| `socket.on('cad_thought', ...)` | **Remove** — CAD emit gone. |
| `import CadWindow` + `<CadWindow>` usage | **Remove** — orphaned component. |

These are silent no-ops today (Socket.IO drops unhandled), not crashes, but must
be cleaned to avoid dead UI paths.
