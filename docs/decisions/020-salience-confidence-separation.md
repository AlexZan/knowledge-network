# Decision 020: Salience, Corroboration, and Logical Confidence Are Distinct

**Status**: Implemented
**Date**: 2026-03-04

---

## Revised Scope (2026-03-04)

### What's already resolved

[Decision 019](019-semantic-vs-logical-edges.md) separated semantic and logical edges. `confidence.py` now filters on `get_logical_edge_types()` — `related_to` edges are **excluded** from PageRank. The original problem statement below ("all three flow through the same PageRank computation") is no longer true. Confidence is already logically clean. Corroboration (`independent_sources`) is already tracked and working.

### What remains — three gaps

1. **Salience metric.** No way to answer "what are the core concepts of this domain?" Confidence measures how well-argued a claim is, not how central it is. A niche claim with 3 independent supporters ranks higher than a foundational concept discussed in every document but with only 1 explicit `supports` edge. Salience would rank by semantic density — nodes with many `related_to` connections surface as the concepts documents keep returning to.

2. **Edge weights by reasoning quality.** All `supports` edges contribute equally to PageRank. The linker writes a `reasoning` field on edges it can justify, but `confidence.py` doesn't read it. A reasoned edge like `"Both assert that measurement creates rather than reveals physical properties"` counts the same as a blind guess with no justification. Proposed: 1.0 weight for edges with reasoning, 0.5 without.

3. **Concept nodes from embedding clusters.** When multiple documents state the same claim in different words, they become separate nodes with no connection. The cluster pass finds them via cosine similarity (pure math, no LLM). The synthesis pass generates a concept node linking them via `exemplifies`. Each original survives with its provenance. The concept node inherits corroboration from its independent instances.

### Trigger update

- ~~Decision 019 implemented~~ — done.
- ~~Rust port~~ — deferred; implementing in Python.
- Ready to implement now.

---

## Problem (original, partially stale)

~~The current confidence system conflates three different epistemic signals into a single number:~~

> **Note**: The conflation described below was partially resolved by [Decision 019](019-semantic-vs-logical-edges.md). `related_to` edges no longer affect PageRank. The remaining issue is edge weight blindness (no reasoning-based weighting) and the absence of a salience metric. See Revised Scope above.

The current confidence system conflates three different epistemic signals into a single number:

1. **Salience** — how central/prominent a concept is to the domain
2. **Corroboration** — how many independent sources mention it
3. **Logical confidence** — how well-justified it is through reasoned support chains

~~All three currently flow through the same PageRank computation over `supports`/`contradicts` edges, with all edges weighted equally regardless of whether they represent logical implication or semantic proximity.~~

~~This conflation causes two concrete problems:~~
~~- A `preference` node expressing "I want to explore X" inflates confidence in claims about X via `supports` edges~~
- A strong logical argument with explicit reasoning weighs the same as a linker's best guess with no justification

---

## Decision

### Three distinct metrics

| Metric | Question | What earns it | Edges that contribute |
|--------|----------|---------------|-----------------------|
| **Salience** | How central is this concept to the domain? | Semantic density — how much attention it receives across documents | `related_to`, all edges (count of references) |
| **Corroboration** | How many independent sources mention it? | Unique `source` values across the node + its logical supporters | `supports`, `exemplifies`, `contradicts` (logical only) |
| **Logical confidence** | How well-justified is this claim? | Reasoned support chains, weighted by reasoning quality | `supports` (with reasoning weighting), `exemplifies` |

Confidence (the existing system) maps to **logical confidence**. Salience is new. Corroboration is the existing `independent_sources` count — which is already logically clean and remains unchanged.

### Edge weights by reasoning quality

All logical edges (`supports`, `exemplifies`) are not equal. An explicit justification is stronger evidence than a topological guess:

