"""
tests/test_phase_4_5.py — Milestone 4.5 Verification (Unified Lifecycle)

Tests confirming:
  - ApplicationHost coordinates unified shutdown
  - Cleanup hooks execute in LIFO order
  - ApplicationHost.stop() is idempotent
  - Shutdown path is unified (no duplicate cleanup logic)
  - All resources cleaned up exactly once
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call, Mock
from pathlib import Path
import sys

# Ensure backend is on sys.path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Mock heavy dependencies before importing core modules
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper
from core.application import ApplicationHost


class TestPhase4_5_Unified_Lifecycle(unittest.TestCase):
    """Phase 4.5: Verify unified application lifecycle"""

    def setUp(self):
        """Create isolated ApplicationHost for each test"""
        self.container = DependencyContainer()
        self.bootstrapper = Bootstrapper(container=self.container, kasa_agent=None)
        self.app_host = ApplicationHost(container=self.container, bootstrapper=self.bootstrapper)
        # Phase 4.5: Cross-register ApplicationHost with Bootstrapper
        self.bootstrapper._app_host = self.app_host

    def test_application_host_registered_in_container(self):
        """Verify ApplicationHost is registered and resolvable via DI"""
        self.bootstrapper.bootstrap()
        # After bootstrap, ApplicationHost should be registered
        try:
            resolved_host = self.container.resolve(ApplicationHost)
            self.assertIs(resolved_host, self.app_host)
        except Exception as e:
            self.fail(f"ApplicationHost not registered in container: {e}")

    def test_cleanup_hooks_execute_lifo(self):
        """Verify cleanup hooks execute in reverse registration order (LIFO)"""
        execution_order = []

        async def hook1():
            execution_order.append(1)

        async def hook2():
            execution_order.append(2)

        async def hook3():
            execution_order.append(3)

        self.app_host.register_cleanup_hook(hook1)
        self.app_host.register_cleanup_hook(hook2)
        self.app_host.register_cleanup_hook(hook3)

        self.app_host.initialize()
        self.app_host.start()

        # Execute stop
        asyncio.run(self.app_host.stop())

        # Should execute in reverse order: 3, 2, 1
        self.assertEqual(execution_order, [3, 2, 1],
                        "Cleanup hooks must execute in LIFO order")

    def test_stop_is_idempotent(self):
        """Verify ApplicationHost.stop() can be called multiple times safely"""
        call_count = 0

        async def counting_hook():
            nonlocal call_count
            call_count += 1

        self.app_host.register_cleanup_hook(counting_hook)
        self.app_host.initialize()
        self.app_host.start()

        # Call stop three times
        asyncio.run(self.app_host.stop())
        asyncio.run(self.app_host.stop())
        asyncio.run(self.app_host.stop())

        # Hook should only execute once (first stop)
        self.assertEqual(call_count, 1,
                        "Cleanup hooks must execute exactly once despite multiple stop() calls")

    def test_cleanup_hook_errors_are_non_fatal(self):
        """Verify that errors in one cleanup hook don't prevent others from running"""
        execution_order = []

        async def hook1():
            execution_order.append(1)

        async def hook2_fails():
            execution_order.append(2)
            raise RuntimeError("Hook 2 intentional failure")

        async def hook3():
            execution_order.append(3)

        self.app_host.register_cleanup_hook(hook1)
        self.app_host.register_cleanup_hook(hook2_fails)
        self.app_host.register_cleanup_hook(hook3)

        self.app_host.initialize()
        self.app_host.start()

        # Stop should not raise despite hook2 failure
        try:
            asyncio.run(self.app_host.stop())
        except Exception as e:
            self.fail(f"ApplicationHost.stop() raised despite error handling: {e}")

        # All three hooks should have executed (LIFO: 3, 2, 1)
        self.assertEqual(execution_order, [3, 2, 1],
                        "All cleanup hooks must execute despite individual failures")

    def test_stop_without_start_is_safe(self):
        """Verify stop() before start() is a safe no-op"""
        call_count = 0

        async def hook():
            nonlocal call_count
            call_count += 1

        self.app_host.register_cleanup_hook(hook)
        self.app_host.initialize()
        # Note: NOT calling start()

        asyncio.run(self.app_host.stop())

        # Hook should not execute since app was never started
        self.assertEqual(call_count, 0,
                        "Cleanup hooks must not execute if stop() called before start()")

    def test_dispose_clears_hooks(self):
        """Verify dispose() clears all registered hooks"""
        async def dummy_hook():
            pass

        self.app_host.register_cleanup_hook(dummy_hook)
        self.app_host.register_cleanup_hook(dummy_hook)

        # Internal hook list should have 2 entries
        self.assertEqual(len(self.app_host._cleanup_hooks), 2)

        self.app_host.dispose()

        # After dispose, hooks should be cleared
        self.assertEqual(len(self.app_host._cleanup_hooks), 0,
                        "dispose() must clear all cleanup hooks")


