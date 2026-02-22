# Decision 011: Efforts Are KG Nodes — Everything Under One Graph

**Date**: 2026-02-22
**Status**: Accepted

---

## Context

Slices 1-7 built an effort system: open/close/expand/reopen/search/decay. Slice 8 was planned as "add a knowledge graph alongside efforts" — conclusion nodes extracted when efforts close.

But this creates two parallel systems:
- Efforts with their own manifest, lifecycle, and tools
- KG nodes with their own store, types, and tools

The user said something that reframes everything: efforts should be a node type *in* the knowledge graph, not a separate system. And the KG should capture things beyond efforts — preferences, facts, decisions — from any conversation, not just effort conclusions.

## Decision

**The knowledge graph is the single persistent layer. Everything is a node.**

An effort is a node type with a rich lifecycle. A fact is a simpler node type. A preference is simpler still. Each node type is defined by a schema that the LLM uses to know when and how to create/manage that type.

### Common node base

Every KG node shares the same base — this is CCM applied universally:

```
Common base (every node):
  - id
  - type (effort, fact, preference, ...)
  - summary (compacted knowledge — what lives in working context)
  - raw_file (link to the conversation that produced this node)
  - status (type-dependent: open/concluded, created/superseded, etc.)
  - created, updated
  - edges (connections to other nodes)
```

The raw log is always preserved. For an effort, it's a full multi-turn thread. For a fact extracted from ambient, it might be 3 messages. But the **structure is identical**: summary in context, raw behind a link.

This means expand/collapse works for *any* node type:
- "Show me the full conversation where we decided to use Postgres" → expands the decision node's raw log
- "What was the context for that JWT fact?" → expands the fact node's raw log
- Same mechanism as effort expansion (Slice 2), generalized

### Node type definitions

Each node type adds type-specific fields and behavior on top of the common base:

| Component | What it does | Example (effort) |
|-----------|-------------|-------------------|
| **Schema** | Type-specific fields on top of common base | `{active: bool}` (effort needs active flag) |
| **Lifecycle** | What status transitions are valid | `open → concluded → reopened → concluded` |
| **Tools** | LLM-callable functions to manage the type | `open_effort`, `close_effort`, `switch_effort`, etc. |
| **Instructions** | When/how the LLM should create/manage this type | "Call when user starts focused work that can be concluded..." |
| **Context behavior** | How the node appears in working context | Efforts: full raw when open, summary when concluded. Others: summary only, expandable. |

### Built-in node types

| Type | Extra fields | Lifecycle | Extracted From | Example |
|------|-------------|-----------|---------------|---------|
| effort | active, raw log append | open → concluded (expand, collapse, reopen, switch, decay) | User intent detected by LLM | "Debug the auth bug" |
| fact | confidence, source | created → superseded | Effort or ambient conversation | "API uses JWT with RS256" |
| preference | overrides | created → updated → superseded | Ambient conversation | "User prefers tabs over spaces" |
| decision | rationale, alternatives | created → superseded | Effort conclusion | "Use Postgres over MySQL for this project" |
| solution | problem, fix | created → superseded | Effort conclusion | "Add axios interceptor for token refresh" |
| principle | abstracted_from[] | created (from 8c abstraction) | Multiple related nodes | "Validate inputs at trust boundaries" |

### User-extensible types

Users can define new node types via schema files:

```
~/.oi/schemas/
  effort.yaml      # built-in, shipped with oi
  fact.yaml         # built-in
  preference.yaml   # built-in
  bookmark.yaml     # user-defined
  contact.yaml      # user-defined
```

Each schema defines fields, lifecycle, and extraction instructions. The LLM reads these to know what to capture.

### Schema-detection agent

When the LLM notices knowledge that doesn't fit existing schemas — e.g., user keeps mentioning people with roles and contact info — it can propose a new node type:

```
"I notice you've mentioned several people with their roles and emails.
Would you like me to create a 'contact' schema to track these?"
```

This is the meta-learning layer: the system learns what's worth remembering by noticing patterns in what it can't currently capture. This is a later sub-slice, not part of 8a.

## What this changes

### Conceptual shift

Before: Efforts are the core primitive. KG is an add-on.
After: KG is the core primitive. Efforts are one node type in it.

### Storage

```
~/.oi/
  graph/
    nodes/          # All nodes (efforts, facts, preferences, etc.)
    edges/          # Connections between nodes
    schemas/        # Node type definitions
  raw.jsonl         # Ambient conversation buffer (ephemeral)
```

The manifest.yaml (effort-only) is replaced by the graph store (all node types).

### Existing effort tools

The existing effort tools (`open_effort`, `close_effort`, etc.) remain — they're the tool interface for the effort node type. They just operate on the graph store instead of the manifest.

New node types get their own tools (simpler ones — most types don't need open/close/expand/decay):
- `add_knowledge(type, content, ...)` — generic tool for simple types
- Or type-specific tools if the lifecycle warrants it

### Context building

Currently: system prompt + ambient + concluded summaries + expanded raw + open effort raw.

New: system prompt + ambient + relevant KG node summaries (by type, recency, salience) + expanded node raw logs.

The bounded context system (Slice 4: eviction, decay, windowing) applies to all node types, not just efforts. Any node can be expanded to load its source conversation into context, and any expanded node decays when not referenced.

## Migration path

Slice 8a doesn't need to rewrite the effort system. The path:

1. **8a**: Add simple node types (fact, preference, decision) alongside existing efforts. One graph store, efforts still use existing tools.
2. **8b**: Connections and queries across all node types.
3. **Later**: Refactor effort storage to use the graph store natively (the tools stay the same, the storage backend changes).

The effort tools are the *interface*. The storage can evolve behind them.

## Risks

- **Complexity**: More node types = more for the LLM to manage. Mitigation: start with 2-3 types, add only when the LLM demonstrates it can handle them.
- **Over-extraction**: LLM might create too many nodes from casual conversation. Mitigation: extraction instructions should be conservative — only capture what the user would want to recall.
- **Schema bloat**: Too many user-defined types. Mitigation: the schema-detection agent proposes, user approves. No automatic creation.

## Relationship to other decisions

- **Decision 010 (ONE CHAT)**: One global graph, no project silos. Prerequisite for cross-domain knowledge.
- **Thesis 2 (Dynamic Knowledge Network)**: This decision implements it — every conversation extends the graph.
- **Thesis 3 (Abstraction & Privacy)**: The principle node type is the mechanism for abstraction.
