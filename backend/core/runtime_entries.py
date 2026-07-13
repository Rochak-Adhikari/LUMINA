"""
core/runtime_entries.py — Lumina V2 Runtime Entry Facades (Phase 1.8)

Lightweight entry-point facades that FUTURE phases will use to bridge the
existing Socket.IO server and AudioLoop into the new architecture. They
hold a RuntimeFacade and expose a minimal, typed surface for that future
integration.

IMPORTANT: These are scaffolding only. They are NOT wired into Socket.IO,
AudioLoop, Gemini Live, or any runtime path in this phase. They contain no
event handling, no audio logic, no routing, and no business logic — only a
held reference to RuntimeFacade and accessors for the infrastructure a
future integration will need. No existing runtime code is modified to use
them.
"""

from __future__ import annotations

from core.runtime_facade import RuntimeFacade


class SocketIORuntimeEntry:
    """
    Future integration point for the Socket.IO layer.

    Phase 2+ can construct one of these with a RuntimeFacade and use it to
    reach BrainState / EventBus / pipeline without importing server globals.
    No Socket.IO handlers are registered or modified here.
    """

    def __init__(self, facade: RuntimeFacade) -> None:
        self._facade = facade

    @property
    def facade(self) -> RuntimeFacade:
        return self._facade


class AudioLoopRuntimeEntry:
    """
    Future integration point for the AudioLoop / voice pipeline.

    Phase 2+ can construct one of these with a RuntimeFacade to access
    infrastructure services. No audio, Gemini, or voice-pipeline logic is
    present or modified here.
    """

    def __init__(self, facade: RuntimeFacade) -> None:
        self._facade = facade

    @property
    def facade(self) -> RuntimeFacade:
        return self._facade
