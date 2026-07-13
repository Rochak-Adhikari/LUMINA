"""
core/pipeline.py — Lumina V2 Request Pipeline Foundation (Phase 1.5)

Pure infrastructure for a generic, ordered middleware execution pipeline.
This module does NOT decide what runs through the pipeline, does not
contain any business/prompt/tool/permission logic, and is NOT connected
to any existing runtime path (Socket.IO, AudioLoop, Gemini Live, tool
dispatch). It exists solely so later phases can adopt it incrementally
without re-architecting.

Components
----------
PipelineContext  — immutable-by-convention bundle of per-execution data
                    (ExecutionContext, a read-only BrainState snapshot,
                    immutable request metadata) plus a mutable attribute
                    bag middleware can use to pass data to each other, and
                    minimal cancellation state.

RequestPipeline   — ordered middleware chain. Mutable (register/remove/
                    clear) only until sealed; sealed by PipelineBuilder at
                    the end of construction, after which mutation raises.

PipelineBuilder   — fluent builder that accumulates middleware and
                    produces a sealed, immutable RequestPipeline.

Design principles
------------------
1. INFRASTRUCTURE ONLY
   No concrete middleware is implemented here (see core/middleware.py for
   the base abstraction only). This module never inspects what a
   middleware does — it just calls handle() in order.

2. IMMUTABLE AFTER STARTUP
   RequestPipeline is built once during application initialization
   (via Bootstrapper) and sealed. Sealing freezes the middleware order
   into a tuple and rejects further register()/remove()/clear() calls.

3. LOCK-FREE EXECUTION
   Because construction and execution are separated by sealing, execute()
   never needs a lock — the middleware tuple cannot change after startup.

4. COMPLEMENTS, DOES NOT REPLACE
   PipelineContext carries an ExecutionContext and a BrainState snapshot
   by reference rather than duplicating their responsibilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional

from core.context import ExecutionContext
from core.interfaces import IPipeline, IPipelineMiddleware


@dataclass
class PipelineContext:
    """
    Per-execution data passed through a RequestPipeline.

    execution_context  ExecutionContext for this unit of work (Phase 1.4).
    brain_snapshot      Read-only BrainState snapshot at pipeline start
                        (as returned by IBrainState.snapshot()); never
                        mutated by the pipeline.
    request_metadata    Immutable mapping describing the request (e.g.
                        {"kind": "voice"} in future phases). Frozen at
                        construction time.
    attributes          Mutable dict middleware may use to pass data to
                        later middleware in the same execution. Not
                        immutable by design — this is the one place
                        cross-middleware communication is expected.
    """

    execution_context: ExecutionContext
    brain_snapshot: Any = None
    request_metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    attributes: Dict[str, Any] = field(default_factory=dict)
    _cancelled: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.request_metadata, MappingProxyType):
            self.request_metadata = MappingProxyType(dict(self.request_metadata))

    def cancel(self) -> None:
        """Mark this execution as cancelled. Middleware may check is_cancelled."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


class RequestPipeline(IPipeline):
    """
    Ordered middleware chain.

    Mutable only until seal() is called (done by PipelineBuilder.build()).
    After sealing, register()/remove()/clear() raise RuntimeError, and
    execute() iterates a fixed tuple — no locking required.
    """

    def __init__(self) -> None:
        self._middleware: List[IPipelineMiddleware] = []
        self._sealed = False

    def register(self, middleware: IPipelineMiddleware) -> None:
        self._assert_not_sealed()
        self._middleware.append(middleware)

    def remove(self, middleware: IPipelineMiddleware) -> None:
        self._assert_not_sealed()
        self._middleware.remove(middleware)

    def clear(self) -> None:
        self._assert_not_sealed()
        self._middleware.clear()

    def seal(self) -> None:
        """Freeze middleware order and forbid further mutation."""
        self._middleware = list(self._middleware)  # defensive copy before freezing
        self._sealed = True

    @property
    def is_sealed(self) -> bool:
        return self._sealed

    @property
    def middleware_count(self) -> int:
        return len(self._middleware)

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Run *context* through the middleware chain in registration order."""
        chain = self._middleware

        async def _run(index: int, ctx: PipelineContext) -> PipelineContext:
            if index >= len(chain):
                return ctx

            async def call_next(next_ctx: PipelineContext) -> PipelineContext:
                return await _run(index + 1, next_ctx)

            return await chain[index].handle(ctx, call_next)

        return await _run(0, context)

    def _assert_not_sealed(self) -> None:
        if self._sealed:
            raise RuntimeError(
                "RequestPipeline is sealed (immutable after application "
                "initialization). Configure middleware before build()."
            )


class PipelineBuilder:
    """
    Fluent builder that accumulates middleware and produces a sealed,
    immutable RequestPipeline. Intended for use exclusively during
    application startup (Bootstrapper).
    """

    def __init__(self) -> None:
        self._pipeline = RequestPipeline()

    def use(self, middleware: IPipelineMiddleware) -> "PipelineBuilder":
        """Append *middleware* to the pipeline being built. Returns self."""
        self._pipeline.register(middleware)
        return self

    def build(self) -> RequestPipeline:
        """Seal and return the constructed RequestPipeline."""
        self._pipeline.seal()
        return self._pipeline
