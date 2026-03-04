# Decision 019: Semantic vs. Logical Edge Types

**Status**: Implemented
**Date**: 2026-03-04

---

## Problem

The linker has only logical edge types (`supports`, `contradicts`, `exemplifies`). When it encounters two nodes that are semantically related but have no logical implication between them, it reaches for the closest available type — usually `supports`.

**Concrete case from first physics theory ingest:**

`preference-001` ("User expresses interest in exploring delayed-choice experiments") was linked to `fact-015`, `fact-010`, `fact-017`, etc. via `supports` edges. This is semantically coherent (they share a topic domain) but logically wrong — a statement of research intent is not evidence for a physics claim.

Result: `preference-001` inflates the confidence of core theory facts through the PageRank computation. "I want to test X" contributes 1.0 authority to "X is true."

---

## Decision

Add a `logical` flag to edge types in `node_types.yaml`. Edge types with `logical: true` are included in confidence computation (PageRank). Edge types with `logical: false` are used only for traversal and discovery.

Add a new `related_to` edge type: `logical: false`. This captures "these nodes are about the same subject" without asserting any implication direction.

### Schema change

```yaml
edge_types:
  supports:
    linkable: true
    logical: true
  contradicts:
    linkable: true
    logical: true
  exemplifies:
    linkable: false
    logical: true
  related_to:           # NEW
    linkable: true
    logical: false      # semantic only — not counted in confidence
  because_of:
    linkable: false
    logical: false      # causal dependency, not logical implication
  supersedes:
    linkable: false
    logical: false
```

### Traversal modes

| Mode | Which edges | Use case |
|------|-------------|----------|
| Confidence (PageRank) | `logical: true` only | Compute authority scores |
| Logical graph walk | `logical: true` only | Find logically-grounded evidence chains |
| Semantic graph walk | all edges | Broad topic discovery, RAG-style retrieval |
| Default `query_knowledge` | all edges for seeding, logical only for ranking | Balanced — discover via semantics, rank via logic |

### Linker prompt change

The linker prompt must distinguish:

- **Supports**: A is evidence that B is true, or A being true makes B more likely
- **Contradicts**: A being true makes B less likely or directly refutes B
- **Exemplifies**: B is a general principle; A is a specific instance of it
- **Related_to**: A and B are about the same topic/domain, but no directional implication — use this when in doubt

The key test: *"Would a logician accept A as evidence for or against B?"* If no, use `related_to`.

---

## Effects

### Immediate

- `preference-001 → fact-015 [supports]` should be `preference-001 → fact-015 [related_to]`
- Confidence of core theory facts drops slightly (no longer boosted by preference nodes)
- Confidence computation explicitly filters to `logical: true` edges

### Structural

The KG now has two traversal layers:
1. **Logic layer**: `supports`/`contradicts`/`exemplifies` — the argument graph. Authority flows through this layer via PageRank.
2. **Topic layer**: `related_to` — the semantic neighborhood. No authority, but enables discovery of related nodes that have no logical connection.

This makes the system closer to a hybrid KG+RAG architecture: the topic layer provides the recall properties of vector search, the logic layer provides the precision and confidence semantics that pure RAG lacks.

### Future passes enabled

Once `related_to` exists, additional ingestion passes can populate the topic layer without polluting the logic layer:
- **LLM external knowledge pass**: Use model's training knowledge to add `related_to` links from ingested claims to known external concepts (icebox)
- **Internet/citation pass**: Link ingested claims to published papers via `related_to` (icebox)

---

## What we are NOT doing

- Not changing the existing `supports`/`contradicts` semantics
- Not making `related_to` undirected (edges stay directed; source is "more specifically about" target)
- Not running the linker again on existing data (the `preference-001` case can be manually fixed or left for next ingest)

---

## Trigger

Implement when ingesting the second physics document. At that point, the linker needs the `related_to` type available, and the confidence computation needs to filter to `logical: true` edges only.
