# Decision 013: Unified KG Architecture — Mutability Gradient, Automerge Storage, Reactive Edges

**Date**: 2026-02-26
**Status**: Accepted

---

## Context

Decisions 011-012 established that everything is a KG node and sessions are audit logs. But they left open:

- How does node mutability work across abstraction layers?
- What's the storage backend for concurrent/distributed access?
- How do semantic dependencies (e.g., preference invalidated when its reason changes) propagate?

This decision resolves all three by connecting the knowledge-network semantic model to the Vault storage architecture (see `D:\Dev\Open-Intelligence\vault\docs\decisions\001-storage-architecture.md`).

## Decision

### 1. Mutability is a gradient mapped to abstraction layers

Not all nodes are equally mutable. A raw observation changes freely; a well-supported principle almost never does.

| Layer | Name | Mutability | Example |
|-------|------|-----------|---------|
| 0 | Raw / Private | Highly mutable — active state, frequent updates | Open effort, in-progress session, scratch notes |
| 1 | Contextual / Personal | Mutable — can be updated, superseded | "I use VS Code", "JWT expires in 1h in our config" |
| 2 | General / Shareable | Low mutability — changes require evidence from multiple sources | "REST is simpler than GraphQL for CRUD APIs" |
| 3 | Universal / Cross-network | Nearly immutable — well-established principles | "Validate inputs at trust boundaries" |

Abstraction level is already stored on principle nodes (`abstraction_level` field, added in Slice 8g). This decision extends the concept: every node has an implicit layer based on its type and evidence.

**Schema defines per-type:**
- Valid states and transitions
- Edge types it can participate in
- Mutation rules (who/what can change it, under what conditions)
- Propagation behavior (what happens when a dependency changes)

### 2. Automerge (CRDT) as the storage layer

The Vault project (`D:\Dev\Open-Intelligence\vault`) already decided on Automerge + libp2p for distributed, conflict-free, offline-first storage. Unanimous roundtable consensus (see Vault Decision 001).

**The knowledge graph is an Automerge document.** This gives us:

- **Concurrent writes that auto-merge** — two sessions editing the same node produce a deterministic result via CRDT math
- **Full change history** — every operation is tracked (event-sourcing semantics for free)
- **Offline-first** — each session works independently, syncs when reconnected
- **No last-write-wins corruption** — the failure mode of our current YAML-file approach

```
+-------------------------------------------+
|  Knowledge Graph (schema, semantics)       |
|  - Node types, edge types, propagation     |
|  - Confidence, abstraction layers          |
+-------------------------------------------+
|  Automerge (CRDT)                          |
|  - Concurrent merge, change history        |
|  - Offline-first, deterministic            |
+-------------------------------------------+
|  libp2p (Transport)                        |
|  - P2P sync across devices/sessions        |
|  - No central server                       |
+-------------------------------------------+
```

The KG layer owns *semantics* (what nodes mean, how they relate, when confidence changes). Automerge owns *storage* (how writes merge, how history is preserved). libp2p owns *sync* (how devices find each other and exchange data).

### 3. Reactive edges via `because_of`

Nodes can depend on other nodes for their validity:

```
Node A (preference): "I prefer TypeScript"
  because_of -> Node B (fact): "TypeScript has better IDE support"
    because_of -> Node C (fact): "I use VS Code"
```

When Node C is superseded ("I switched to Neovim"), the chain above may be invalidated. The current system has no propagation mechanism — stale dependencies sit undetected.

**Resolution: Lazy query-time staleness check.**

When `query_knowledge` returns a node, check if any `because_of` targets are superseded or contested. If so:
- Lower the node's effective confidence
- Add a `stale_dependency` flag
- The LLM can then ask: "You said you prefer TypeScript because of VS Code, but you've switched to Neovim — does that still hold?"

This is cheap (only runs when queried), doesn't require a propagation engine, and gives the LLM enough signal to ask the right question. The node isn't wrong — its *justification* is stale.

**Not chosen:** Eager propagation (walk all inbound `because_of` edges on supersession). Too expensive, too noisy — not every dependency chain is invalidating (Neovim has great TS support too).

## Architectural Traces

We validated this design by tracing prompts through the proposed architecture:

### Trace 1: Simple fact
`"I'm at Miami Beach"` -> Layer 1 node, no edges. Works trivially.

### Trace 2: Preference with reason
`"I prefer TypeScript because of VS Code IDE support"` -> preference node + fact node + `because_of` edge. When reason is contested, lazy staleness check flags the preference. **Works with the staleness addition.**

### Trace 3: Effort lifecycle
Open effort -> Layer 0 node, mutable (log appended each turn). Close effort -> compaction produces Layer 1 nodes (facts, decisions). Layer 0 node transitions to `concluded`. **Works — same as current implementation, just stored in graph instead of manifest.**

### Trace 4: Principle contradiction
Layer 2 principle with 4 supporting facts. New contradicting fact arrives. Confidence recalculation: 4 supports vs 1 contradiction -> confidence drops from "high" to "moderate". Refinement happens lazily at close_effort via pattern detection. **Works with current architecture.**

### Trace 5: Conflicting facts from different efforts
Two efforts produce contradicting facts about JWT expiry. `contradicts` edge created, user asked to resolve. Resolution produces a higher-quality node that `supersedes` both. If unresolved, `query_knowledge` returns both with `contested` flag. **Works — already implemented.**

### Trace 6: Deep `because_of` chain
Three-level dependency chain. Bottom node superseded. Middle and top nodes have stale justifications but no mechanism detects this. **Fixed by lazy query-time staleness check (see section 3 above).**

### Trace 7: Concurrent mutation
Two sessions writing to the same effort node. YAML files -> last-write-wins corruption. **Fixed by Automerge CRDT storage (see section 2 above).** Not a current-slice concern — single-user, single-session for now.

## Implementation Strategy

**Keep building the semantic layer on Python/YAML.** The current prototype (314 unit + 33 e2e tests) validates semantics — node types, edges, confidence, patterns, propagation. The storage layer is an implementation detail.

When Vault's Automerge layer is ready, port the semantic logic. The test suite provides the safety net for the rewrite.

| Concern | Current (prototype) | Future (production) |
|---------|-------------------|-------------------|
| Storage | YAML files | Automerge document |
| Concurrency | Single-session (YAML is fine) | Multi-session (CRDT merge) |
| Sync | N/A | libp2p P2P |
| Semantic layer | Python (oi package) | Port to Rust or keep as Python service |
| Tests | pytest (314 + 33 e2e) | Same tests, different backend |

## Open Questions

- **because_of staleness**: Identified as needed. Which slice implements it?
- **Schema system**: JSON Schema as single source of truth for Python/TypeScript/Rust? Or defer until multi-language is real?
- **Effort migration**: When does the effort manifest.yaml actually move into the graph store? Deferred from 8f, still deferred.
- **Privacy gradient**: Layer 0-3 maps to sharing boundaries. How does this interact with Vault's E2E encryption and token auth?

## References

- [Decision 011: Efforts Are KG Nodes](011-efforts-are-kg-nodes.md)
- [Decision 012: Sessions as Audit Logs](012-session-as-audit-log.md)
- [Vault Decision 001: Storage Architecture](D:\Dev\Open-Intelligence\vault\docs\decisions\001-storage-architecture.md)
- [Vault Roundtable 001: Distributed Storage Tech](D:\Dev\Open-Intelligence\vault\docs\roundtables\001-distributed-storage-tech.md)
