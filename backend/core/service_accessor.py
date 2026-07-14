"""
core/service_accessor.py — Lumina V2 Service Accessor Bridge (Phase 3)

Provides a unified, safe access pattern for resolving services that were
previously accessed via ``audio_loop.memory_store`` and
``audio_loop.project_manager`` scattered throughout server.py.

ServiceAccessor:
  1. Tries to resolve the service from the DI container first.
  2. Falls back to direct access on the AudioLoop reference if the DI
     resolution fails (e.g. container not yet populated during early startup).
  3. Returns None if neither source is available.

This bridge enables incremental migration: callers switch from
``audio_loop.memory_store`` to ``service_accessor.memory_store`` without
any behavior change, but gain the benefit of DI container resolution.

Thread-safe: all reads are idempotent and each call resolves fresh from
the container (no cached stale references).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.container import DependencyContainer, container as _default_container
from core.interfaces import IMemoryManager, IWorkspaceManager, IKnowledgeManager

logger = logging.getLogger(__name__)


class ServiceAccessor:
    """
    Safe bridge for resolving IMemoryManager, IWorkspaceManager, and
    IKnowledgeManager with fallback to AudioLoop attributes.

    Usage::

        sa = ServiceAccessor(container, session_manager)

        # In a handler:
        store = sa.memory_store
        if store:
            memories = store.get_memories(limit=10)
    """

    def __init__(
        self,
        container: DependencyContainer = _default_container,
        session_manager: Any = None,
    ) -> None:
        self._container = container
        self._session_manager = session_manager

    # ------------------------------------------------------------------
    # Primary accessors
    # ------------------------------------------------------------------

    @property
    def memory_store(self) -> Any:
        """
        Resolve IMemoryManager from DI container, falling back to
        SessionManager → AudioLoop.memory_store.
        """
        try:
            if self._container.is_registered(IMemoryManager):
                return self._container.resolve(IMemoryManager)
        except Exception as e:
            logger.debug("[ServiceAccessor] IMemoryManager resolve failed, using fallback: %s", e)
        # Fallback to session manager
        if self._session_manager is not None:
            return self._session_manager.memory_store
        return None

    @property
    def project_manager(self) -> Any:
        """
        Resolve IWorkspaceManager from DI container, falling back to
        SessionManager → AudioLoop.project_manager.
        """
        try:
            if self._container.is_registered(IWorkspaceManager):
                return self._container.resolve(IWorkspaceManager)
        except Exception as e:
            logger.debug("[ServiceAccessor] IWorkspaceManager resolve failed, using fallback: %s", e)
        # Fallback to session manager
        if self._session_manager is not None:
            return self._session_manager.project_manager
        return None

    @property
    def knowledge_manager(self) -> Any:
        """
        Resolve IKnowledgeManager from DI container, or None.
        No AudioLoop fallback (MemoryEngine is not an AudioLoop attribute).
        """
        try:
            if self._container.is_registered(IKnowledgeManager):
                return self._container.resolve(IKnowledgeManager)
        except Exception as e:
            logger.debug("[ServiceAccessor] IKnowledgeManager resolve failed: %s", e)
        return None

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    @property
    def has_memory_store(self) -> bool:
        """True if a memory store is available from either source."""
        return self.memory_store is not None

    @property
    def has_project_manager(self) -> bool:
        """True if a project manager is available from either source."""
        return self.project_manager is not None

    @property
    def has_knowledge_manager(self) -> bool:
        """True if a knowledge manager is available from either source."""
        return self.knowledge_manager is not None

    # ------------------------------------------------------------------
    # Current project helper
    # ------------------------------------------------------------------

    @property
    def current_project(self) -> Optional[str]:
        """Return the current project name, or None."""
        pm = self.project_manager
        if pm is not None:
            return getattr(pm, 'current_project', None)
        return None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return diagnostic status dict."""
        return {
            "has_memory_store": self.has_memory_store,
            "has_project_manager": self.has_project_manager,
            "has_knowledge_manager": self.has_knowledge_manager,
            "current_project": self.current_project,
            "container_registered": {
                "IMemoryManager": self._container.is_registered(IMemoryManager),
                "IWorkspaceManager": self._container.is_registered(IWorkspaceManager),
                "IKnowledgeManager": self._container.is_registered(IKnowledgeManager),
            },
        }
