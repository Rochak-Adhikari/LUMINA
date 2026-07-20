# API Integration Plan (Frontend → Backend REST)

**Date:** 2026-07-20
Maps frontend surfaces to backend REST endpoints (`API_REFERENCE.md`). Base:
`http://localhost:8000`. Most realtime flows use Socket.IO
(`SOCKET_INTEGRATION_PLAN.md`); REST covers health, settings, browser, vision,
memory lifecycle.

## Mapping

| Frontend surface | REST call | Purpose |
|------------------|-----------|---------|
| App boot / connection status | `GET /status` | Confirm backend alive. |
| System Settings panel — browser confirmation | `GET /api/settings/browser-confirmation` | Load mode. |
| System Settings panel — browser confirmation | `POST /api/settings/browser-confirmation` `{mode}` | Save mode (strict/relaxed/off). |
| Browser Workspace panel — live frame | `GET /api/vision/latest` | Latest screenshot frame. |
| Browser Workspace panel — status | `GET /local-browser/status` | CDP reachable + tab state. |
| Browser Workspace panel — open URL | `POST /local-browser/open` `{url}` | Open URL in local Brave. |
| Memory panel — status/counts | `GET /memory/status` | Engine status + state/type counts. |
| Memory panel — search | `POST /memory/search` `{query, top_k}` | Hybrid search. |
| Memory panel — reindex | `POST /memory/reindex` | Rebuild index. |
| Memory panel — pending list | `GET /memory/pending` | Pending memories. |
| Memory panel — confirm | `POST /memory/confirm` `{id}` | Promote to active. |
| Memory panel — deny | `POST /memory/deny` `{id}` | Demote to dormant. |
| WhatsApp reply feature | `POST /whatsapp_reply` `{text, sender}` | Generate reply. |

## Recommended integration approach

1. **Add a small REST client module** (`src/lib/api.js` — new file, to be created
   during integration) wrapping `fetch` with the `http://localhost:8000` base,
   JSON handling, and error normalization. Currently no REST client exists.
2. Replace any placeholder/hardcoded data in panels with these calls.
3. Handle documented error codes: `400` (bad body), `404` (memory id),
   `405` (GET on search), `503` (memory engine/store unavailable).

## Notes / gaps

- Quests / Events / Archive CRUD are **Socket.IO**, not REST — see
  `SOCKET_INTEGRATION_PLAN.md`.
- No auth headers required (local-first, single-user).
- Electron discovers the actual backend port (8000–8009) if 8000 is occupied;
  the REST client should honor the discovered port rather than assuming 8000 in
  edge cases.
