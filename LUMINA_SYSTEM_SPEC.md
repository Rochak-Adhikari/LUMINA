# 🪪 Lumina — Complete System Specification

This document serves as a comprehensive developer reference for updating, modifying, or redesigning Lumina's user interface. It outlines the core persona mechanics, backend socket APIs, voice pipelines, and all 25 interactive capabilities.

---

## 🧠 1. Core Identity & Persona Engine

Lumina is a voice-first, highly adaptive personal companion. She is designed to feel like an equal partner—supportive, witty, and warm.

### 🎭 Persona Modes
Adjustable via the UI (**Settings → Persona**) or dynamically managed in adaptive mode:
*   **Playful Best Friend (`playful_mischievous_best_friend`):** High teasing cap, casual and witty Neplish dialect, frequent use of urban expressions.
*   **Calm & Supportive (`calm_supportive`):** Low teasing intensity, active listening, highly empathetic responses during negative emotion classification.
*   **Professional (`professional`):** Direct, structured, low-tease, and focused entirely on efficiency.

### 🎭 Sentiment & Strict Mode
*   **Emotion Classification:** Classifies Scepter's (user's) input into `neutral`, `excited`, `sad`, `frustrated`, `debating`, `self_sabotage`, or `bored`.
*   **Strict Mode:** Automatically triggers if the user displays continuous negative sentiments or self-sabotaging speech. Directs Lumina to be gentle, present, and direct (no teasing).
*   **Anti-Cringe Safeguards:** Implements a cooldown of 6 turns on pet names, caps teasing intensity dynamically, and enforces natural dialogue structures (no corporate AI disclaimers).

### ⚡ Behavioral Initiative
*   **Idle Check-Ins:** Automatically pings Scepter when he is silent. Follows a multi-stage progression:
    *   *Stage 1:* Soft ping ("Still there?").
    *   *Stage 2:* Helpful/playful suggestion.
    *   *Stage 3+:* Silent standby to avoid spam.
*   **Jealousy System:** Triggers a deterministic, playful reaction if Scepter praises other AI assistants (e.g., ChatGPT, Claude, Alexa).
*   **Singing Mode:** Can sing custom binary/developer-themed songs when requested.

---

## 🎙️ 2. Voice & Live Audio Pipeline

Lumina communicates using real-time bidirectional audio.

*   **API Model:** `models/gemini-2.5-flash-native-audio-preview-12-2025`
*   **Voice Profile:** `Kore` (Clear, firm, expressive female voice).
*   **Language Tone:** Casual Neplish (urban Nepali with fluid English mixing).
*   **Voice Activity Detection (VAD):**
    *   *Min Speech:* 350ms to trigger start.
    *   *Silence Stop:* 900ms of silence closes the user's speaking turn.
    *   *Barge-in:* Instantly cuts off Lumina's synthesized voice output if Scepter starts speaking mid-sentence.

---

## 🛠️ 3. Full Capability Compendium (25 Features)

Lumina's capabilities are registered under `ACTION_REGISTRY` in the backend and map directly to the **Features Compendium** UI:

### 🗣️ Voice & AI
1.  **Real-Time Voice Conversation:** Live bidirectional audio stream with interrupt detection.
2.  **Hybrid Long-Term Memory:** Three-layer retrieval combining FAISS (semantic vectors), SQLite (raw records), and FTS5 (full-text exact match).
3.  **Persona & Emotional Engine:** Dynamic tone, teasing, and behavioral initiatives.
4.  **Face Authentication:** Local MediaPipe landmarks authentication gate via the PC webcam.

### 🔌 Actions & Automation
5.  **Web Search:** Real-time search engine query execution.
6.  **Browser Control:** Playwright-driven headless browser.
7.  **File Processor:** High-level AI analysis of PDFs (summarize), Images (OCR/Q&A), CSVs (stats), Audio (transcribe), and Video (scenes).
8.  **File Controller:** Native file system CRUD (create, read, list, rename, delete files/folders).
9.  **Dev Agent:** Scaffolds multi-file projects, installs npm/pip packages, runs scripts, and self-corrects build errors.
10. **Flight Finder:** Background Google Flights scraper to list cheaper routes.
11. **Game Updater:** Steam and Epic Games library updater and install automation.
12. **Send Messages:** Compose and send messages via WhatsApp, Telegram, or Instagram.
13. **Reminders & Alarms:** Persistent database-backed reminders with screen alarms and custom TTS calls.
14. **Spotify Control:** Controls local desktop playback (play, pause, skip, queue, liked songs).
15. **YouTube Control:** Launches videos, plays playlists, controls volume and skips in Lumina's dedicated browser.

### 💻 System & OS Control
16. **Computer Control:** Simulates mouse cursor clicks, moves, keyboard typing, clipboard copies, and system hotkeys.
17. **Computer Settings:** Adjusts Windows volume, screen brightness, Wi-Fi, power settings, or logs off.
18. **Open Applications:** Launches, focuses, or closes local software (Notepad, VS Code, Discord, etc.).
19. **Screen Processor:** OCR text extraction and image description of your active desktop screen.
20. **Desktop Control:** Minimizes, maximizes, tiles windows, and manages virtual desktops.
21. **Command Line Control:** Executes commands and runs scripts directly inside PowerShell or CMD.

### 🌐 Remote & Creative Interfaces
22. **Remote Phone Dashboard:** A secure mobile-friendly Web interface accessed via your home LAN. Allows voice streaming from a phone microphone, log monitoring, and drag-and-drop file sharing.
23. **WhatsApp Gateway:** Background Playwright listener that runs in Lumina's Brave instance, reads incoming messages from Scepter, passes them to the AI, and types replies back.
24. **CAD Design Agent:** Generates and refines OpenSCAD 3D models from prompts, exports printable STL files.
25. **Smart Home (Kasa) & 3D Printer Control:** Network-level control of TP-Link Kasa smart plugs/lights, andMoonraker/OctoPrint printer status checks.

---

## 🔌 4. Socket.IO API & UI Events

The frontend React client communicates with the backend via bidirectional WebSockets (`socket.io-client` on port `8000`).

### 📥 Emitters (Sent from UI to Backend)
*   `socket.emit('get_settings')` — Requests current configuration (persona, tools permission list, and remote pairing data).
*   `socket.emit('update_settings', data)` — Updates parameters (e.g. `{ persona_mode: 'professional' }`).
*   `socket.emit('revoke_remote_devices')` — Invalidates existing phone tokens.
*   `socket.emit('kill_browser_tools')` — Emergency close for all active Playwright/CDP sessions.
*   `socket.emit('reminder_alarm_dismissed', { event_id: id })` — Dismisses active screen alarm.

### 📤 Listeners (Received by UI from Backend)
*   `socket.on('settings', (payload))` — Hydrates settings panels, tool allowlist toggles, and updates the remote QR code URL (`remote_pairing.qr_url`).
*   `socket.on('audio_data', (bytes))` — Feeds raw PCM audio chunks into the visualizer.
*   `socket.on('transcription', (data))` — Outputs speech-to-text text lines to the chat overlay.
*   `socket.on('browser_frame', (frame))` — Streams frame screenshots to the virtual Browser Window overlay.
*   `socket.on('cad_data', (data))` — Feeds raw geometry data to the 3D canvas renderer.
*   `socket.on('reminder_alarm', (event))` — Activates the fullscreen amber alert screen.
