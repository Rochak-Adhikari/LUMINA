"""
core/test_phase_1_5.py — Phase 1.5 verification tests (Request Pipeline Foundation)

Run:
    conda activate lumina && python backend/core/test_phase_1_5.py
"""

from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_passed = 0
_failed = 0


def check(condition: bool, description: str) -> None:
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {description}")
    else:
        _failed += 1
        print(f"  [FAIL] {description}")


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run() -> None:
    from core.pipeline import PipelineBuilder, PipelineContext, RequestPipeline
    from core.middleware import PipelineMiddleware
    from core.interfaces import IPipeline, IPipelineMiddleware
    from core.context import ExecutionContext
    from core.container import DependencyContainer

    # Test-only middleware — records call order. Not a production component.
    class _RecordingMiddleware(PipelineMiddleware):
        def __init__(self, tag: str, calls: list):
            self._tag = tag
            self._calls = calls

        async def handle(self, context: PipelineContext, call_next):
            self._calls.append(f"{self._tag}:before")
            context.attributes[self._tag] = True
            result = await call_next(context)
            self._calls.append(f"{self._tag}:after")
            return result

    class _ShortCircuitMiddleware(PipelineMiddleware):
        async def handle(self, context: PipelineContext, call_next):
            context.attributes["short_circuited"] = True
            return context  # deliberately does not call call_next

    section("PipelineContext")
    ec = ExecutionContext()
    ctx = PipelineContext(execution_context=ec, request_metadata={"kind": "test"})
    check(ctx.execution_context is ec, "PipelineContext holds the ExecutionContext by reference")
    check(dict(ctx.request_metadata) == {"kind": "test"}, "request_metadata content preserved")
    try:
        ctx.request_metadata["kind"] = "mutated"  # type: ignore[index]
        check(False, "request_metadata should be immutable")
    except TypeError:
        check(True, "request_metadata is immutable (TypeError on write)")
    check(ctx.attributes == {}, "attributes bag starts empty")
    ctx.attributes["foo"] = "bar"
    check(ctx.attributes["foo"] == "bar", "attributes bag is mutable for middleware communication")
    check(ctx.is_cancelled is False, "context starts not cancelled")
    ctx.cancel()
    check(ctx.is_cancelled is True, "cancel() sets is_cancelled")

    section("RequestPipeline — mutation before seal")
    pipeline = RequestPipeline()
    check(isinstance(pipeline, IPipeline), "RequestPipeline implements IPipeline")
    check(pipeline.is_sealed is False, "fresh pipeline is not sealed")
    calls: list = []
    mw_a = _RecordingMiddleware("a", calls)
    mw_b = _RecordingMiddleware("b", calls)
    pipeline.register(mw_a)
    pipeline.register(mw_b)
    check(pipeline.middleware_count == 2, "register() adds middleware")
    pipeline.remove(mw_b)
    check(pipeline.middleware_count == 1, "remove() removes middleware")
    pipeline.register(mw_b)
    pipeline.clear()
    check(pipeline.middleware_count == 0, "clear() removes all middleware")
    pipeline.register(mw_a)
    pipeline.register(mw_b)

    section("RequestPipeline — seal & immutability")
    pipeline.seal()
    check(pipeline.is_sealed is True, "seal() marks pipeline sealed")
    for label, fn in (
        ("register", lambda: pipeline.register(mw_a)),
        ("remove", lambda: pipeline.remove(mw_a)),
        ("clear", lambda: pipeline.clear()),
    ):
        try:
            fn()
            check(False, f"{label}() after seal should raise RuntimeError")
        except RuntimeError:
            check(True, f"{label}() after seal raises RuntimeError")

    section("RequestPipeline — execute() ordering")
    exec_ctx = PipelineContext(execution_context=ExecutionContext())

    async def run_pipeline():
        return await pipeline.execute(exec_ctx)

    result = asyncio.run(run_pipeline())
    check(calls == ["a:before", "b:before", "b:after", "a:after"], "middleware run in order, wrapping call_next correctly")
    check(result is exec_ctx, "execute() returns the (possibly transformed) context")
    check(result.attributes.get("a") is True and result.attributes.get("b") is True, "middleware mutated shared attributes bag")

    section("RequestPipeline — empty pipeline execute()")
    empty = PipelineBuilder().build()
    empty_ctx = PipelineContext(execution_context=ExecutionContext())
    empty_result = asyncio.run(empty.execute(empty_ctx))
    check(empty_result is empty_ctx, "empty sealed pipeline returns context unchanged")
    check(empty.is_sealed is True, "PipelineBuilder.build() returns a sealed pipeline")

    section("RequestPipeline — short-circuit")
    sc_pipeline = PipelineBuilder().use(_ShortCircuitMiddleware()).use(mw_a).build()
    # mw_a already sealed once above; re-registering a sealed-immutable
    # instance into a *different* pipeline is fine, it's stateless.
    sc_calls_before = len(calls)
    sc_ctx = PipelineContext(execution_context=ExecutionContext())
    sc_result = asyncio.run(sc_pipeline.execute(sc_ctx))
    check(sc_result.attributes.get("short_circuited") is True, "short-circuit middleware ran")
    check(len(calls) == sc_calls_before, "downstream middleware did not run after short-circuit")

    section("PipelineBuilder — fluent API")
    b = PipelineBuilder()
    returned = b.use(_RecordingMiddleware("x", []))
    check(returned is b, "use() returns self for chaining")

    section("DI Container integration")
    c = DependencyContainer()
    built = PipelineBuilder().build()
    c.register_instance(IPipeline, built)
    resolved = c.resolve(IPipeline)
    check(resolved is built, "RequestPipeline resolves from container via IPipeline")

    section("Bootstrapper integration")
    from core.bootstrap import Bootstrapper
    bc = DependencyContainer()
    bs = Bootstrapper(container=bc, kasa_agent=None)
    bs.bootstrap()
    check(bs.pipeline is not None, "Bootstrapper constructs a RequestPipeline")
    check(bs.pipeline.is_sealed is True, "Bootstrapper-built pipeline is sealed (immutable)")
    check(bs.pipeline.middleware_count == 0, "Bootstrapper registers zero middleware (infrastructure only)")
    check(
        bc.resolve(IPipeline) is bs.pipeline,
        "Bootstrapper registers the same pipeline instance it exposes",
    )

    section("Interface contract sanity")
    check(issubclass(PipelineMiddleware, IPipelineMiddleware), "PipelineMiddleware implements IPipelineMiddleware")
    check(issubclass(RequestPipeline, IPipeline), "RequestPipeline implements IPipeline")

    section("PHASE 1.5 TEST SUMMARY")
    print(f"  Passed: {_passed}")
    print(f"  Failed: {_failed}")
    print("=" * 60)
    if _failed == 0:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    run()
