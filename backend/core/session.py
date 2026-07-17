"""
core/session.py — Lumina V2 Session Lifecycle Manager (Phase 3)

Centralizes ownership of the AudioLoop reference that was previously a
module-level global in server.py.  SessionManager does NOT construct
AudioLoop — that responsibility stays with the start_audio() handler —
but it provides a thread-safe, typed interface for all code that needs
to read or mutate the active session.

This module:
  - Holds the single AudioLoop reference
  - Synchronizes session state with BrainState on attach/detach
  - Publishes lifecycle events to EventBus
  - Provides typed accessors for sub-services (memory_store, project_manager)
    so callers stop reaching through audio_loop.X

Design decisions:
  - NOT a replacement for AudioLoop — it is a wrapper that owns the reference
  - Thread-safe: a threading.Lock guards attach/detach mutations
  - Additive: existing code that accesses the raw AudioLoop reference
    continues to work unchanged during incremental migration
"""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from core.interfaces import IBrainState, IEventBus


class SessionManager:
    """
    Owns the active AudioLoop session reference and lifecycle coordination.

    Typical lifecycle:
        1. sm = SessionManager(brain_state, event_bus)
        2. sm.attach(audio_loop)       # called from start_audio()
        3. sm.audio_loop               # typed access from handlers
        4. sm.detach()                  # called from stop_audio() / shutdown

    The manager synchronizes with BrainState on attach/detach and
    publishes lifecycle events to EventBus.
    """

    def __init__(
        self,
        brain_state: IBrainState,
        event_bus: IEventBus,
    ) -> None:
        self._brain_state = brain_state
        self._event_bus = event_bus
        self._lock = threading.Lock()
        self._audio_loop: Any = None
        self._attached_at: Optional[float] = None
        # Phase 4.3: SessionManager additionally owns the asyncio task running
        # AudioLoop.run() and the FaceAuthenticator reference (previously
        # module-level globals in server.py).
        self._loop_task: Any = None
        self._authenticator: Any = None

    # ------------------------------------------------------------------
    # Lifecycle API
    # ------------------------------------------------------------------

    def attach(self, audio_loop: Any) -> None:
        """
        Attach a newly constructed AudioLoop to this manager.

        Updates BrainState session info and publishes
        'session.audio_attached' to EventBus (sync).
        """
        with self._lock:
            self._audio_loop = audio_loop
            self._attached_at = time.time()

        # Sync with BrainState
        try:
            with self._brain_state.transaction() as draft:
                draft.connected_at = self._attached_at
        except Exception as e:
            print(f"[SessionManager] BrainState sync on attach failed (non-fatal): {e}")

        # Publish lifecycle event
        try:
            self._event_bus.publish_sync("session.audio_attached", {
                "attached_at": self._attached_at,
            })
        except Exception as e:
            print(f"[SessionManager] EventBus publish on attach failed (non-fatal): {e}")

        print(f"[SessionManager] AudioLoop attached at ts={self._attached_at:.1f}")

    def detach(self) -> None:
        """
        Detach the current AudioLoop and clear the session reference.

        Updates BrainState and publishes 'session.audio_detached' event.
        """
        was_attached = False
        with self._lock:
            if self._audio_loop is not None:
                was_attached = True
                self._audio_loop = None
                self._attached_at = None

        if was_attached:
            # Sync with BrainState
            try:
                self._brain_state.reset_session()
            except Exception as e:
                print(f"[SessionManager] BrainState reset on detach failed (non-fatal): {e}")

            # Publish lifecycle event
            try:
                self._event_bus.publish_sync("session.audio_detached", {
                    "detached_at": time.time(),
                })
            except Exception as e:
                print(f"[SessionManager] EventBus publish on detach failed (non-fatal): {e}")

            print("[SessionManager] AudioLoop detached")

    # ------------------------------------------------------------------
    # Read-only accessors
    # ------------------------------------------------------------------

    @property
    def audio_loop(self) -> Any:
        """
        Return the current AudioLoop instance, or None if not attached.

        Thread-safe read — no lock needed for simple reference read on CPython
        (GIL guarantees atomic pointer reads).
        """
        return self._audio_loop

    @property
    def is_active(self) -> bool:
        """True if an AudioLoop is currently attached."""
        return self._audio_loop is not None

    # ------------------------------------------------------------------
    # Phase 4.3: loop task + authenticator ownership
    # ------------------------------------------------------------------

    @property
    def loop_task(self) -> Any:
        """Return the asyncio.Task running AudioLoop.run(), or None."""
        return self._loop_task

    def set_loop_task(self, task: Any) -> None:
        """Store (or clear, with None) the asyncio.Task running AudioLoop.run().

        SessionManager only owns the reference — cancellation remains an
        explicit caller decision so existing shutdown ordering is unchanged.
        """
        with self._lock:
            self._loop_task = task

    @property
    def authenticator(self) -> Any:
        """Return the FaceAuthenticator instance, or None."""
        return self._authenticator

    def set_authenticator(self, authenticator: Any) -> None:
        """Store (or clear, with None) the FaceAuthenticator reference."""
        with self._lock:
            self._authenticator = authenticator

    @property
    def attached_at(self) -> Optional[float]:
        """Unix timestamp when the current AudioLoop was attached."""
        return self._attached_at

    # ------------------------------------------------------------------
    # Sub-service accessors (convenience properties)
    # ------------------------------------------------------------------

    @property
    def memory_store(self) -> Any:
        """Return the memory store from the active AudioLoop, or None."""
        loop = self._audio_loop
        if loop is not None:
            return getattr(loop, 'memory_store', None)
        return None

    @property
    def project_manager(self) -> Any:
        """Return the project manager from the active AudioLoop, or None."""
        loop = self._audio_loop
        if loop is not None:
            return getattr(loop, 'project_manager', None)
        return None

    @property
    def session(self) -> Any:
        """Return the Gemini session from the active AudioLoop, or None."""
        loop = self._audio_loop
        if loop is not None:
            return getattr(loop, 'session', None)
        return None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return diagnostic status dict."""
        loop = self._audio_loop
        return {
            "is_active": loop is not None,
            "attached_at": self._attached_at,
            "has_memory_store": self.memory_store is not None,
            "has_project_manager": self.project_manager is not None,
            "has_gemini_session": self.session is not None,
            "has_loop_task": self._loop_task is not None,
            "has_authenticator": self._authenticator is not None,
        }
