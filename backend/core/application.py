"""
core/application.py — Lumina V2 Application Lifecycle Layer (Phase 1.3, 4.5)

ApplicationHost owns the orchestration of application startup and shutdown.
It does NOT construct services itself — that responsibility belongs to
Bootstrapper (core/bootstrap.py).  ApplicationHost only sequences the
lifecycle and exposes read-only access to whatever Bootstrapper registered
into the DI container.

Phase 4.5: ApplicationHost.stop() coordinates graceful resource cleanup
through SessionManager and registered cleanup hooks, providing a single
shutdown path for all runtime exit scenarios.

This is an orchestration layer only.  No runtime/business logic lives here.
Future phases (Planner, Runtime, Reflection, Evolution) will hook into this
lifecycle without requiring changes to existing services.
"""

from __future__ import annotations

import asyncio
from typing import Type, TypeVar, Optional, Callable, Awaitable

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper

T = TypeVar("T")


class ApplicationHost:
    """
    Owns the application lifecycle: initialize → start → stop → dispose.

    Each method is independently callable and idempotent — calling
    initialize() twice, or stop() before start(), is a safe no-op rather
    than an error, so callers (including future phases) don't need to
    track state themselves.

    Phase 4.5: stop() orchestrates cleanup across services.
    """

    def __init__(self, container: DependencyContainer, bootstrapper: Bootstrapper) -> None:
        self._container = container
        self._bootstrapper = bootstrapper
        self._initialized = False
        self._started = False
        # Phase 4.5: cleanup hooks (async callables registered by services)
        self._cleanup_hooks: list[Callable[[], Awaitable[None]]] = []

    def register_cleanup_hook(self, hook: Callable[[], Awaitable[None]]) -> None:
        """
        Phase 4.5: Register an async cleanup hook to be called during stop().
        Hooks are called in reverse registration order (LIFO).
        """
        self._cleanup_hooks.append(hook)

    def initialize(self) -> None:
        """Run the bootstrapper to construct and register all services."""
        if self._initialized:
            return
        self._bootstrapper.bootstrap()
        self._initialized = True

    def start(self) -> None:
        """Mark the application as running. Requires initialize() first."""
        if not self._initialized:
            raise RuntimeError(
                "ApplicationHost.start() called before initialize()."
            )
        self._started = True

    async def stop(self) -> None:
        """
        Phase 4.5: Unified graceful shutdown — coordinates cleanup across
        all registered services and hooks. Idempotent.
        """
        if not self._started:
            return
        self._started = False

        print("\n[ApplicationHost] Beginning unified shutdown...")

        # Run cleanup hooks in reverse order (LIFO — last registered, first cleaned)
        for hook in reversed(self._cleanup_hooks):
            try:
                await hook()
            except Exception as e:
                print(f"[ApplicationHost] Cleanup hook error (non-fatal): {e}")

        print("[ApplicationHost] Unified shutdown complete.")

    def dispose(self) -> None:
        """Release lifecycle state. Does not tear down the DI container."""
        self._started = False
        self._initialized = False
        self._cleanup_hooks.clear()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_started(self) -> bool:
        return self._started

    def get_service(self, interface: Type[T]) -> T:
        """Read-only access to a service registered in the container."""
        return self._container.resolve(interface)


