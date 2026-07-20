# Lumina

<p align="center">
  <img src="assets/logo.png" alt="Lumina Logo" width="180"/>
</p>

<p align="center">
  <strong>A modular, extensible desktop AI assistant built with Electron, React, FastAPI, and Python.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-active-success" />
  <img src="https://img.shields.io/badge/python-3.12-blue" />
  <img src="https://img.shields.io/badge/electron-latest-47848F" />
  <img src="https://img.shields.io/badge/react-19-61DAFB" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
</p>

---

## Overview

Lumina is an AI desktop assistant focused on modular architecture, local execution, extensibility, and real-world productivity.

Unlike traditional chatbot applications, Lumina combines conversational AI with desktop automation, browser interaction, memory, voice, and developer tooling through a clean service-oriented architecture.

The project is currently undergoing a major architectural refactor to make future development faster, safer, and easier to extend.

---

# Features

### AI Conversation

- Natural language conversations
- Streaming responses
- Persona system
- Long-term memory
- Context-aware conversations

### Voice

- Speech-to-text
- Text-to-speech
- Voice Activity Detection (VAD)
- Continuous conversation mode

### Desktop Automation

- Browser automation
- Desktop control
- Application launching
- File processing
- Developer tools
- Reminder system

### Memory

- Long-term memory
- Memory lifecycle management
- Hybrid semantic search
- Memory approval workflow

### Workspace Reasoning

Per-project structured memory with a read-only, deterministic recall layer that
feeds planning and prompting:

- Workspace Memory (structured per-project records)
- Workspace Retrieval (deterministic, memory-only retriever)
- Decision Recall
- Notes Recall
- Task Recall
- Architecture Recall
- WorkspaceRecallContext (frozen recall container)
- PromptWorkspaceContext (frozen prompt-safe projection)
- Prompt Builder (workspace prompt formatting)
- Workspace-aware Planning
- Workspace-aware Prompting

Retrieval happens exactly once, in ContextBuilder — the sole enrichment point.
Planners and prompt builders never retrieve. See
`Docs/TRUTH/adr/ADR-0007-workspace-context-boundary.md`.

### Architecture

- Dependency Injection
- Event Bus
- Runtime Context
- Session Manager
- Service Container
- Modular interfaces
- Extensible pipeline

---

# Technology Stack

## Frontend

- React 19
- Electron
- Vite
- TypeScript

## Backend

- FastAPI
- Python 3.12
- AsyncIO

## AI

- OpenAI Compatible APIs
- Memory Engine
- Tool Calling
- Voice Pipeline

---

# Project Structure

```
backend/
│
├── brain/
│   ├── events.py
│   ├── state.py
│   └── ...
│
├── core/
│   ├── application.py
│   ├── bootstrap.py
│   ├── container.py
│   ├── interfaces.py
│   ├── pipeline.py
│   ├── runtime_facade.py
│   ├── services.py
│   └── ...
│
├── server.py
└── lumina.py

frontend/

docs/

workspace/
```

---

# Architecture

The new architecture is centered around several core systems:

- Dependency Injection Container
- Runtime Facade
- Event Bus
- Brain State Manager
- Session Manager
- Middleware Pipeline
- Service Accessor Layer
- Validation Layer

Documentation:

- `Docs/04_Guides/FEATURE_GUIDE.md` — how every feature works
- `Docs/TRUTH/ENGINEERING_ROADMAP.md` — authoritative engineering roadmap
- `Docs/TRUTH/ROADMAP.md` — long-term product vision
- `Docs/TRUTH/ARCHITECTURE.md` — architecture overview
- `Docs/TRUTH/adr/` — architecture decision records (ADR-0007, ADR-0008)
- `Docs/02_Development/PHASE_HISTORY.md` — completed phase history
- `Docs/02_Development/CURRENT_STATUS.md` — current status

---

# Getting Started

## Clone

```bash
git clone https://github.com/Rochak-Adhikari/LUMINA.git

cd LUMINA
```

---

## Backend

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Frontend

```bash
npm install
```

---

## Environment

Create a `.env` file and configure the required API keys.

Example:

```env
OPENAI_API_KEY=

OPENAI_BASE_URL=

MODEL=
```

---

## Run

Backend

```bash
python backend/server.py
```

Frontend

```bash
npm run dev
```

Electron

```bash
npm run electron
```

---

# Current Architecture Progress

## Phases 1–4 — Runtime Foundation

- Dependency Injection, Context System, Session Layer, Bootstrap
- Brain State, Event System, Runtime Pipeline
- Interface Extraction, Service Accessors, Runtime Facade
- Stable Runtime Recovery (port scan, graceful shutdown, settings self-heal)

Completed / Frozen

---

## Phase 5 — Cognitive Architecture

- BrainCore orchestrator + frozen value objects
- Planning (RulePlanner / LLMPlanner / PlannerChain) + Skills
- Capability Layer
- Workspace Memory + Workspace Activation
- Reflection Engine
- Workspace Reasoning (retrieval → planning → prompting)

Completed / Frozen

---

## Phase 6 — Evolution Engine

Analysis-only, fully dormant (never mutates runtime):

- Reflection Learning, Strategy Improvement, Performance Analysis
- Memory Consolidation, Self Evolution (Recommendation Engine)
- Validation & Freeze

Completed · Validated · Frozen

---

## Phase 7 — Skill Creator

Deterministic 10-stage compiler pipeline (all stages dormant in DI):

- Builder → Verifier → Generator → Tester → Approver (human gate)
- Installer → Registry → Lifecycle → Marketplace → Rollback

Turns an approved evolution recommendation into an installed, registered skill;
each stage produces one frozen immutable artifact. See `Docs/TRUTH/pipeline/*`
and ADR-0009–0013.

Completed · Validated · Frozen

---

# Roadmap

- Phase 8 — Skill Runtime (consume RegistryEntry to use created skills) / Autonomous Planning
- Plugin system, multi-agent workflows, local LLM support, advanced memory graph

See `Docs/04_Guides/FEATURE_GUIDE.md` for how every shipped feature works, and
`Docs/TRUTH/ENGINEERING_ROADMAP.md` for the authoritative roadmap.

---

# Contributing

Contributions are welcome.

1. Fork the repository

2. Create a feature branch

```bash
git checkout -b feature/my-feature
```

3. Commit

```bash
git commit -m "feat: add feature"
```

4. Push

```bash
git push origin feature/my-feature
```

5. Open a Pull Request

---

# License

This project is licensed under the MIT License.

See the LICENSE file for details.

---

# Acknowledgements

Lumina builds upon ideas and inspiration from numerous open-source AI assistant projects and the broader AI developer community.

Special thanks to all contributors and open-source maintainers whose work has helped shape this project.

---

<p align="center">
Made with ❤️ by the Lumina Contributors
</p>
