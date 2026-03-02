# Journey Log

> Where we are in implementing the thesis. For humans and agents to regain context.

## Source of Truth

- **Thesis**: [thesis.md](thesis.md) - The 5 core theses and vision
- **Slices**: [slices/README.md](slices/README.md) - Implementation roadmap
- **Technical**: [PROJECT.md](PROJECT.md) - Current architecture and code structure

Read those first. This doc tracks **implementation progress and pivots**.

---

## Current Status: Slice 11b Complete, Dogfooding MCP Server

Slices 1-7 built the memory system. Slices 8a-8h built the knowledge graph. Slices 9-10 unified the store and schema. Slice 11 exposed the graph via MCP for Claude Code integration. Slice 11b added provenance linking so no node is an orphan.

Now dogfooding: using the MCP server in real Claude Code sessions to build the graph organically. 27 active nodes, topology producing real confidence signals (decision-001 reached high confidence through convergent support).

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
| 8f | Done | `expand_knowledge`/`collapse_knowledge` tools, session fragment extraction, knowledge decay, `close_effort` forwards `session_id` |
| 8g | Done | `principle` node type, `exemplifies` edges, pattern detection pipeline, convergence from ≥3 facts / ≥2 sources |
| 8h | Done | `because_of` edges, staleness detection, confidence cap for stale deps |
| 9 | Done | Efforts migrated into `knowledge.yaml` as `type: "effort"` nodes. One store. `manifest.yaml` eliminated. |
| 10 | Done | `node_types.yaml` as single source of truth. Behavioral flags. All consumers wired to schema helpers. |
| 11 | Done | MCP server (FastMCP, stdio transport). 9 tools: add/query/remove_edge, effort CRUD. Human-readable output. |
| 11b | Done | Provenance linking: `reasoning` field, `chatlog://` URIs auto-stamped, MCP tool call log, Claude Code schema descriptor. |

**Test counts**: 377 free tests + 52 LLM tests (marker-separated). 1 skipped. 9 MCP tools.

### Session: MCP Server + Provenance (2026-03-01 to 2026-03-02)

Built and dogfooded the MCP server across two sessions. Key events:

1. **Slice 11 implementation**: 8 MCP tools wrapping existing functions. Fixed a linker inconsistency (temperature=0 for deterministic classification). Caught ourselves dismissing a test failure as "flaky" — root cause was a real bug. Added formatting helpers after raw JSON output was unacceptable.

2. **Brainstorming session**: Designed graph-aware search (three-layer pipeline: seed match → graph walk → LLM classify), two-pass bulk ingestion, conflict resolution ("recency is not authority, topology is"). Documented in [Decision 015](decisions/015-graph-aware-search-and-ingestion.md). Reorganized roadmap.

3. **Slice 11b implementation**: Three provenance layers so nodes link back to source conversations. Auto-discovers Claude Code's conversation logs and stamps `chatlog://` URIs. Investigated Claude Code's native log format — append-only JSONL, compaction doesn't split files.

4. **Dogfooding discoveries**:
   - Linker produces false positive contradictions across abstraction levels (GitHub #4). Led to adding `remove_edge` MCP tool.
   - Test suite was accidentally running paid LLM tests. Added `pytest.mark.llm` markers so default `pytest` is always free.
   - decision-001 reached **high confidence** through convergent support from independent later decisions — first real topology signal.

### Architecture: Unified KG + Vault Convergence

See [Decision 013](decisions/013-unified-kg-architecture.md). Key points:

- **Mutability gradient**: Layer 0 (raw) → Layer 3 (universal). Maps to abstraction levels on principle nodes.
- **Vault as storage layer**: Automerge (CRDT) solves concurrent mutation. Deferred until after ingestion proves the graph at scale.
- **Reactive edges**: `because_of` chains with lazy query-time staleness checks. Implemented in Slice 8h.

### What's Next

See [roadmap](slices/README.md) for full details. Priority order:
1. **Search Infrastructure (12a-d)**: Graph walk, embeddings, batch LLM classification, hybrid retrieval. Needed before ingestion can scale.
2. **Bulk Document Ingestion (13a-e)**: Two-pass architecture, conflict resolution with user sign-off. Target: Open Systems document corpus.
3. **Vault/Automerge**: After ingestion proves the graph at scale.

---

## Key Architectural Decisions

### System Prompt Optimization (Slice 8b)

Removed redundant tool descriptions from system prompt — they're already in `TOOL_DEFINITIONS` (passed via API `tools` parameter). System prompt now only contains behavioral rules (when to call tools, when NOT to). Saves ~130 tokens/turn.

### MCP Server for Claude Code Integration (Slice 11)

MCP became valuable once the KG needed to be used from Claude Code. FastMCP with stdio transport — Claude Code spawns the server as a subprocess. NixOS wrapper script (`bin/oi-mcp`) sets LD_LIBRARY_PATH. Human-readable formatted output, not raw JSON.

### Provenance: Never Create Orphan Nodes (Slice 11b)

Every node created via MCP gets three provenance layers: `reasoning` field (portable why), `chatlog://` URI (auto-discovered from Claude Code's native logs), MCP tool call log (audit trail). Schema descriptors define per-client log formats — Claude Code first, others when needed. See [Decision 015](decisions/015-graph-aware-search-and-ingestion.md).

### Linker Pipeline: Standalone Function

The node-linking pipeline (`find_candidates` → `link_nodes`) must be a standalone function, not embedded in tool handlers. Both chat mode and future data-ingest mode call the same pipeline — only the entry point differs.

### Tool Chaining Analysis

Analyzed all tool call patterns for optimization opportunities. Only one always-sequential pattern exists: `close_effort` → `summarize` → `extract_knowledge` → `add_knowledge` (already server-side). All other sequences are LLM-controlled and conditional on user intent.

### Unified KG + Vault Storage ([Decision 013](decisions/013-unified-kg-architecture.md))

The knowledge graph and Vault project converge: Automerge (CRDT) as the storage layer, KG as the semantic layer. Mutability gradient maps abstraction layers to mutation rules. Reactive `because_of` edges enable lazy staleness detection. Current Python/YAML prototype validates semantics; storage swaps to Automerge when Vault is ready.

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
4. **Current work**: Dogfooding MCP server, building KG organically. Next: Search Infrastructure (12a-d). See [Decision 015](decisions/015-graph-aware-search-and-ingestion.md) for design.
