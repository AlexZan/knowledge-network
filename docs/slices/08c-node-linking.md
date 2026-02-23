# Slice 8c: Node Linking (Contradiction Detection + Relationship Edges)

**Goal**: When a new knowledge node is added, find related existing nodes and classify the relationship (supports, contradicts, or none). This is the foundation for confidence scoring (8d) and data ingest (future).

**Thesis**: 4 (Conflict Resolution) — "Not all conflicts are equal. Truth conflicts and preference conflicts require different resolution."

---

## Core Hypothesis

> New knowledge should not land in the graph in isolation. A specialized linker agent can compare a new node against existing candidates and produce typed edges — enabling contradiction detection, support reinforcement, and eventually confidence scoring.

---

## Architecture

### Two-Stage Pipeline

Every new node passes through:

```
New node
    ↓
Stage 1: Candidate Retrieval
    "Which existing nodes might be related?"
    → Keyword overlap on summaries (MVP)
    → Same node_type filter
    → Returns top-N candidates
    ↓
Stage 2: Linker Agent (small model)
    Input: new node + each candidate (pairwise)
    Instructions: procedural comparison
    Output: edge type (supports / contradicts / none) per pair
    ↓
Persist edges + flag contradictions for user
```

### Why Two Stages

- **Retrieval** is cheap (string matching, no LLM) — filters the graph to a small candidate set
- **Linking** is expensive (LLM call per pair) — only runs on candidates, not the whole graph
- At small graph sizes (<100 nodes), retrieval can be brute-force. Embeddings are a future optimization, not an MVP requirement.

### Both Modes Use the Same Pipeline

| Mode | Entry point | What happens |
|------|------------|--------------|
| **Chat** | `add_knowledge()` or `extract_knowledge()` on close | Each new node → retrieval → linker → persist |
| **Ingest** (future) | Document chunker feeds nodes | Same pipeline, called in a loop |

By building the linker as a standalone function, ingest mode is just a different front door.

---

## Retrieval: `find_candidates()`

```python
def find_candidates(
    new_node: dict,
    graph: dict,
    max_candidates: int = 5,
) -> list[dict]:
    """Find existing nodes that might relate to the new node.

    MVP: keyword overlap between summaries.
    Future: embedding similarity, graph neighborhood.

    Returns list of candidate nodes, scored and sorted.
    """
```

### MVP Strategy: Keyword Overlap

1. Tokenize new node summary into keywords (lowercase, strip stopwords)
2. For each existing active node, tokenize its summary
3. Score = number of overlapping keywords / total unique keywords (Jaccard)
4. Filter: score > 0.1 (at least some overlap)
5. Return top `max_candidates` sorted by score

### Why Not Embeddings Yet

- Graph will be <100 nodes for months
- Keyword overlap is sufficient for "are these about the same topic?"
- Adding an embedding model is a dependency we don't need yet
- The interface (`find_candidates → list[dict]`) stays the same when we swap in embeddings later

---

## Linker Agent: `link_nodes()`

```python
def link_nodes(
    new_node: dict,
    candidate: dict,
    model: str = LINKER_MODEL,
) -> dict:
    """Compare two nodes and classify their relationship.

    Returns: {"edge_type": "supports"|"contradicts"|"none", "reasoning": "..."}
    """
```

### Procedural Prompt (Small Model)

Following the "small models need procedural instructions" lesson:

```
Compare these two knowledge nodes and classify their relationship.

Node A (new): [{node_type}] {summary}
Node B (existing): [{node_type}] {summary}

Follow these steps:
1. Identify the core claim in Node A
2. Identify the core claim in Node B
3. Are they about the same topic? If NO → output "none"
4. If same topic: does Node A agree with Node B? If YES → output "supports"
5. If same topic: does Node A disagree with or replace Node B? If YES → output "contradicts"

Respond with ONLY a JSON object:
{"edge_type": "supports"|"contradicts"|"none", "reasoning": "one sentence"}
```

### Model Choice

- Default: `LINKER_MODEL` (configurable, start with same DEFAULT_MODEL)
- This is classification, not generation — a smaller/cheaper model works
- Can swap to qwen3:8b or similar once we validate the prompt

---

## Contradiction Handling

When the linker returns `contradicts`:

### MVP: Flag + Persist

1. Create the `contradicts` edge in the graph
2. Mark both nodes with `has_contradiction: true`
3. Show a banner to the user: `"⚠ Contradiction: [new node] vs [existing node]"`
4. Do NOT auto-resolve — user decides

### Why Not Auto-Resolve Yet

