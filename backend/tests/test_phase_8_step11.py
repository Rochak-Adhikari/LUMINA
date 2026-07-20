"""
tests/test_phase_8_step11.py — Milestone 8.11 (Runtime Pipeline Orchestrator)

Verifies the coordinator over the ten runtime stages:

    discovery → matching → resolution → sandbox → loader → context injection
      → executor → observer → recorder → persistence

  - full successful pipeline (completed=True, every field populated)
  - early stop on discovery failure (no downstream stages called)
  - early stop on no-match / unresolved / sandbox denial / load failure /
    context-not-prepared / execution failure
  - no downstream stages run after a stop
  - deterministic output (same inputs → identical result)
  - RuntimePipelineResult frozen
  - architectural boundary tests (allowed imports only; no business logic)

Fakes stand in for every stage; the orchestrator is pure coordination.
Stdlib unittest.
"""

import ast
import unittest
from pathlib import Path
import sys

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from brain.skill_runtime.runtime_pipeline import RuntimePipeline
from brain.skill_runtime.interfaces import IRuntimePipeline
from brain.skill_runtime.models import (
    CapabilityRequest,
    SandboxPolicy,
    RuntimePipelineResult,
    DiscoveredSkill,
    RegistrySearchResult,
    CapabilityMatch,
    CapabilityMatchResult,
    DependencyResolution,
    SandboxDecision,
    LoadedSkill,
    ContextInjectionResult,
    ExecutionResult,
    ExecutionObservation,
    ExecutionRecord,
    PersistenceResult,
)


# ---- Fakes: each records that it was called ---------------------------

class _Calls:
    def __init__(self):
        self.log = []


def _skill(key="fam.pkg.skill"):
    return DiscoveredSkill(blueprint_id="b1", registry_key=key)


class _Discovery:
    def __init__(self, calls, ok=True):
        self.calls, self.ok = calls, ok

    def discover(self, query=""):
        self.calls.log.append("discovery")
        skills = [_skill()] if self.ok else []
        return RegistrySearchResult(skills=skills, total_count=len(skills))


class _Matcher:
    def __init__(self, calls, ok=True):
        self.calls, self.ok = calls, ok

    def match(self, request):
        self.calls.log.append("match")
        m = [CapabilityMatch(skill=_skill(), score=100)] if self.ok else []
        return CapabilityMatchResult(matches=m, match_count=len(m))


class _Resolver:
    def __init__(self, calls, ok=True):
        self.calls, self.ok = calls, ok

    def resolve(self, matches, **kw):
        self.calls.log.append("resolve")
        return DependencyResolution(resolved=self.ok,
                                    skill=_skill() if self.ok else None)


class _Sandbox:
    def __init__(self, calls, ok=True):
        self.calls, self.ok = calls, ok

    def evaluate(self, resolution, policy):
        self.calls.log.append("sandbox")
        return SandboxDecision(approved=self.ok, skill=_skill())


class _Loader:
    def __init__(self, calls, ok=True):
        self.calls, self.ok = calls, ok

    def load(self, decision):
        self.calls.log.append("load")
        return LoadedSkill(loaded=self.ok, skill=_skill())


class _Injector:
    def __init__(self, calls, ok=True):
        self.calls, self.ok = calls, ok

    def inject(self, loaded, **kw):
        self.calls.log.append("inject")
        return ContextInjectionResult(prepared=self.ok)


class _Executor:
    def __init__(self, calls, ok=True):
        self.calls, self.ok = calls, ok

    def execute(self, loaded, context=None):
        self.calls.log.append("execute")
        return ExecutionResult(succeeded=self.ok, registry_key="fam.pkg.skill",
                               output="x" if self.ok else None,
                               error="" if self.ok else "boom")


class _Observer:
    def __init__(self, calls):
        self.calls = calls

    def observe(self, result, *, timestamp=None):
        self.calls.log.append("observe")
        return ExecutionObservation(observed=True,
                                    registry_key=result.registry_key,
                                    succeeded=result.succeeded,
                                    timestamp=timestamp)


class _Recorder:
    def __init__(self, calls):
        self.calls = calls

    def record(self, observation, *, conversation_id="", metadata=None, timestamp=None):
        self.calls.log.append("record")
        return ExecutionRecord(recorded=observation.observed,
                               registry_key=observation.registry_key,
                               succeeded=observation.succeeded,
                               timestamp=timestamp)


class _Persistence:
    def __init__(self, calls):
        self.calls = calls

    def prepare(self, record, *, storage_key=""):
        self.calls.log.append("prepare")
        return PersistenceResult(persistable=record.recorded, record=record,
                                 storage_key=storage_key)


def _pipeline(calls, **flags):
    """Build a RuntimePipeline; flags like discovery_ok=False flip a stage."""
    def ok(name):
        return flags.get(f"{name}_ok", True)
    return RuntimePipeline(
        _Discovery(calls, ok("discovery")),
        _Matcher(calls, ok("match")),
        _Resolver(calls, ok("resolve")),
        _Sandbox(calls, ok("sandbox")),
        _Loader(calls, ok("load")),
        _Injector(calls, ok("inject")),
        _Executor(calls, ok("execute")),
        _Observer(calls),
        _Recorder(calls),
        _Persistence(calls),
    )


