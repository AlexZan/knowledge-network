# Journey Log

> Where we are in implementing the thesis. For humans and agents to regain context.

## Source of Truth

- **Thesis**: [thesis.md](thesis.md) - The 5 core theses and vision
- **Slices**: [slices/README.md](slices/README.md) - Implementation roadmap
- **Technical**: [PROJECT.md](PROJECT.md) - Current architecture and code structure

Read those first. This doc tracks **implementation progress and pivots**.

---

## Current Status: Slice 8e Complete, 8f Next

Slices 1-7 built the memory system. Slices 8a-8d added the knowledge graph (store, auto-extraction, linking, confidence). Slice 8e made the graph usable at runtime: searchable, evictable, with contradiction resolution and session audit logs. Next: unified graph storage (8f).

### What's Built

| Slice | Status | Key Feature |
|-------|--------|-------------|
| 1-5 | Done | Effort lifecycle: open → work → close → summary. Expansion, decay, search, reopen. |
| 6 | Done | Cross-session persistence, session markers |
| 7 | Done | read_file, write_file, append_file, run_command with confirmation callbacks |
| 8a | Done | `add_knowledge` tool, `knowledge.yaml` (nodes + edges), knowledge shown in system prompt |
| 8b | Done | `extract_knowledge()` LLM call on effort close, 0-5 nodes auto-persisted |
| 8c+8d | Done | Auto-linking (keyword overlap + LLM classification), confidence from topology (low/medium/high/contested) |
| 8e | Done | `query_knowledge` tool, knowledge eviction (30-turn threshold), `supersedes` for contradiction resolution, session audit logs |

### What's Next: 8f (Traceable Knowledge)

Any knowledge node expandable to its source conversation. Session log linking (builds on 8e's `created_in_session`). `expand_knowledge` tool. Effort migration deferred — current dual storage works fine.

---

## Key Architectural Decisions

### System Prompt Optimization (Slice 8b)

Removed redundant tool descriptions from system prompt — they're already in `TOOL_DEFINITIONS` (passed via API `tools` parameter). System prompt now only contains behavioral rules (when to call tools, when NOT to). Saves ~130 tokens/turn.

### MCP Not Needed Pre-MVP

MCP would add transport/process overhead for no benefit at current scale. Tool descriptions already load via `tools` parameter, not system prompt. MCP becomes valuable when: third-party tools, multiple LLM hosts, or hot-swappable tool servers.

### Linker Pipeline: Standalone Function

The node-linking pipeline (`find_candidates` → `link_nodes`) must be a standalone function, not embedded in tool handlers. Both chat mode and future data-ingest mode call the same pipeline — only the entry point differs.

### Tool Chaining Analysis

Analyzed all tool call patterns for optimization opportunities. Only one always-sequential pattern exists: `close_effort` → `summarize` → `extract_knowledge` → `add_knowledge` (already server-side). All other sequences are LLM-controlled and conditional on user intent.

---

## Implementation Pivots

### Pivot: Artifact Model → Effort Model (Pre-Slice 1)

**Original**: Flexible `Artifact` type with dynamic `artifact_type` (effort, fact, event).
**Pivot**: Dedicated effort model with explicit lifecycle (open → concluded). Knowledge nodes separate.
**Why**: Efforts have clear lifecycle semantics. Mixing them with facts/events created ambiguity.

### Pivot: oi-pipe TDD → Direct Implementation (Slice 1+)

**Original**: Build slices using oi-pipe TDD pipeline.
**Pivot**: Direct implementation with manual tests, using oi-pipe lessons for test design.
**Why**: Pipeline overhead wasn't justified for the knowledge-network codebase size. Pipeline lessons (generate→validate→retry, small models need procedures) still apply.

### Pivot: Monolithic Slice 8b → Sub-slices (Post-8b)

**Original roadmap**: 8b was "Conflict + Confidence" (contradiction detection + truth/preference classification + topology scoring).
**Pivot**: Split into 8c (contradiction detection), 8d (confidence from topology).
**Why**: Each sub-slice is independently testable. Contradiction detection is useful without confidence; confidence needs edges to exist first.

---

## For Agents

1. **Read [thesis.md](thesis.md)** — understand the vision (5 theses)
2. **Read [slices/README.md](slices/README.md)** — see the roadmap
3. **Read [PROJECT.md](PROJECT.md)** — current technical state
4. **Current work**: Slice 8f — traceable knowledge (expand any node to source conversation)
