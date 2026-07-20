# API Reference (REST)

**Date:** 2026-07-20
Source: `backend/server.py`. FastAPI app (`app`). Base URL: `http://localhost:8000`.
Inspected directly from route decorators.

---

## GET `/status`
- **Purpose:** Health check.
- **Request:** none.
- **Response:** `{"status": "running", "service": "Lumina Backend"}`
- **Errors:** none.

## POST `/whatsapp_reply`
- **Purpose:** Generate a Lumina reply for a WhatsApp message.
- **Body:** `{"text": str, "sender": str}` (pydantic `WhatsAppMessage`).
- **Response:** `{"reply": str}`
- **Errors:** returns `{"reply": "..."}` fallback string if `GEMINI_API_KEY` unset or generation fails (no non-200).

## GET `/api/settings/browser-confirmation`
- **Purpose:** Read browser-confirmation mode.
- **Request:** none.
- **Response:** `{"mode": "strict"|"relaxed"|"off"}` (default `"relaxed"`).

## POST `/api/settings/browser-confirmation`
- **Purpose:** Set browser-confirmation mode; persists + emits `settings`.
- **Body:** `{"mode": "strict"|"relaxed"|"off"}`
- **Response:** `{"mode": <mode>}`
- **Errors:** `400 {"error": "Invalid mode: ..."}` for anything else.

## GET `/api/vision/latest`
- **Purpose:** Latest browser screenshot frame from the frame cache.
- **Response:** `{"timestamp", "tab_index", "title", "url", "screenshot_b64"}`
- **Errors:** `{"error": "No frames captured yet"}` (200) when cache empty.

## GET `/local-browser/status`
- **Purpose:** CDP reachability + current tab state.
- **Response:** `{"cdp_reachable": bool, "connected": bool, "tab": <state>|null}`
  (or `{"cdp_reachable": true, "connected": false, "error": ...}`).

## POST `/local-browser/open`
- **Purpose:** Open a URL in the local Brave browser.
- **Body:** `{"url": str}`
- **Response:** browser-control result dict (`{ok, message, data, ...}`).
- **Errors:** `400 {"error": "Missing 'url' field"}`.

## GET `/memory/status`
- **Purpose:** Memory engine status + lifecycle state/type counts.
- **Response:** engine status dict, plus `by_state`, `by_type`, `total_memories` when store available; `{"error": "..."}` if engine uninitialized.

## GET `/memory/search`
- **Purpose:** Hint route — search is POST-only.
- **Response:** `405` with example usage JSON.

## POST `/memory/search`
- **Purpose:** Hybrid (vector + keyword) memory search.
- **Body:** `{"query": str, "top_k": int=8}` (top_k capped at 20).
- **Response:** `{"query", "top_k", "results": [...], "count": int}`
- **Errors:** `503` engine uninitialized; `400` invalid JSON / missing query.

## POST `/memory/reindex`
- **Purpose:** Reindex all memories + transcripts (idempotent).
- **Response:** `{"status": "ok", "counts": {...}}`
- **Errors:** `503` engine uninitialized.

## GET `/memory/pending`
- **Purpose:** List last 20 pending memories with lifecycle fields.
- **Response:** `{"count": int, "memories": [...]}`
- **Errors:** `503` memory store unavailable.

## POST `/memory/confirm`
- **Purpose:** Promote a pending memory to active.
- **Body:** `{"id": int}`
- **Response:** `{"status": "promoted", "id", "new_state": "active"}`
- **Errors:** `503` store unavailable; `400` invalid/missing id; `404` not found/already active.

## POST `/memory/deny`
- **Purpose:** Demote a pending memory to dormant.
- **Body:** `{"id": int}`
- **Response:** `{"status": "demoted", "id", "new_state": "dormant"}`
- **Errors:** `503` store unavailable; `400` invalid/missing id; `404` not found/already dormant.

---

**Total: 13 REST routes** (11 unique paths; `/memory/search` has GET-hint + POST).
Primary realtime channel is Socket.IO (see `SOCKET_EVENTS.md`); REST covers
health, settings, local-browser, vision, and memory lifecycle.
