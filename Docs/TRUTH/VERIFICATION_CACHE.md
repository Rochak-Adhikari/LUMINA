# VERIFICATION CACHE
Version: 1.0
Status: Active

Purpose:

Avoid unnecessary repository reads.

Previously verified files should NOT be reread unless their verification becomes invalid.

---

# CACHE VALIDITY

Verification remains valid until one of the following occurs:

- the file changes
- a direct dependency changes
- the user explicitly requests verification
- the current roadmap step requires a new interface

Otherwise the cached understanding is authoritative.

---

# CURRENTLY VERIFIED

## Architecture

docs/architecture/README.md

docs/architecture/01_CURRENT_ARCHITECTURE.md

docs/architecture/02_ARCHITECTURE_ANALYSIS.md

docs/architecture/03_REFACTORING_PLAN.md

docs/architecture/04_V3_ARCHITECTURE.md

docs/architecture/05_IMPLEMENTATION_ROADMAP.md

docs/architecture/06_FUTURE_FEATURES.md

---

## Truth

Docs/TRUTH/

---

## Runtime

backend/server.py

backend/lumina.py

backend/core/bootstrap.py

backend/core/runtime_facade.py

---

## Skill System

backend/brain/skills/builtin.py

backend/brain/skills/registry.py

---

# CURRENT SESSION CACHE

During each implementation session maintain an internal cache of files already read.

Never reread these files unless they were modified during the session.

Example:

backend/brain/planning/llm_planner.py

backend/tests/test_phase_5_4.py

backend/brain/core/brain_core.py

---

# READ BUDGET

Repository reads are expensive.

Maximum policy:

Read each required file exactly once.

Never reread unchanged files.

Never perform repository-wide searches.

Never inspect sibling modules without direct dependency.

Never perform "verification" reads after implementation unless requested.

---

# WHEN A FILE MAY BE READ

A verified file may ONLY be read if:

1. It was modified.

2. One of its direct dependencies changed.

3. The user explicitly requests re-verification.

4. The approved roadmap step requires information not already available.

Otherwise use cached knowledge.

---

# IMPLEMENTATION POLICY

For every roadmap step:

1. Check this cache.

2. Determine required files.

3. Read only those files.

4. Implement.

5. Run regression.

6. Stop.

Never restart repository discovery.

Never rescan architecture.

Never rediscover invariants.

---

# REPOSITORY POLICY

Full repository scans are prohibited during implementation unless explicitly requested by the user.

Directory exploration is prohibited unless required to locate a missing implementation file.

Architecture rediscovery is prohibited.

Repeated verification is prohibited.

---

# GOAL

Minimize:

- repository reads
- token usage
- API cost
- implementation time

while preserving:

- correctness
- roadmap compliance
- deterministic implementation
- regression safety