# Slice 12e: Directed Graph Traversal

**Status:** proposed
**Depends on:** 12a (graph_walk), 08c (node linking), 08h (because_of staleness)
**Date:** 2026-03-09

## Problem

`graph_walk` is a **search expansion** tool — it finds nearby nodes to boost query relevance. It treats all edges as bidirectional pipes and ignores edge types. This means the knowledge graph can't answer **reasoning questions**:

- "Why do I believe X?" (follow inbound `supports` chains)
- "What depends on X?" (follow outbound `supports`/`because_of` from X)
- "What breaks if I change my mind about X?" (impact analysis)
- "Show me the evidence for this high-confidence node" (confidence explanation)

These are the queries that differentiate a knowledge graph from a vector store.

## What Changes

**One new function** in `search.py` + **one new function** in `confidence.py` + **one new MCP tool**.

### 1. `traverse()` in `search.py` (~50 lines)

```python
def traverse(
    start_id: str,
    knowledge: dict,
    edge_types: set[str] | None = None,   # None = all
    direction: str = "inbound",            # "inbound" | "outbound" | "both"
    max_hops: int = 3,
) -> list[dict]:
    """Directed, edge-type-filtered graph traversal.

    Returns [{node_id, hop, edge_type, via}] — the path, not just endpoints.
    """
```

Unlike `graph_walk` (which scores and ranks), `traverse` returns the **path structure** — which node led to which, via what edge type, at what hop distance. This is BFS with filters.

### 2. `explain_confidence()` in `confidence.py` (~30 lines)

```python
def explain_confidence(node_id: str, graph: dict) -> dict:
    """Return the support/contradiction tree that produces this node's confidence.

    Returns {
        node_id, level, score,
        support_chain: [{node_id, edge_type, source, summary, score}],
        contradiction_chain: [{node_id, edge_type, source, summary, score}],
    }
    """
```

Calls `traverse(node_id, graph, edge_types={"supports","exemplifies"}, direction="inbound")` for the support chain, same with `{"contradicts"}` for contradictions. Attaches the PageRank score from `compute_confidence` to each node in the chain. This makes confidence **inspectable** — the agent can explain *why* something is high confidence.

### 3. `mcp_traverse` MCP tool

Exposes `traverse` + `explain_confidence` to the agent. Two modes:

- `traverse` mode: "follow supports edges inbound from fact-042, max 3 hops"
- `explain` mode: "explain why fact-042 is high confidence"

## What Doesn't Change

- `graph_walk` stays as-is — it's the search expansion layer, doing its job well
- `query_knowledge` stays as-is — still uses `graph_walk` for search
- No schema changes, no new edge types, no data migration

## Scope

- ~80 lines of new code across `search.py` and `confidence.py`
- ~30 lines in `mcp_server.py` for the tool
- Tests: pure graph traversal, no LLM calls, free to run
- Zero cost at runtime — pure graph operations, no API calls

## What This Enables

| Query | How |
|-------|-----|
| "Why do I believe X?" | `traverse(X, edge_types={supports}, direction=inbound)` |
| "What depends on X?" | `traverse(X, edge_types={supports, because_of}, direction=outbound)` |
| "What breaks if X is wrong?" | outbound traverse + flag nodes whose confidence would drop |
| "Explain this confidence" | `explain_confidence(X)` returns the full tree |
| "Deep staleness check" | `traverse(X, edge_types={because_of}, direction=outbound)` — finds all downstream nodes, checks for superseded/contested ancestors. Subsumes the icebox `because_of` multi-hop item |

## Relationship to Existing Roadmap

- **Subsumes** icebox item "`because_of` multi-hop" — deep chain staleness becomes a `traverse` call
- **Delivers** the "multi-hop traversal" need identified in `rag-architecture-reference.md`
- **Enables** the "walkable reasoning chains" described in `topological-truth-paper.md:219`
- **Prerequisite for** hierarchical effort KGs (expand/collapse traversal needs directed edge following)

## Not In Scope

- Modifying `graph_walk` (it stays as search expansion)
- LLM reranking of traversal results (that's 12d)
- Cross-effort traversal (that's the hierarchical KGs item)