- Truth vs preference classification (Thesis 4) is a separate concern
- Auto-resolution needs confidence scores (8d)
- For MVP, surfacing contradictions is the value — resolution is 8d+

---

## Integration Points

### `add_knowledge()` in `tools.py`

After persisting the new node, call the linking pipeline:

```python
# Existing: persist node to knowledge.yaml
# New: find candidates and link
candidates = find_candidates(new_node, knowledge)
for candidate in candidates:
    result = link_nodes(new_node, candidate, model)
    if result["edge_type"] != "none":
        # Persist edge
        # If contradicts: flag for user
```

### `extract_knowledge()` in close_effort flow

Each auto-extracted node already goes through `add_knowledge()` — linking happens automatically.

### Banner in `orchestrator.py`

Update `add_knowledge` banner to show detected relationships:

```
--- Knowledge added: [fact] fact-003 ---
  Supports: [fact-001] "API uses JWT with RS256"
  ⚠ Contradicts: [decision-002] "Use session cookies for auth"
```

---

## File Changes

| File | Change |
|------|--------|
| `src/oi/linker.py` | **New file**: `find_candidates()`, `link_nodes()` |
| `src/oi/tools.py` | `add_knowledge()` calls linking pipeline after persist |
| `src/oi/orchestrator.py` | Update `add_knowledge` banner to show edges |
| `tests/test_linker.py` | **New file**: unit tests for retrieval + linker |
| `tests/test_tools.py` | Update `add_knowledge` tests for linking integration |
| `tests/test_e2e_real_llm.py` | E2E test: add contradicting knowledge, verify edge created |

---

## Testing Strategy

| What | How | LLM needed? |
|------|-----|-------------|
| `find_candidates` keyword matching | Unit test | No |
| `find_candidates` returns empty for unrelated nodes | Unit test | No |
| `find_candidates` ranks by relevance | Unit test | No |
| `link_nodes` parses valid JSON response | Unit test (mock LLM) | No |
| `link_nodes` returns "none" on parse failure | Unit test (mock LLM) | No |
| `link_nodes` handles markdown fences | Unit test (mock LLM) | No |
| `add_knowledge` creates edges via linker | Unit test (mock linker) | No |
| `add_knowledge` flags contradictions | Unit test (mock linker) | No |
| Contradiction banner shown to user | Unit test | No |
| Full flow: add fact, add contradicting fact | E2E test | Yes |
| Close effort extracts nodes with linking | E2E test | Yes |

---

## Scope

### In Scope

- `find_candidates()` with keyword-based retrieval
- `link_nodes()` with procedural LLM prompt
- Edge creation (supports/contradicts) on `add_knowledge`
- Contradiction flagging in banners
- Works for both manual `add_knowledge` and auto-extraction on close

### Out of Scope (Later Slices)

| Feature | Slice | Why Deferred |
|---------|-------|--------------|
| Confidence scoring from topology | 8d | Needs edges to exist first |
| Truth vs preference classification | 8d | Needs confidence context |
| Auto-resolution of contradictions | 8d | Needs classification + confidence |
| Embedding-based retrieval | Future | Keyword overlap sufficient at current scale |
| Data ingest mode | Future | Same pipeline, different entry point |
| `query_knowledge` tool | 8e | Convenience, not core thesis |

---

## Success Criteria

- [ ] Adding a supporting fact creates a `supports` edge
- [ ] Adding a contradicting fact creates a `contradicts` edge and shows banner
- [ ] Unrelated facts create no edges
- [ ] Linking works for both manual add and auto-extraction on close
- [ ] `find_candidates` returns empty for graphs with no related nodes
- [ ] `link_nodes` fails gracefully (returns "none") on LLM errors
- [ ] Existing tests still pass (linking is additive)

---

## Future: Embedding Retrieval

When the graph exceeds ~100 nodes, keyword overlap won't scale. The upgrade path:

1. Add embedding generation on node creation (store in `knowledge.yaml` or separate index)
2. Replace `find_candidates` internals with cosine similarity on embeddings
3. Interface stays the same — `find_candidates(new_node, graph) → list[dict]`

This is a swap-in optimization, not a redesign. The RAG architecture reference (`docs/research/rag-architecture-reference.md`) details the hybrid approach: vector for "find similar", graph for "find connected".

---

## Related Documents

- [RAG Architecture Reference](../research/rag-architecture-reference.md) — Vector vs Graph retrieval
- [Thesis](../thesis.md) — Thesis 4 (Conflict Resolution), Thesis 5 (Emergent Confidence)
- [Roadmap](README.md) — Slice 8 sub-slice plan
