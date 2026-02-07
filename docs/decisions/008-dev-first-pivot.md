# Decision 008: Dev-First Pivot

**Date**: 2024-01-17
**Status**: Accepted

---

## Context

The original slice roadmap targeted a generic AI conversation system with:
- Conclusion-triggered compaction
- Knowledge graph
- Abstraction layers
- Conflict resolution
- Emergent confidence

Through extensive brainstorming, we realized:

1. **The system is primitives + applications** - primitives are domain-agnostic, applications are configurations
2. **Dev workflow is the first application** - and will be used to build everything else
3. **2025 dev is PO-centric** - brainstorming, contracts, documentation - not touching code
4. **We designed significant new concepts** that weren't in the original slices:
   - Two-log model (raw + manifest)
   - Continuous capture
   - Effort weight / context budget
   - Peer agent model with kanban coordination
   - Stateless escalation via failure_count
   - Human cognitive model (temporal grounding, progress visibility)

---

## Decision

**Pivot from generic AI slices to dev-first slices.**

The new slice roadmap:
1. Targets development/documentation/brainstorming workflows
2. Incorporates all concepts designed in this session
3. Builds the TDD pipeline as the first application
4. Will generalize later by expanding, not by returning to old generic slices

---

## Rationale

### Why dev-first?

1. **Self-hosting** - The system builds itself. Dev tooling is needed first.
2. **Concrete use case** - Generic AI is vague. TDD pipeline is specific and testable.
3. **Informed generalization** - Building dev-first teaches us what primitives actually need.
4. **Immediate value** - We can use it while building it.

### Why not keep old slices?

1. **Superseded** - New concepts (two-log, continuous capture, peer agents) weren't in old slices
2. **Not implementation-ready** - Old slices were brainstorm-level, not detailed
3. **Git preserves history** - Can always look back if needed
4. **Expansion not regression** - Generalization will expand dev system, not return to old generic

---

## Consequences

### Positive
- Clear focus on concrete deliverable (dev pipeline)
- All session insights incorporated from the start
- System can be used while being built

### Negative
- Delays generic AI features (knowledge graph, abstraction layers, etc.)
- Old slice docs become obsolete

### Mitigations
- Generic features become later slices (after dev pipeline works)
- Old docs replaced, not archived (git history suffices)

---

## New Slice Roadmap

See [slices/README.md](../slices/README.md) for the dev-first roadmap.

---

## Related Documents

- [effort-scoped-context.md](../brainstorm/effort-scoped-context.md) - Core model
- [context-and-cognition.md](../brainstorm/context-and-cognition.md) - Two-log, continuous capture
- [peer-agent-scenario.md](../scenarios/peer-agent-scenario.md) - Peer agent model
- [agent-communication.md](../brainstorm/agent-communication.md) - Disputes, escalation
- [tech-stack.md](../tech-stack.md) - Primitives + applications framing
- [thesis.md](../thesis.md) - Updated with primitives framing
