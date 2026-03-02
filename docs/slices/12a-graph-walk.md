# Slice 12a: Graph Walk Search

**Status**: Spec
**Depends on**: Slice 11b (Provenance Linking)
**Blocks**: Slice 12d (Hybrid Retrieval)

---

## Problem

Both `query_knowledge()` and `find_candidates()` use **keyword-only Jaccard similarity** to find matching nodes. This misses:

- **Related nodes with different vocabulary**: A fact about "REST APIs" won't match a query for "HTTP endpoints" even though they're connected by edges in the graph.
- **Neighborhood context**: A decision about authentication links to 5 supporting facts. Searching for one of those facts should surface the others, but keyword matching treats each node independently.
- **Convergence signals**: A node reachable via multiple independent paths is more relevant than one reachable via a single path, but flat search can't detect this.

The graph structure already contains this information via edges — we just don't use it during search.

## Solution

Add a **graph walk layer** between keyword seed matching and result ranking. After finding initial seed matches via keywords (existing logic), expand the candidate set by following edges 1-2 hops outward. Score decays with distance; convergence (multiple paths) boosts score.

### Algorithm

```
1. Keyword seed matching (existing Jaccard logic)
   → produces seed_matches: [{node_id, keyword_score}]

2. Graph walk expansion
   For each seed match:
     - Follow all edges 1 hop out → score = seed_score * HOP_1_DECAY (0.7)
     - Follow all edges 2 hops out → score = seed_score * HOP_2_DECAY (0.4)
     - Skip already-seen nodes (no cycles)
     - Skip superseded nodes

3. Score aggregation
   If a node is reached via multiple paths, scores ADD (convergence signal)
   Final score = max(keyword_score, 0) + sum(walk_scores)

4. Return top-N candidates sorted by final score
```

### What edges to walk

All edge types are walkable, bidirectionally:

| Edge type | Walk behavior |
|-----------|---------------|
| `supports` | Walk freely, high relevance |
| `contradicts` | Walk freely — opposing clusters are still relevant |
| `exemplifies` | Walk freely — connects facts to principles |
| `because_of` | Walk freely — causal chains |
| `supersedes` | Walk toward **newer** node only (old → new, not new → old) |

Bidirectional means: if A→B is a "supports" edge, walking from B also discovers A.

### Where it plugs in

**Two callers, one function:**

```python
# New: src/oi/search.py
def graph_walk(
    seeds: list[dict],          # [{node_id, score}] from keyword matching
    knowledge: dict,            # full graph (nodes + edges)
    max_hops: int = 2,          # how far to walk
    hop_1_decay: float = 0.7,   # score multiplier for 1-hop
    hop_2_decay: float = 0.4,   # score multiplier for 2-hop
) -> list[dict]:
    """Expand seed matches by walking the graph. Returns [{node_id, score}]."""
```

**Caller 1: `query_knowledge()`** in `knowledge.py`
- Currently: keyword scan → filter → return results
- After: keyword scan → **graph_walk()** → filter → return results
- User-facing search gets richer results

**Caller 2: `find_candidates()`** in `linker.py`
- Currently: keyword scan → top 5
- After: keyword scan → **graph_walk()** → top N
- Auto-linker discovers candidates via graph neighborhood, not just keyword overlap
- May increase `max_candidates` from 5 to 8-10 since walk surfaces more relevant candidates

### Example

Graph state:
```
fact-001: "REST APIs use JSON"
  ─supports─→ decision-003: "Use REST for integrations"
  ─supports─→ fact-004: "JSON is human-readable"
fact-002: "SOAP uses XML"
  ─contradicts─→ decision-003
```

Query: "JSON format"
- **Keyword seed**: fact-001 (score 0.5), fact-004 (score 0.3)
- **Walk from fact-001 (1-hop)**: decision-003 (0.5 × 0.7 = 0.35), fact-004 (0.5 × 0.7 = 0.35)
- **Walk from fact-004 (1-hop)**: fact-001 (0.3 × 0.7 = 0.21)
- **Walk from fact-001 (2-hop via decision-003)**: fact-002 (0.5 × 0.4 = 0.20)
- **Walk from fact-004 (2-hop via fact-001)**: decision-003 (0.3 × 0.4 = 0.12)
- **Aggregated scores**:
  - fact-001: 0.5 (keyword) + 0.21 (walk from fact-004) = **0.71**
  - fact-004: 0.3 (keyword) + 0.35 (walk from fact-001) = **0.65**
  - decision-003: 0.35 (1-hop from fact-001) + 0.12 (2-hop from fact-004) = **0.47** (not a keyword match, discovered via walk!)
  - fact-002: **0.20** (2-hop discovery, opposing cluster)

Without graph walk, decision-003 and fact-002 would be invisible.

## Changes

### New: `src/oi/search.py`

Core graph walk implementation (~60-80 lines):

```python
def graph_walk(seeds, knowledge, max_hops=2, hop_1_decay=0.7, hop_2_decay=0.4):
    """Expand seed matches by walking graph edges."""

def _build_adjacency(knowledge):
    """Build bidirectional adjacency list from edges. Supersedes edges are directional."""
```

### Modified: `src/oi/knowledge.py`

`query_knowledge()` calls `graph_walk()` after keyword matching:

```python
# Before: keyword_matches → filter → return
# After:  keyword_matches → graph_walk() → filter → return
```

Minimal change — insert one function call between existing keyword scoring and filtering.

### Modified: `src/oi/linker.py`

`find_candidates()` calls `graph_walk()` after keyword matching:

```python
# Before: keyword_scores → top 5
# After:  keyword_scores → graph_walk() → top max_candidates
```

Consider increasing `max_candidates` default from 5 to 8 since walk surfaces more relevant candidates. The LLM classification cost is still bounded (8 calls max, or 1 batch call when 12c lands).

### Tests

- **Unit: `test_search.py`**
  - Test 1-hop expansion from single seed
  - Test 2-hop expansion reaches distant nodes
  - Test convergence: node reachable via 2 paths scores higher than via 1
  - Test supersedes edge only walks toward newer node
  - Test skip superseded/inactive nodes
  - Test empty graph returns seeds unchanged
  - Test cycle handling (A→B→A doesn't loop)

- **Integration: `test_knowledge.py`**
  - Test query_knowledge with graph walk finds neighborhood matches
  - Test linker find_candidates surfaces walk-discovered candidates

## Design Notes

- **Graph walk is deterministic** — no LLM calls, no API cost. Pure graph traversal.
- **Backward compatible** — keyword matching still happens first. Walk only enriches. If the graph has no edges, behavior is identical to today.
- **Performance**: At 27 nodes this is instant. At 10K nodes, the walk is still O(seeds × edges_per_node^hops) which is bounded by `max_hops=2`. The adjacency list is built once per call.
- **Decay constants (0.7, 0.4)** are initial values. We can tune them based on dogfooding. They should probably be configurable but defaulted.
- **This slice does NOT change the LLM classification prompt.** That's 12c (batch LLM). This slice only changes which candidates get sent to the LLM.

## Success Criteria

After implementing, re-run the query that produced issue #4's false positive. The graph walk should surface more relevant context nodes, giving the linker better candidates. Not guaranteed to fix the false positive (that needs prompt work in 12c), but should reduce the problem by providing richer context.

## Not In This Slice

- Embeddings (12b) — different seed matching, not graph walk
- Batch LLM classification (12c) — prompt changes, not candidate discovery
- Hybrid pipeline wiring (12d) — combines 12a+12b+12c
- Configurable decay constants via schema/config (future)
