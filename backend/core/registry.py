"""
Decorator-based registry for runtime discovery of pluggable components.

Adapted from OpenJarvis registry pattern. Each typed subclass gets its own
isolated storage so registrations in one registry never leak into another.

Usage:
    @ActionRegistry.register("open_app")
    def open_app(params, response, player, session_memory):
        ...

    # Later:
    fn = ActionRegistry.get("open_app")
    result = fn(params, response, player, session_memory)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Generic, Tuple, TypeVar

T = TypeVar("T")


class RegistryBase(Generic[T]):
    """Generic registry base class with class-specific entry isolation."""

    @classmethod
    def _entries(cls) -> Dict[str, T]:
        attr_name = f"_registry_entries_{cls.__name__}"
        storage = getattr(cls, attr_name, None)
        if storage is None:
            storage: Dict[str, T] = {}
            setattr(cls, attr_name, storage)
        return storage

    @classmethod
    def register(cls, key: str) -> Callable[[T], T]:
        """Decorator that registers *entry* under *key*."""
        def decorator(entry: T) -> T:
            entries = cls._entries()
            if key in entries:
                raise ValueError(f"{cls.__name__} already has an entry for '{key}'")
            entries[key] = entry
            return entry
        return decorator

    @classmethod
    def register_value(cls, key: str, value: T) -> T:
        """Imperatively register a *value* under *key*."""
        entries = cls._entries()
        if key in entries:
            raise ValueError(f"{cls.__name__} already has an entry for '{key}'")
        entries[key] = value
        return value

    @classmethod
    def get(cls, key: str) -> T:
        """Retrieve the entry for *key*, raising ``KeyError`` if missing."""
        try:
            return cls._entries()[key]
        except KeyError as exc:
            raise KeyError(
                f"{cls.__name__} does not have an entry for '{key}'"
            ) from exc

    @classmethod
    def create(cls, key: str, *args: Any, **kwargs: Any) -> Any:
        """Look up *key* and instantiate it with the given arguments."""
        entry = cls.get(key)
        if not callable(entry):
            raise TypeError(
                f"{cls.__name__} entry '{key}' is not callable"
                " and cannot be instantiated"
            )
        return entry(*args, **kwargs)

    @classmethod
    def items(cls) -> Tuple[Tuple[str, T], ...]:
        """Return all ``(key, entry)`` pairs as a tuple."""
        return tuple(cls._entries().items())

    @classmethod
    def keys(cls) -> Tuple[str, ...]:
        """Return all registered keys as a tuple."""
        return tuple(cls._entries().keys())

    @classmethod
    def contains(cls, key: str) -> bool:
        """Check whether *key* is registered."""
        return key in cls._entries()

    @classmethod
    def clear(cls) -> None:
        """Remove all entries (useful in tests)."""
        cls._entries().clear()


# ---------------------------------------------------------------------------
# Typed subclass registries — one per Lumina primitive
# ---------------------------------------------------------------------------

class ActionRegistry(RegistryBase[Callable]):
    """Registry for action functions (imported from actions/ modules)."""


class AgentRegistry(RegistryBase[Any]):
    """Registry for agent implementations (CadAgent, KasaAgent, etc.)."""


class ToolRegistry(RegistryBase[Any]):
    """Registry for Gemini function declaration tool specs."""


class ToolDispatcherRegistry(RegistryBase[Callable]):
    """Registry for dispatcher handlers that execute Gemini function calls."""
