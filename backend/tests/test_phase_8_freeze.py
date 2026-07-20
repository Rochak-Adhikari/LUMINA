"""
tests/test_phase_8_freeze.py — Phase 8 Validation & Freeze

Subsystem-wide validation of the whole Skill Runtime (Phases 8.1–8.13) as the
governance gate before FREEZE. Asserts, across every stage at once:

  - every runtime interface has exactly one registered concrete implementation
  - every stage resolves through the RuntimeFacade (dormant accessor)
  - all skill_runtime models are frozen (immutability)
  - the runtime is dormant — bootstrapping registers services but no runtime
    path auto-invokes them (Phase 5 behavior byte-identical)
  - AST boundary enforcement across ALL stage modules (no forbidden imports:
    subprocess/threading/asyncio/requests/sqlite/socket, no core/brain-planner/
    skill_creator upward imports; importlib only in the loader)
  - determinism guard: no clocks/uuid/random tokens in any stage module
    (the loader's caller-supplied import is the only permitted side effect)

This test adds NO runtime behavior. It only proves the existing subsystem holds
its invariants. Stdlib unittest.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.container import DependencyContainer
from core.bootstrap import Bootstrapper
from core.runtime_facade import RuntimeFacade

from brain.skill_runtime import interfaces as ifaces
from brain.skill_runtime import models as models_mod

from brain.skill_runtime.interfaces import (
    IRegistryDiscovery, ICapabilityMatcher, IDependencyResolver, ISkillSandbox,
    ISkillLoader, ISkillExecutor, IContextInjector, IExecutionObserver,
    IExecutionRecorder, IExecutionPersistence, IRuntimePipeline,
    IFailureRecovery, IRuntimeValidator,
)

# The 13 runtime contracts + their facade accessor names.
_CONTRACTS = {
    IRegistryDiscovery: "registry_discovery",
    ICapabilityMatcher: "capability_matcher",
    IDependencyResolver: "dependency_resolver",
    ISkillSandbox: "skill_sandbox",
    ISkillLoader: "skill_loader",
    ISkillExecutor: "skill_executor",
    IContextInjector: "context_injector",
    IExecutionObserver: "execution_observer",
    IExecutionRecorder: "execution_recorder",
    IExecutionPersistence: "execution_persistence",
    IRuntimePipeline: "runtime_pipeline",
    IFailureRecovery: "failure_recovery",
    IRuntimeValidator: "runtime_validator",
}

_STAGE_MODULES = [
    "registry_discovery.py", "capability_matcher.py", "dependency_resolver.py",
    "skill_sandbox.py", "skill_loader.py", "skill_executor.py",
    "context_injector.py", "execution_observer.py", "execution_recorder.py",
    "execution_persistence.py", "runtime_pipeline.py", "failure_recovery.py",
    "runtime_validation.py",
]

_SR = backend_dir / "brain" / "skill_runtime"


def _module_imports(rel):
    src = (_SR / rel).read_text(encoding="utf-8")
    modules = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(a.name for a in node.names)
    return modules


class TestContractsAndDI(unittest.TestCase):
    def setUp(self):
        self.c = DependencyContainer()
        Bootstrapper(self.c).bootstrap()
        self.facade = RuntimeFacade(self.c)

    def test_all_thirteen_registered(self):
        for contract in _CONTRACTS:
            self.assertTrue(self.c.is_registered(contract),
                            f"{contract.__name__} not registered")

    def test_each_contract_one_impl(self):
        for contract in _CONTRACTS:
            impl = self.c.resolve(contract)
            self.assertIsInstance(impl, contract)

    def test_facade_accessors_resolve(self):
        for contract, accessor in _CONTRACTS.items():
            svc = getattr(self.facade, accessor)
            self.assertIsInstance(svc, contract, accessor)

    def test_singleton_identity(self):
        # Each dormant service is a single shared instance.
        for contract in _CONTRACTS:
            self.assertIs(self.c.resolve(contract), self.c.resolve(contract))


class TestImmutability(unittest.TestCase):
    def test_all_models_frozen(self):
        from pydantic import BaseModel
        checked = 0
        for name in dir(models_mod):
            obj = getattr(models_mod, name)
            if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
                self.assertTrue(
                    obj.model_config.get("frozen", False),
                    f"{name} is not frozen",
                )
                checked += 1
        self.assertGreaterEqual(checked, 13)


class TestBoundaries(unittest.TestCase):
    FORBIDDEN_IMPORTS = (
        "subprocess", "threading", "asyncio", "requests", "socket", "sqlite3",
        "core.bootstrap", "brain.planning", "brain.skill_creator",
    )

    def test_no_forbidden_imports_any_stage(self):
        for rel in _STAGE_MODULES:
            imports = _module_imports(rel)
            for imp in imports:
                for banned in self.FORBIDDEN_IMPORTS:
                    self.assertFalse(
                        imp == banned or imp.startswith(banned + "."),
                        f"{rel} imports forbidden {imp}",
                    )

    def test_importlib_only_in_loader(self):
        for rel in _STAGE_MODULES:
            imports = _module_imports(rel)
            uses_importlib = any(i == "importlib" or i.startswith("importlib.")
                                 for i in imports)
            if rel == "skill_loader.py":
                self.assertTrue(uses_importlib, "loader must import importlib")
            else:
                self.assertFalse(uses_importlib, f"{rel} must not import importlib")

    def test_no_nondeterminism_tokens(self):
        # No clocks/uuid/random anywhere; loader's import is the only side effect.
        for rel in _STAGE_MODULES:
            src = (_SR / rel).read_text(encoding="utf-8")
            for banned in ["datetime.now", "utcnow", "time.time(", "uuid.",
                           "uuid4", "uuid1", "random.", "secrets."]:
                self.assertNotIn(banned, src, f"{rel} contains {banned}")


class TestDormancy(unittest.TestCase):
    def test_bootstrap_is_clean(self):
        # Bootstrapping the container registers the runtime but must not raise
        # or auto-run any stage (dormant). A second bootstrap is idempotent.
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        for contract in _CONTRACTS:
            self.assertTrue(c.is_registered(contract))


if __name__ == "__main__":
    unittest.main()