| Edge type | Reasoning field present? | Confidence weight |
|-----------|--------------------------|-------------------|
| `related_to` | — | 0 (salience only, not confidence) |
| `supports` | No | 0.5 |
| `supports` | Yes | 1.0 |
| `exemplifies` | — | 1.0 (definitional — instance of a concept) |
| `contradicts` | No | 0.5 |
| `contradicts` | Yes | 1.0 |

The linker already writes a `reasoning` field on edges when it can justify one. The confidence computation needs to read this field and apply the weight multiplier.

### Living concept nodes (concept hierarchy)

Rather than deduplicating similar claims across documents, the system builds a hierarchy:

- **Instance nodes**: each document's claim survives as its own node, with its exact wording and source provenance
- **Concept nodes**: emerge from embedding clusters — synthesized by the LLM from all instance nodes in the cluster
- **Edges**: each instance → concept via `exemplifies`

The concept node's logical confidence = high when its `exemplifies` instances come from 3+ independent sources, with reasoning. Its salience = high when many semantically related nodes exist across the graph.

**Concept nodes evolve**: when a new instance is added to a cluster, the concept node is marked `dirty` and re-synthesized on the next synthesis pass (one LLM call per concept update). All instances survive — no merging, no loss of nuance.

**What is a concept node's type?** The existing `principle` type with `exemplifies` edges already supports this pattern. The missing piece is generating principle/concept nodes from embedding clusters during ingestion, not just from logical convergence post-hoc.

### Implementation passes (post-embed)

After the existing ingest pipeline (parse → extract → write → link → embed), two new optional passes:

1. **Cluster pass** (cheap): scan embedding space for cosine similarity clusters above threshold — no LLM, pure math
2. **Synthesis pass** (one LLM call per new/dirty concept): generate canonical concept summary from instance nodes, write/update concept node, link instances via `exemplifies`

---

## What salience enables

- `query_knowledge` can sort by salience to answer: *"what are the core concepts of this theory?"*
- High-salience + low-confidence = a central claim that lacks logical backing — worth investigating
- High-salience + high-confidence = a core, well-supported claim
- Low-salience + high-confidence = a niche but logically solid fact
- The `related_to` edge graph (semantic layer) is the substrate salience is computed over

---

## What this does NOT change

- Existing confidence levels (low/medium/high/contested) and their thresholds — unchanged
- Existing `supports`/`contradicts`/`exemplifies` semantics — unchanged
- The PageRank algorithm — extended with edge weight multiplier, otherwise identical
- No re-ingestion of existing data required; edge weights default to 0.5 when reasoning absent

---

## Relationship to other decisions

- **Decision 019** (semantic vs logical edges): `related_to` is the semantic edge that feeds salience but not confidence. This decision specifies *what* `related_to` contributes.
- **Slice 8g** (The Agent Generalizes): concept nodes via clustering is the same pattern as principle nodes via logical convergence — same node type (`principle`), different trigger (embedding clusters vs logical convergence). Both mechanisms produce the same node structure.
- **Slice 12b** (Embedding Search): embeddings already exist. The cluster pass is a new consumer of the same embedding vectors.

---

## Trigger

~~Implement when:~~
~~1. Decision 019 (`related_to` edge type) is implemented — salience needs the semantic layer to exist~~
~~2. Rust port reaches the ingestion pipeline phase — the cluster + synthesis passes are natural pipeline stages~~
~~3. Or: if Python analysis of the physics theory KG shows that near-duplicate nodes are creating significant noise after 5+ documents~~

All prerequisites met. **Implemented** (2026-03-04):
- Phase 1: Edge weight by reasoning quality (`confidence.py` — 0.5x for unreasoned, 1.0x for reasoned)
- Phase 2: Salience metric (`compute_salience()`, `sort_by` param in `query_knowledge` + MCP)
- Phase 3: Concept nodes from embedding clusters (`cluster.py` — `find_clusters()`, `synthesize_concepts()`, opt-in pipeline stages). Default threshold tuned from 0.85 to 0.90 after empirical evaluation (0.85 conflated distinct claims; 0.90 catches only genuine near-duplicates).