REQ = CapabilityRequest(capability="c")
POL = SandboxPolicy()


class TestSuccess(unittest.TestCase):
    def test_is_interface(self):
        self.assertIsInstance(_pipeline(_Calls()), IRuntimePipeline)

    def test_full_success(self):
        c = _Calls()
        r = _pipeline(c).run(REQ, policy=POL, storage_key="k")
        self.assertTrue(r.completed)
        self.assertEqual(r.reason, "")
        self.assertEqual(r.registry_key, "fam.pkg.skill")
        for f in ("discovery", "match", "resolution", "sandbox", "loaded",
                  "context", "execution", "observation", "record", "persistence"):
            self.assertIsNotNone(getattr(r, f), f)
        self.assertEqual(
            c.log,
            ["discovery", "match", "resolve", "sandbox", "load", "inject",
             "execute", "observe", "record", "prepare"],
        )


class TestEarlyStop(unittest.TestCase):
    def test_discovery_stop(self):
        c = _Calls()
        r = _pipeline(c, discovery_ok=False).run(REQ, policy=POL)
        self.assertFalse(r.completed)
        self.assertEqual(r.reason, "discovery_empty")
        self.assertEqual(c.log, ["discovery"])
        self.assertIsNone(r.match)

    def test_no_match_stop(self):
        c = _Calls()
        r = _pipeline(c, match_ok=False).run(REQ, policy=POL)
        self.assertEqual(r.reason, "no_match")
        self.assertEqual(c.log, ["discovery", "match"])

    def test_unresolved_stop(self):
        c = _Calls()
        r = _pipeline(c, resolve_ok=False).run(REQ, policy=POL)
        self.assertEqual(r.reason, "unresolved")
        self.assertEqual(c.log, ["discovery", "match", "resolve"])
        self.assertIsNone(r.sandbox)

    def test_sandbox_denied_stop(self):
        c = _Calls()
        r = _pipeline(c, sandbox_ok=False).run(REQ, policy=POL)
        self.assertEqual(r.reason, "sandbox_denied")
        self.assertEqual(c.log, ["discovery", "match", "resolve", "sandbox"])
        self.assertIsNone(r.loaded)

    def test_load_failed_stop(self):
        c = _Calls()
        r = _pipeline(c, load_ok=False).run(REQ, policy=POL)
        self.assertEqual(r.reason, "load_failed")
        self.assertEqual(c.log,
                         ["discovery", "match", "resolve", "sandbox", "load"])
        self.assertIsNone(r.context)

    def test_context_stop(self):
        c = _Calls()
        r = _pipeline(c, inject_ok=False).run(REQ, policy=POL)
        self.assertEqual(r.reason, "context_not_prepared")
        self.assertEqual(
            c.log,
            ["discovery", "match", "resolve", "sandbox", "load", "inject"])
        self.assertIsNone(r.execution)

    def test_execution_failed_still_observes(self):
        # failure path DOES observe/record/prepare (capture the failure) but
        # completed stays False.
        c = _Calls()
        r = _pipeline(c, execute_ok=False).run(REQ, policy=POL)
        self.assertFalse(r.completed)
        self.assertEqual(r.reason, "execution_failed")
        self.assertIsNotNone(r.observation)
        self.assertIsNotNone(r.record)
        self.assertIsNotNone(r.persistence)
        self.assertEqual(
            c.log,
            ["discovery", "match", "resolve", "sandbox", "load", "inject",
             "execute", "observe", "record", "prepare"])


class TestDeterminism(unittest.TestCase):
    def test_same_inputs_same_output(self):
        r1 = _pipeline(_Calls()).run(REQ, policy=POL, storage_key="k",
                                     timestamp="T")
        r2 = _pipeline(_Calls()).run(REQ, policy=POL, storage_key="k",
                                     timestamp="T")
        self.assertEqual(r1.model_dump(), r2.model_dump())

    def test_result_frozen(self):
        r = _pipeline(_Calls()).run(REQ, policy=POL)
        with self.assertRaises(Exception):
            r.completed = False


class TestBoundaries(unittest.TestCase):
    def _imports(self, rel):
        src = (backend_dir / rel).read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
        return modules

    def test_allowed_imports_only(self):
        allowed = (
            "brain.skill_runtime.interfaces",
            "brain.skill_runtime.models",
            "typing", "__future__",
        )
        for m in self._imports("brain/skill_runtime/runtime_pipeline.py"):
            self.assertTrue(m.startswith(allowed), f"forbidden import {m}")

    def test_no_forbidden_tokens(self):
        src = (backend_dir / "brain/skill_runtime/runtime_pipeline.py").read_text(encoding="utf-8")
        for banned in ["subprocess", "threading", "asyncio", "importlib",
                       "eval(", "exec(", "compile(", "open(", ".now(",
                       "requests", "sqlite", "while "]:
            self.assertNotIn(banned, src, f"forbidden token {banned}")

    def test_dormant_registration(self):
        from core.container import DependencyContainer
        from core.bootstrap import Bootstrapper
        c = DependencyContainer()
        Bootstrapper(c).bootstrap()
        self.assertTrue(c.is_registered(IRuntimePipeline))
        self.assertIsInstance(c.resolve(IRuntimePipeline), RuntimePipeline)


if __name__ == "__main__":
    unittest.main()
