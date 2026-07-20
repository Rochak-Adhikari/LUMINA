"""
core/container.py — Lumina V2 Dependency Injection Container

A lightweight, zero-dependency DI container that maps interface types to
concrete implementations.  No external libraries (no dependency_injector,
no wire, no inject).

Design decisions:
  - Singleton registrations: one instance is created on first resolve and
    reused for the lifetime of the process.
  - Transient registrations: a new instance is created on every resolve call.
  - Factory registrations: a callable is stored and invoked on resolve.
  - Lazy instantiation: nothing is created until first resolve().
  - Thread-safe: a single lock guards mutation of the internal registry.
    Read-paths (resolve) lock only during first-time construction.

Usage:

    from core.container import container
    from core.interfaces import IMemoryManager
    from memory_store import MemoryStore

    # Register a singleton (called once, reused forever)
    container.register_singleton(IMemoryManager, lambda: MemoryStore("lumina_memory.db"))

    # Resolve (creates on first call, returns cached on subsequent calls)
    ms: IMemoryManager = container.resolve(IMemoryManager)

    # Register a transient (new instance every resolve)
    container.register_transient(IFoo, lambda: FooImpl())

    # Register a pre-built instance directly
    container.register_instance(IEventBus, event_bus)
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional, Type, TypeVar

T = TypeVar("T")

# Registration modes
_SINGLETON = "singleton"
_TRANSIENT = "transient"
_INSTANCE  = "instance"


class _Registration:
    """Internal record stored for each registered interface."""

    __slots__ = ("mode", "factory", "instance")

    def __init__(self, mode: str, factory: Optional[Callable[[], Any]], instance: Any = None):
        self.mode = mode
        self.factory = factory
        self.instance = instance  # populated after first singleton resolve


class DependencyContainer:
    """
    Lightweight dependency injection container.

    Public methods
    ──────────────
    register_singleton(iface, factory)  — one shared instance (lazy)
    register_transient(iface, factory)  — new instance per resolve
    register_instance(iface, obj)       — pre-built object, returned as-is
    resolve(iface)                      — retrieve (or create) the binding
    is_registered(iface)                — check if a binding exists
    reset()                             — remove all registrations (tests only)
    """

    def __init__(self) -> None:
        self._registry: Dict[Any, _Registration] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register_singleton(
        self,
        interface: Type[T],
        factory: Callable[[], T],
    ) -> None:
        """
        Register *factory* as the provider for *interface*.
        The factory is called exactly once; the result is cached and
        returned for every subsequent resolve call.

        Raises ValueError if the interface is already registered.
        """
        with self._lock:
            self._assert_not_registered(interface)
            self._registry[interface] = _Registration(
                mode=_SINGLETON, factory=factory
            )

    def register_transient(
        self,
        interface: Type[T],
        factory: Callable[[], T],
    ) -> None:
        """
        Register *factory* as the provider for *interface*.
        The factory is called on every resolve() call.

        Raises ValueError if the interface is already registered.
        """
        with self._lock:
            self._assert_not_registered(interface)
            self._registry[interface] = _Registration(
                mode=_TRANSIENT, factory=factory
            )

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Directly register a pre-built *instance* for *interface*.
        Semantically equivalent to a singleton that is already resolved.

        Raises ValueError if the interface is already registered.
        """
        with self._lock:
            self._assert_not_registered(interface)
            self._registry[interface] = _Registration(
                mode=_INSTANCE, factory=None, instance=instance
            )

    def override(self, interface: Type[T], instance: T) -> None:
        """
        Force-replace an existing binding with a pre-built instance.
        Intended for use in tests or late-binding scenarios (e.g. when the
        concrete object is constructed by legacy code before the container
        is available).

        Does NOT raise if the interface is already registered.
        """
        with self._lock:
            self._registry[interface] = _Registration(
                mode=_INSTANCE, factory=None, instance=instance
            )

    # ------------------------------------------------------------------
    # Resolution API
    # ------------------------------------------------------------------

    def resolve(self, interface: Type[T]) -> T:
        """
        Return the implementation bound to *interface*.

        - SINGLETON: creates once, then returns cached instance.
        - TRANSIENT: creates and returns a fresh instance every call.
        - INSTANCE:  returns the pre-built object directly.

        Raises KeyError if *interface* is not registered.
        """
        reg = self._registry.get(interface)
        if reg is None:
            raise KeyError(
                f"[DI Container] No binding registered for {interface!r}. "
                f"Call container.register_singleton / register_instance first."
            )

        if reg.mode == _INSTANCE:
            return reg.instance  # type: ignore[return-value]

        if reg.mode == _SINGLETON:
            # Double-checked locking for thread-safe lazy init
            if reg.instance is None:
                with self._lock:
                    if reg.instance is None:
                        reg.instance = reg.factory()
            return reg.instance  # type: ignore[return-value]

        # TRANSIENT — new every time, no lock needed
        return reg.factory()  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_registered(self, interface: Type[T]) -> bool:
        """Return True if *interface* has a binding in this container."""
        return interface in self._registry

    def reset(self) -> None:
        """
        Remove all registrations.

        ⚠️  Intended for use in tests only.  Calling this in production
        code will cause the next resolve() to raise KeyError.
        """
        with self._lock:
            self._registry.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_not_registered(self, interface: Any) -> None:
        if interface in self._registry:
            raise ValueError(
                f"[DI Container] '{interface!r}' is already registered. "
                f"Use container.override() to forcibly replace an existing binding."
            )


# ---------------------------------------------------------------------------
# Process-level singleton container instance
# ---------------------------------------------------------------------------

container: DependencyContainer = DependencyContainer()
"""
The global container instance.

Import this object wherever you need to register or resolve dependencies::

    from core.container import container
"""