class TestPhase4_5_Runtime_Facade_Lifecycle_Access(unittest.TestCase):
    """Phase 4.5: Verify RuntimeFacade exposes ApplicationHost"""

    def test_runtime_facade_exposes_application_host(self):
        """Verify RuntimeFacade.application_host resolves ApplicationHost"""
        container = DependencyContainer()
        bootstrapper = Bootstrapper(container=container, kasa_agent=None)
        app_host = ApplicationHost(container=container, bootstrapper=bootstrapper)
        # Phase 4.5: Cross-register ApplicationHost with Bootstrapper
        bootstrapper._app_host = app_host
        bootstrapper.bootstrap()

        # RuntimeFacade should resolve ApplicationHost
        from core.runtime_facade import RuntimeFacade
        facade = RuntimeFacade(container)

        try:
            resolved = facade.application_host
            self.assertIs(resolved, app_host,
                         "RuntimeFacade must expose the same ApplicationHost instance")
        except Exception as e:
            self.fail(f"RuntimeFacade.application_host failed: {e}")


class TestPhase4_5_No_Duplicate_Shutdown_Paths(unittest.TestCase):
    """Phase 4.5: Verify legacy shutdown paths eliminated"""

    def test_shutdown_handlers_delegate_to_app_host(self):
        """
        Verify server.py shutdown handlers delegate to ApplicationHost.stop()
        rather than performing their own cleanup (AST verification)
        """
        import ast

        backend_dir = Path(__file__).parent.parent
        server_path = backend_dir / "server.py"

        with open(server_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source)

        # Find shutdown_event, shutdown, and stop_audio functions
        shutdown_functions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                if node.name in ('shutdown_event', 'shutdown', 'stop_audio'):
                    shutdown_functions[node.name] = node

        self.assertGreater(len(shutdown_functions), 0,
                          "Must find at least one shutdown handler")

        # Each shutdown handler must route through the unified lifecycle and
        # NOT inline old cleanup patterns.
        #
        # Phase 5.4 Order 1 (B2 fix): process-exit handlers (shutdown_event,
        # shutdown) delegate to ApplicationHost.stop(); the session-scoped
        # stop_audio delegates to _unified_shutdown() directly. Using
        # ApplicationHost.stop() from stop_audio would flip the host's
        # _started flag off permanently and silently no-op every later real
        # shutdown — so stop_audio must NOT call it.
        for func_name, func_node in shutdown_functions.items():
            func_source = ast.unparse(func_node)

            if func_name == 'stop_audio':
                # Session-scoped teardown, not lifecycle disarm.
                self.assertIn("_unified_shutdown", func_source,
                             "stop_audio must delegate to _unified_shutdown (B2 fix)")
                self.assertNotIn("_app_host.stop()", func_source,
                             "stop_audio must NOT call ApplicationHost.stop() (B2 fix)")
            else:
                # Process-exit handlers still route through ApplicationHost.
                self.assertIn("_app_host.stop()", func_source,
                             f"{func_name} must delegate to ApplicationHost.stop()")

            # Must NOT inline old cleanup patterns
            bad_patterns = [
                "audio_loop.stop()",  # Should be in unified shutdown, not here
                "_session_mgr.detach()",  # Should be in unified shutdown
                "loop_task.cancel()",  # Should be in unified shutdown
                "authenticator.stop()",  # Should be in unified shutdown
            ]

            for pattern in bad_patterns:
                # Allow the pattern ONLY if it's inside the unified shutdown function itself
                if func_name in ('shutdown_event', 'shutdown', 'stop_audio'):
                    self.assertNotIn(pattern, func_source,
                                    f"{func_name} must not inline cleanup; delegate to unified shutdown")


if __name__ == '__main__':
    unittest.main()
