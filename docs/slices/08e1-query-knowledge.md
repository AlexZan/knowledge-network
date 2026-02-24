# Slice 8e-1: query_knowledge Tool

## Context

The knowledge graph stores facts, preferences, and decisions as nodes with edges (supports, contradicts). Nodes are shown in the system prompt, but the LLM has no tool to search or filter them — it can only see the flat list. As the graph grows, the system prompt listing becomes unwieldy and the LLM needs a structured way to query it.

**Depends on**: 8c (linking), 8d (confidence from topology)
**Enables**: System prompt can eventually trim low-confidence/old nodes, knowing the LLM can query them on demand (mirrors effort eviction pattern from Slice 4).

## Goal

Add a `query_knowledge` tool that lets the LLM search and filter the knowledge graph. Pure read — no mutations.

## Tool Definition

```
query_knowledge(query?, node_type?, min_confidence?)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | No | Keyword search against node summaries |
| `node_type` | string (enum) | No | Filter by type: `fact`, `preference`, `decision` |
| `min_confidence` | string (enum) | No | Minimum confidence level: `low`, `medium`, `high` |

At least one parameter must be provided. Returns JSON array of matching nodes with their confidence and edges.

## Behavior

### Search mechanism

Reuse `extract_keywords` from `decay.py` (already used by linker's `find_candidates`). Match nodes where at least 2 query keywords overlap with the node summary keywords, OR the node ID matches the query string. Case-insensitive.

When no `query` is provided (type/confidence filter only), return all nodes matching the filters.

### Response format

```json
{
  "matches": [
    {
      "id": "fact-001",
      "type": "fact",
      "summary": "Python 3.12 supports PEP 695 type aliases",
      "source": "python-upgrade",
      "confidence": {"level": "medium", "inbound_supports": 1, "inbound_contradicts": 0, "independent_sources": 1},
      "edges": [
        {"target": "fact-003", "type": "supports"},
        {"source": "decision-001", "type": "supports"}
      ]
    }
  ],
  "total_nodes": 12
}
```

Edges include both inbound and outbound for each matched node. `total_nodes` is the total count of active nodes in the graph (for context).

### Edge cases

- No matches → `{"matches": [], "total_nodes": N}`
- No parameters → `{"error": "At least one filter required: query, node_type, or min_confidence"}`
- Empty graph → `{"matches": [], "total_nodes": 0}`

## Implementation

### New function in `knowledge.py`

```python
def query_knowledge(session_dir: Path, query: str = None, node_type: str = None, min_confidence: str = None) -> str:
```

No LLM call. Pure keyword matching + filtering + confidence computation.

### Changes

| File | Change |
|------|--------|
| `src/oi/knowledge.py` | Add `query_knowledge()` function |
| `src/oi/tools.py` | Add tool definition to `TOOL_DEFINITIONS`. Add `query_knowledge` to import. Add case in `execute_tool`. |
| `tests/test_tools.py` | Import `query_knowledge`. Tests for the new function. |

### Confidence level ordering

For `min_confidence` filtering: `low` < `medium` < `high`. `contested` is excluded from the ordering — contested nodes are always returned regardless of `min_confidence` (they're important to surface).

## Acceptance Criteria

1. `query_knowledge(query="python")` returns nodes with matching keywords
2. `query_knowledge(node_type="preference")` returns only preference nodes
3. `query_knowledge(min_confidence="medium")` returns medium + high + contested nodes
4. `query_knowledge(query="python", node_type="fact")` filters compose (AND)
5. `query_knowledge()` with no args returns an error
6. Result includes edges (both inbound and outbound) for each matched node
7. Result includes confidence computed from current graph state
8. `execute_tool(session_dir, "query_knowledge", {...})` dispatches correctly
9. Empty graph returns `{"matches": [], "total_nodes": 0}`

## Not in scope

- Full-text search or semantic/embedding search (future)
- Pagination (graph size is small enough for now)
- Mutation operations (that's `add_knowledge`)
- Node eviction from system prompt (future slice — but this tool is the prerequisite)
