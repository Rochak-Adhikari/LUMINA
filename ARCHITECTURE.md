# Lumina Core Architecture

> **Version**: 2.0.0  
> **Status**: FROZEN  
> **Last Updated**: February 2025

---

## System Identity

| Property | Value |
|----------|-------|
| **Name** | Lumina |
| **Nickname** | Luna |
| **Creator** | Scepter (Rochak Adhikari) |
| **Role** | Long-term AI companion |

**Lumina is NOT:**
- A chatbot
- A tool
- An assistant
- An autonomous agent

**Lumina IS:**
- A conversational companion
- A voice-first AI presence
- A personality with memory of context

---

## Lumina Core Responsibilities

Lumina Core is the central orchestration layer. It is responsible for **conversation flow only**.

### ✅ Lumina Core OWNS

| Responsibility | Description |
|----------------|-------------|
| **Conversation Orchestration** | Managing the flow of dialogue between user and AI |
| **Voice Pipeline Coordination** | Coordinating STT → LLM → TTS handoffs |
| **Persona & Tone Control** | Maintaining consistent personality and language style |
| **Session Context** | Tracking conversation state within a session |
| **LLM Interaction** | Sending prompts and receiving responses from the language model |

### ❌ Lumina Core DOES NOT

| Forbidden Action | Reason |
|------------------|--------|
| Control the OS | Out of scope; violates companion boundary |
| Read/Write/Delete files | No filesystem access |
| Control devices | No hardware interaction |
| Execute tools | Tool execution is disabled |
| Perform autonomous actions | Lumina only responds, never initiates |
| Manage agents | No sub-agent orchestration |

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     LUMINA CORE                         │
│                                                         │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│   │   STT   │ ─► │   LLM   │ ─► │   TTS   │           │
│   │ (Input) │    │(Gemini) │    │(Output) │           │
│   └─────────┘    └─────────┘    └─────────┘           │
│        ▲              │              │                 │
│        │              ▼              ▼                 │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│   │  Mic    │    │ Persona │    │ Speaker │           │
│   │ Stream  │    │ Control │    │ Stream  │           │
│   └─────────┘    └─────────┘    └─────────┘           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Language & Persona Specification

### Primary Language
- **Nepali (ne-NP)** — Modern, casual, conversational

### Style Guidelines
- Sound like a young urban Nepali speaker
- Mix English naturally where appropriate
- Friendly, witty, warm tone
- Companion-like (not formal, not robotic)

### Forbidden Language Patterns
- Formal/academic Nepali
- Literary or Sanskrit-heavy words
- News anchor tone
- Textbook phrasing

### Word Avoidance List
| Avoid (Nepali) | Prefer (English/Simple) |
|----------------|------------------------|
| निर्देशन | direction |
| जटिल | complex |
| अमूल्य | priceless |
| सटीक | precise |
| विसृत | forgotten |

---

## Frozen Components

The following components are **architecturally frozen** and must not be modified without explicit approval:

1. `lumina.py` — Core LLM interaction and audio loop
2. `server.py` — Socket.IO server and session management
3. `App.jsx` — Main UI component
4. Voice pipeline (STT → LLM → TTS)

---

## Change Policy

### Allowed Changes
- Documentation updates
- system_instruction text (persona only)
- UI text/labels (no behavior)
- Bug fixes that restore existing behavior

### Forbidden Changes
- Adding new features
- Adding agents or tools
- Changing API contracts
- Refactoring core logic
- Performance optimizations that alter flow

---

## Versioning

| Version | Description |
|---------|-------------|
| 1.x | Original A.D.A system |
| 2.0.0 | Lumina rebrand, architecture freeze |

---

*This document defines the architectural boundaries of Lumina Core. Any changes that violate these boundaries require explicit review.*
