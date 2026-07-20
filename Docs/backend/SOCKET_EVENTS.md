# Socket.IO Events

**Date:** 2026-07-20
Source: `backend/server.py` (`@sio.event` handlers) + emitted events across
`server.py` / `lumina.py`. Server is `python-socketio` ASGI, mounted with FastAPI.
Client connects to `http://localhost:8000`.

## Incoming events (client → server, `@sio.event`)

| Event | Payload | Purpose |
|-------|---------|---------|
| `hb_pong` | — | Heartbeat reply to server `hb_ping`. |
| `connect` | (auto) | Connection established; auth wiring. |
| `disconnect` | (auto) | Client disconnected; session teardown. |
| `start_audio` | `{device_index?}` | Construct AudioLoop, open Gemini Live session. |
| `stop_audio` | — | Session-scoped unified shutdown. |
| `pause_audio` | — | Mute/pause mic capture. |
| `resume_audio` | — | Resume mic capture. |
| `confirm_tool` | `{id, confirmed}` | Resolve a pending tool-confirmation gate. |
| `shutdown` | `{}` | Full app shutdown (ApplicationHost.stop). |
| `user_input` | `{text}` | Text input into the conversation. |
| `video_frame` | `{data}` | Push a webcam/screen frame. |
| `save_memory` | `{...}` | Persist a memory record. |
| `upload_memory` | `{memory}` | Upload memory text. |
| `process_file` | `{file_path, file_name}` | Process an uploaded file (tier-2 `file_processor`). |
| `prompt_web_agent` | `{prompt}` | Web-agent prompt (web agent disabled in build). |
| `get_settings` | — | Request current SETTINGS → emits `settings`. |
| `update_settings` | `{...}` | Update + persist settings. |
| `revoke_remote_devices` | — | Revoke remote device pairings. |
| `get_tool_permissions` | — | Request tool-permission map. |
| `update_tool_permissions` | `{...}` | Update tool permissions. |
| `kill_browser_tools` | — | Force-stop browser tooling. |
| `list_quests` / `create_quest` / `update_quest` / `delete_quest` | quest dict | Quest CRUD. |
| `list_events` / `create_event` / `update_event` / `delete_event` | event dict | Calendar-event CRUD. |
| `list_archive_notes` / `create_archive_note` / `update_archive_note` / `delete_archive_note` | note dict | Knowledge-archive note CRUD. |
| `reminder_alarm_dismissed` | `{...}` | Dismiss a fired reminder alarm. |
| `memory_decision` | `{...}` | Confirm/deny a memory suggestion. |
| `add_memory` | `{...}` | Add a memory. |
| `get_memories` | `{...?}` | Fetch memories. |
| `get_memory_stats` | — | Memory statistics. |

**39 incoming events.**

## Outgoing events (server → client, `sio.emit`)

| Event | Payload | Purpose |
|-------|---------|---------|
| `hb_ping` | — | Heartbeat ping (client replies `hb_pong`). |
| `connection_status` | `{status}` | Connection state. |
| `model_status` | `{status}` | Gemini Live status (connecting/connected/…). |
| `status` | `{msg}` | Human-readable status line. |
| `error` | `{msg}` | Error message. |
| `settings` | `{...SETTINGS}` | Current settings snapshot. |
| `audio_data` | `{data}` | AI audio chunk (playback). |
| `transcription` | `{...}` | Speech transcription. |
| `chat_message` | `{...}` | Chat message to render. |
| `tool_confirmation_request` | `{id, tool, args}` | Ask user to confirm a gated tool. |
| `project_update` | `{...}` | Active project changed. |
| `navigate_panel` | `{panel, view}` | Voice-driven UI navigation. |
| `reminder_alarm` | `{event}` | Fire a reminder alarm. |
| `memory_lifecycle_event` | `{...}` | Memory state change. |
| `browser_frame` | `{...}` | Browser screenshot/stream frame. |
| `print_status_update` | ~~removed~~ | **No longer emitted (Printer removed).** |
| `cad_data` / `cad_status` / `cad_thought` | ~~removed~~ | **No longer emitted (CAD removed).** Exception: `cad_data` was formerly also emitted by the print_stl path — that path is gone. |
| `kasa_devices` / `kasa_update` | ~~removed~~ | **No longer emitted (Kasa removed).** |

## Integration note (gap)

The current frontend (`src/Ui_TEST/AppTest.jsx`) still **emits**
`discover_kasa` and `discover_printers`, and **listens** for `cad_data`,
`cad_status`, `cad_thought`. The backend no longer registers those incoming
handlers nor emits those outgoing events. See
`docs/frontend/SOCKET_INTEGRATION_PLAN.md` and `PROJECT_CHECKPOINT.md` — these
must be removed/ignored during frontend integration. They are silent no-ops
(Socket.IO drops unhandled emits), not crashes.
