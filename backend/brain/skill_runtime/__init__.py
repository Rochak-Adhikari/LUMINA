"""
brain/skill_runtime — Phase 8: Skill Runtime.

The runtime that CONSUMES the immutable artifacts produced by the Phase 7 Skill
Creator. Phase 7 produces skills; Phase 8 discovers, matches, loads, and (later)
executes them. Phase 8 NEVER modifies Phase 7 artifacts and NEVER bypasses the
Registry — every runtime flow begins from a RegistryEntry.

Milestone 8.1 (this package's first contribution): Registry Discovery — a
read-only service that answers "what skills exist?" by querying the frozen
IBlueprintRegistry, so the Planner never imports skills directly.

Dormant: registered in DI, no runtime consumer wires into it yet.
"""
