# PHASE 5.4 ENGINEERING RULES
Version: 1.0
Status: Authoritative

These rules are mandatory for every implementation session.

---

# PRIMARY OBJECTIVE

Implement ONLY the currently approved roadmap step.

Do not redesign.

Do not optimize unrelated code.

Do not expand scope.

---

# SOURCE OF TRUTH

The architecture has already been verified.

The following documents are authoritative:

docs/architecture/
Docs/TRUTH/

Do NOT rediscover architecture unless explicitly requested.

---

# VERIFICATION CACHE

Before reading ANY repository file:

1. Read VERIFICATION_CACHE.md.
2. If the file is listed as VERIFIED,
3. AND the user has not changed it,
4. AND no dependency changed,

DO NOT READ IT AGAIN.

Assume previous verification remains valid.

---

# CURRENT SESSION CACHE

Files read during the current implementation session are considered cached.

Never read the same file twice unless:

- the file was modified
- a dependency changed
- the user explicitly requests rereading

Otherwise reuse previous understanding.

---

# REPOSITORY READ POLICY

Repository reads are expensive.

Always ask:

"Do I actually need this file?"

If NO

DO NOT READ IT.

If YES

Read it exactly once.

Never perform repository-wide scans.

Never inspect directories out of curiosity.

Never reread unchanged files.

---

# READ ORDER

Only read files in this order:

1. VERIFICATION_CACHE.md
2. Current roadmap document
3. File being modified
4. Direct dependency (only if required)
5. Failing test (only if required)

Never read unrelated modules.

---

# IMPLEMENTATION ORDER

Always follow:

docs/architecture/05_IMPLEMENTATION_ROADMAP.md

Never skip steps.

Never combine roadmap steps.

Never anticipate future work.

---

# SCOPE RULES

Modify ONLY files required for the approved roadmap step.

Never:

- rename unrelated code
- clean unrelated code
- modernize unrelated code
- optimize unrelated code
- move files
- change formatting outside touched code

Atomic commits only.

---

# BEFORE CODING

If repository state has not changed output ONLY:

No architectural changes detected.
Proceeding with implementation.

Then print:

Files to modify

Files intentionally untouched

Dependencies

Risks

Begin implementation.

Do NOT perform additional repository analysis.

---

# AFTER CODING

Output ONLY:

Summary

Files modified

Tests executed

Regression results

Suggested commit message

STOP.

Do not continue to the next roadmap step.

---

# UNKNOWN INFORMATION

If something is unknown:

Read ONLY the missing file.

Never restart repository analysis.

Never scan the repository looking for information.

---

# IMPLEMENTATION STOP RULE

Once enough information exists to implement the current roadmap step:

STOP READING.

Begin implementation immediately.

---

# NEVER ASSUME NEW ARCHITECTURE

Unless explicitly instructed:

Assume

- architecture unchanged
- runtime unchanged
- server.py unchanged
- bootstrap unchanged
- builtin skill catalog unchanged

Do not verify them again.

---

# SUCCESS CRITERIA

Success is defined as:

- smallest possible implementation
- roadmap compliance
- zero scope expansion
- passing regression tests
- minimal repository reads
- immediate stop after implementation