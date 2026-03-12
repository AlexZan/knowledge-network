# Linking Pipeline Optimization: Multi-Pass vs First-Pass

**Date:** 2026-03-11
**Context:** Analysis during v4 KG rebuild (2,361 nodes, 0 edges). Evaluated what can be done cheaply in the first pass vs requiring separate expensive passes.

## Current Pipeline (Sequential Passes)

The linking pipeline currently runs as separate stages, each requiring a full graph scan:

1. **Extraction** — LLM extracts nodes from conversations/documents (already done)
2. **Auto-linking** — `auto_link_same_group()` creates `related_to` edges within same-source nodes (implemented, not yet run)
3. **Cross-group LLM linking** — `link_new_nodes()` finds candidates via keyword Jaccard, LLM classifies as `supports`/`contradicts`/`none`
4. **Embedding** — `ensure_embeddings()` generates vectors via Ollama (nomic-embed-text)
5. **Clustering** — `find_clusters()` groups near-duplicates by cosine similarity, `synthesize_concepts()` creates `principle` nodes
6. **Directed traversal** — Proposed in PR #8 (`traverse()` + `explain_confidence()`)

Each pass loads the full graph, scans/modifies, saves. Some can be combined.

## What Can Move to the First Pass (Free or Cheap)

### Already implemented

**Same-conversation auto-linking (step 2)**
- Groups nodes by provenance URI (strip `#fragment`), creates `related_to` edges between all pairs within each group
- Zero LLM cost — purely structural
- Creates intra-conversation subgraphs: if a conversation produced 8 nodes, that's 28 `related_to` edges forming a clique
- For 2,361 nodes across ~205 sources, this creates substantial graph depth before any LLM work

**Cross-group candidate filtering**
- `find_candidates()` now accepts `exclude_same_group=True`
- Same-conversation nodes are filtered from candidate lists, freeing slots for cross-source nodes
- This means the LLM linking pass focuses entirely on cross-source bridges — no wasted calls on pairs that are already linked

### Could be combined with auto-linking pass

**Embedding generation (step 4)**
- `embed_node()` is independent of edge structure — only needs the node summary
- Could run during or immediately after extraction, before any linking
- Currently deferred to a separate `ensure_embeddings()` call
- **Benefit**: Embeddings available for clustering sooner; no second graph load
- **Caveat**: Requires Ollama running (local service dependency). On battery/no-GPU this blocks. Keep as optional.

**Intra-conversation ordering**
- Nodes from the same conversation have turn numbers in their provenance URI (`#turn-0`, `#turn-3`)
- The auto-linking pass already groups by conversation — it could also create ordered chains (`precedes` edges) within conversations
- Currently not implemented. Would need a schema change (new edge type) and careful evaluation of whether ordering adds value
- **Assessment**: Probably over-engineering. `related_to` cliques are sufficient. Turn order is preserved in provenance URIs if needed. See icebox item "Process/sequence edge types."

## What Requires Separate Passes

### Cross-group LLM linking (step 3)

- Needs keyword index built from all nodes (can't do incrementally during extraction — later nodes need to see earlier nodes)
- Each node-pair classification costs an LLM call
- Batch classification (N candidates per prompt) helps but still O(nodes) prompts
- **Optimization already done**: `exclude_same_group` ensures we don't waste LLM calls on already-linked pairs
- **Future optimization**: Run on local model (qwen3:8b via Ollama) for free linking. Quality needs testing.

### Clustering + concept synthesis (step 5)

- Requires embeddings for all nodes (depends on step 4)
- Cosine similarity clustering is O(n²) but fast in numpy
- Concept synthesis requires LLM calls (one per cluster)
- Must run after linking to avoid synthesizing concepts from duplicate/contradictory nodes
- **Can't move earlier**: Depends on both embeddings and edges

### Directed traversal (step 6, PR #8)

- Pure graph operation — needs edges to exist but doesn't create them
- Natural consumer of the graph structure created by steps 2-5
- `traverse(X, edge_types={supports}, direction=inbound)` walks the support chains that cross-group linking created
- `explain_confidence(X)` visualizes why topology produces a given confidence level
- **Timing**: Implement after first full linking run, when we have real edges to traverse

## Graph Structure After All Passes

```
[Conv A nodes] ── related_to clique ──
       │
       │ supports (LLM-classified)
       ▼
[Conv B nodes] ── related_to clique ──
       │
       │ contradicts (LLM-classified)
       ▼
[Conv C nodes] ── related_to clique ──
       │
       │ exemplifies (clustering)
       ▼
[Principle node] (synthesized concept)
```

Intra-conversation cliques provide density. Cross-group typed edges provide reasoning structure. Principle nodes provide abstraction. `traverse()` walks this full structure.

## Key Insight: Same-Group Linking Saves LLM Budget

For 2,361 nodes across ~205 sources (avg ~11.5 nodes/source):
- Auto-linking creates ~11.5 choose 2 = ~66 edges per source × 205 sources = **~13,500 `related_to` edges for free**
- Without auto-linking, LLM would classify many of these pairs (shared keywords within conversations are high)
- With `exclude_same_group`, those candidate slots go to cross-source pairs instead
- Net effect: same LLM budget produces more valuable cross-source edges

## Cosine Similarity for Candidate Finding: Not Needed Yet

Analyzed 2026-03-11. Keyword Jaccard already saturates (80% of nodes hit the 8-candidate cap). Candidates are high quality and cross-source. Domain vocabulary is concentrated enough that shared keywords ARE the right signal. Cosine would only help if nodes used completely different terminology for the same concept — rare in a single-author framework. Revisit for multi-author KGs.

## Recommended Execution Order (When Plugged In)

1. `auto_link_same_group()` — run on all 2,361 node IDs. Free, ~seconds.
2. `ensure_embeddings()` — generate vectors via nomic-embed-text. Free (local), ~minutes on GPU.
3. `link_new_nodes()` with `exclude_same_group=True` — cross-group LLM linking. Test qwen3:8b quality first, then full run.
4. `find_clusters()` + `synthesize_concepts()` — after embeddings + edges exist.
5. Evaluate `traverse()` need — does dogfooding show 1-hop confidence data is insufficient?
