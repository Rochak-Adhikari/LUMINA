"""
core/middleware.py — Lumina V2 Pipeline Middleware Base (Phase 1.5)

Base abstraction for RequestPipeline middleware only. No concrete
middleware (logging, auth, permissions, memory, prompts, tools,
streaming, events, etc.) is implemented here or anywhere yet — those are
explicitly out of scope for Phase 1.5, which establishes infrastructure
only.
"""

from __future__ import annotations

from core.interfaces import IPipelineMiddleware


class PipelineMiddleware(IPipelineMiddleware):
    """
    Base class for RequestPipeline middleware.

    Subclasses must implement `handle(context, call_next)` (inherited as
    an abstractmethod from IPipelineMiddleware). This base class adds no
    behaviour beyond the interface contract — it exists so concrete
    middleware in future phases has a single, consistent base to extend.
    """

    @property
    def name(self) -> str:
        """Human-readable identifier, defaults to the class name."""
        return type(self).__name__
