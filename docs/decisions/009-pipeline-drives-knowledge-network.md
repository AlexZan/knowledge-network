# Decision 009: Pipeline Drives Knowledge Network Features

**Date**: 2025-01-22
**Status**: Accepted

## Context

We identified two distinct modes of operation:

| Mode | Description | Context Pattern |
|------|-------------|-----------------|
| **Pipeline Step** | Agent runs, produces artifact | Clean in → work → clean out. Short-lived context. |
| **Interactive Session** | User + AI back-and-forth | Accumulating context. Needs auto-compaction. |

The knowledge network's auto-compaction (two-log model, streaming capture) is valuable for **interactive sessions** where context accumulates and needs management.

For **pipeline steps**, artifacts themselves serve as the compaction boundary:
- Agent receives artifact (clean input)
- Agent produces artifact (clean output)
- Internal "work" context is discarded after step completes
- No need for sophisticated context management within short-lived agent runs

## Decision

**The pipeline project drives the knowledge network project.**

Instead of:
```
1. Build knowledge network primitives
2. Build pipeline on top
```

We will:
```
1. Build pipeline (agents, artifacts, workflow)
2. When pipeline needs a knowledge network feature, add it
3. Features are driven by real usage, not speculation
```

## Implications

### Knowledge Network (this project)
- **Pause active development** until pipeline needs drive it
- Current state (models, basic storage) is sufficient for pipeline v1
- Interactive session features (two-log, auto-compaction) wait until needed

### Open Intelligence (sibling project)
- **Primary development focus**
- Build CLI, agents, artifact workflow
- When we add interactive brainstorm mode → pull in knowledge network features

### Slice 1 Reframing
- Original Slice 1 mixed pipeline + knowledge network concerns
- For pipeline-only mode: artifacts are the interface, no two-log needed
- Two-log model becomes relevant when we add interactive sessions

## What We Learned

1. **Artifacts are context boundaries** - Clean handoff between agents
2. **Auto-compaction solves interactive accumulation** - Not needed for agent steps
3. **Let usage drive features** - Don't build primitives in isolation

## Related

- [thesis.md](../thesis.md) - Original knowledge network vision (still valid, just deferred)
- [008-dev-first-pivot.md](./008-dev-first-pivot.md) - Earlier decision to specialize for dev
