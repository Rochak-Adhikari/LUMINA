# Lumina V2 HTTP REST API Specification

The Lumina V2 backend runs a FastAPI web application. This document details the HTTP routes, request parameters, and JSON response models.

---

## 1. System Health & Diagnostics

### GET `/health`
- **Description**: Returns the server health status. Used by the Electron launcher to detect backend readiness.
- **Response**:
  ```json
  {"status": "ok", "environment": "lumina"}
  ```

### GET `/debug/events`
- **Description**: Returns a diagnostic summary of all registered EventBus subscribers and wildcard patterns.
- **Response**:
  ```json
  {
    "ok": true,
    "event_bus": {
      "subscription_count": 4,
      "subscriptions": [
        {"token": "abcd1234…", "pattern": "session.*", "is_coro": true}
      ]
    }
  }
  ```

---

## 2. Config & Vision Settings

### POST `/api/settings/browser-confirmation`
- **Description**: Updates the browser confirmation mode.
- **Request Body**:
  ```json
  {"mode": "relaxed"}  // or "strict"
  ```
- **Response**:
  ```json
  {"status": "ok", "mode": "relaxed"}
  ```

### GET `/api/vision/latest`
- **Description**: Returns the base64 encoded screenshot of the latest frame analyzed by the camera/screen processor.
- **Response**:
  ```json
  {"status": "ok", "image": "data:image/jpeg;base64,..."}
  ```

---

## 3. Remote Dashboard REST APIs

These routes are exposed to mobile clients paired via home LAN:

### GET `/api/dashboard/status`
- **Description**: Returns status info of the desktop server (connected clients, active loop status, pairing codes).
- **Response**:
  ```json
  {
    "paired": true,
    "session_active": true,
    "paired_devices": 1
  }
  ```

### POST `/api/dashboard/pair`
- **Description**: Pairs a remote phone device using a temporary token.
- **Request Body**:
  ```json
  {"token": "pairing-uuid-token"}
  ```
- **Response**:
  ```json
  {"paired": true, "device_id": "phone-client-uuid"}
  ```

---

## 4. Passive Memory REST APIs

These endpoints provide admin REST operations over the memory store:

### GET `/memory/status`
- **Description**: Returns database statistics and breakdowns by memory type.
- **Response**:
  ```json
  {
    "total_memories": 6,
    "by_type": {
      "fact": 4,
      "preference": 2
    },
    "database_path": "backend/lumina_memory.db"
  }
  ```

### GET `/memory/pending`
- **Description**: Lists memories currently in a pending state awaiting confirmation.
- **Response**:
  ```json
  [
    {
      "id": 12,
      "type": "fact",
      "content": "User is building a cabinet",
      "created_at": "2026-07-15T10:00:00"
    }
  ]
  ```

### POST `/memory/search`
- **Description**: Runs a search query over the database.
- **Request Body**:
  ```json
  {"query": "Kathmandu", "top_k": 5}
  ```
- **Response**:
  ```json
  [
    {
      "id": 3,
      "type": "fact",
      "content": "User was born in Kathmandu",
      "score": 25.0
    }
  ]
  ```

### POST `/memory/confirm`
- **Description**: Promotes a pending memory suggestion to active status.
- **Request Body**:
  ```json
  {"id": 12}
  ```
- **Response**:
  ```json
  {"status": "confirmed", "id": 12, "new_state": "active"}
  ```

### POST `/memory/deny`
- **Description**: Demotes a pending memory suggestion to dormant/rejected status.
- **Request Body**:
  ```json
  {"id": 12}
  ```
- **Response**:
  ```json
  {"status": "demoted", "id": 12, "new_state": "dormant"}
  ```

### POST `/memory/reindex`
- **Description**: Triggers database reindexing of the FTS index columns.
- **Response**:
  ```json
  {"status": "success"}
  ```
