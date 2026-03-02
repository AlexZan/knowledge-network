# Decision 015: Graph-Aware Search & Bulk Ingestion Architecture

**Date**: 2026-03-02
**Status**: Brainstorming

---

## Context

The knowledge graph needs to scale from ~5 nodes (current) to 10,000-20,000 nodes when ingesting the Open Systems documentation corpus (hundreds of documents spanning two decades). The current flat keyword-Jaccard search and linker will not scale — it misses semantic matches, ignores graph structure, and does O(n) comparisons per insertion.

Bulk ingestion also introduces a conflict resolution problem: documents from different eras will contradict each other, and the system needs to surface these conflicts intelligently without auto-resolving subjective decisions.

## Decision

### 1. Graph-Aware Retrieval (replaces flat scan)

Three-layer candidate discovery:

**Layer 1 — Seed matching (cheap, fast)**
Find initial entry points via keyword overlap (current) or embeddings (future). Only needs to find *some* relevant nodes — doesn't need to be exhaustive.

**Layer 2 — Graph walk (free, uses existing structure)**
From seed matches, follow edges 1-2 hops out. The graph itself becomes the search index. Properties:
- 1-hop neighbors score 0.7x the seed's match score
- 2-hop neighbors score 0.4x
- Nodes reachable via multiple paths get additive scores (convergence signal)
- All edge types are walkable, with different semantics:
  - `supports`: walk freely, high relevance
  - `contradicts`: walk freely, also high relevance (discovers opposing clusters)
  - `supersedes`: prefer walking toward newer node
  - `because_of`: walk both ways (causal chains)

**Layer 3 — LLM classification (expensive, selective)**
Top-15 candidates after layers 1+2 go to LLM for relationship classification. Batch prompt (one call for all candidates) instead of per-pair calls.

**Key property**: As the graph gets denser, search gets *better* not worse. Edges act as bridges between concepts that share no keywords.

### 2. Two-Pass Ingestion

**Pass 1 — Extract** (parallelizable, no linking)
- Parse documents (mixed formats: markdown, PDF, text)
- Extract metadata (date, title, source path, section)
- Chunk large docs into discrete sections
- LLM extracts knowledge nodes from each chunk
- Temporal metadata preserved — doc date becomes node provenance
- Order-independent, embarrassingly parallel

**Pass 2 — Link** (sequential, full graph visibility)
- With all nodes extracted, run the graph-aware linker
- Full picture available — no ordering dependency
- Natural clusters emerge as nodes link
- Contradictions detected across eras

### 3. Two-Mode Conflict Resolution

**Subjective conflicts** (decisions, preferences, architecture):
- Require user sign-off with reason and signature
- Sign-off creates a `signed_decision` node with edges to all supporting evidence
- The sign-off is the capstone, not the sole basis — graph topology should already show the reasoning chain
- System prioritizes: obvious conflicts get fast rubber-stamp prompt, genuinely ambiguous ones flagged for real input

**Objective/factual conflicts**:
- Auto-resolved when existing graph support is overwhelming
- e.g., "VS Code doesn't run on Linux" superseded by 12 nodes saying it does
- No user sign-off needed

### 4. Recency Is Not Authority, Topology Is

A new node does not automatically supersede an old one just because it's newer. A 2023 doc could introduce a faulty conclusion. Authority comes from:
- Number of supporting edges from well-supported nodes
- Brainstorm/debate nodes pointing to it
- Independent sources confirming it
- *Then* user sign-off as final capstone

A node with 10 supports from 2014 outranks a node with 1 support from 2023 — until the 2023 node accumulates its own support network.

### 5. Ingestion Report

After batch ingestion, produce an interactive report:

```
Ingested 200 nodes from 2023-architecture/
  147 linked cleanly (supports existing knowledge)
  38 new topics (no existing matches)
  15 contradictions detected:

CONFLICT 1: Strong recommendation
  REST (12 supports, 3 brainstorms) vs SOAP (10 supports, all pre-2020)
  System confidence: REST — sign off? [Y/reason]

CONFLICT 7: Genuinely ambiguous
  PostgreSQL (4 supports) vs MongoDB (3 supports, 2 recent brainstorms)
  No clear winner — needs your input
```

### 6. Batch LLM Efficiency

At scale, per-pair LLM calls are too expensive. Use batch prompts:

```
New node: "Use REST for all integrations"

Classify relationship to each:
1. [decision] Use SOAP for all integrations
2. [fact] SOAP supports WS-Security
3. [fact] REST APIs use JSON by default
...

For each, respond: supports / contradicts / none
```

One LLM call instead of 15.

## Future Optimizations

- **Cluster detection**: As graph grows, natural topic clusters form. Use as coarse search index — new "database" node only compared against database cluster + neighbors.
- **Embedding layer**: Add vector embeddings for seed matching when keyword overlap ceiling is hit. Hybrid keyword + embedding + graph walk.
- **Schema-detection agent**: Auto-propose new node types discovered during ingestion.

## Rollout Plan

1. Small test batch (5-10 docs) — validate extraction + linking + conflict detection
2. Medium batch (50-100 docs) — validate scale, cost, and report quality
3. Full Open Systems corpus — hundreds of docs, decades of history

## Related

- [Decision 013](013-unified-kg-architecture.md) — Unified KG architecture
- [Slice 12: Bulk Document Ingestion](../slices/README.md) — Roadmap entry
- [Slice 13: Search Infrastructure](../slices/README.md) — Graph-aware retrieval
