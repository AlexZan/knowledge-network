# Journey Log

> Where we are in implementing the thesis. For humans and agents to regain context.

## Source of Truth

- **Thesis**: [thesis.md](thesis.md) - The 5 core theses and vision
- **Slices**: [slices/README.md](slices/README.md) - Implementation roadmap
- **Technical**: [PROJECT.md](PROJECT.md) - Current architecture and code structure

Read those first. This doc tracks **implementation progress and pivots**.

---

## Current Status: Slice 8g Complete, Architecture Validated

Slices 1-7 built the memory system. Slices 8a-8f built the knowledge graph (store, extraction, linking, confidence, querying, traceability). Slice 8g added automatic pattern detection — the system now generalizes across efforts. Dogfooding exposed and fixed two UX bugs in proactive knowledge capture and response verbosity.

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
| 8g | Done | `principle` node type, `exemplifies` edges, pattern detection pipeline (`detect_patterns`), convergence from ≥3 facts / ≥2 sources |

**Test counts**: 314 unit/integration + 33 e2e tests passing. 16 tools total.

### Dogfooding Fixes (Post-8g)

Two rounds of manual testing exposed UX bugs invisible to the test suite:

1. **Proactive knowledge capture**: LLM stopped calling `add_knowledge` after first message. Root cause: system prompt had no procedural guidance + actively suppressed tool calls mid-effort. Fix: step-by-step procedure in system prompt ("read → extract → call BEFORE responding"), exempted `add_knowledge` from tool suppression.

2. **Response verbosity**: Walls of speculative bullet points, 5+ follow-up questions. Fix: added Response Style section to system prompt with explicit rules, bad/good examples, max 1 question.

Both fixes validated with e2e tests based on real chat logs.

### Architecture: Unified KG + Vault Convergence

Traced the proposed unified architecture through 7 scenarios to validate the design. See [Decision 013](decisions/013-unified-kg-architecture.md) for full details. Key findings:

- **Mutability gradient**: Layer 0 (raw, highly mutable) → Layer 3 (universal, nearly immutable). Maps to abstraction levels already on principle nodes.
- **Vault as storage layer**: Automerge (CRDT) solves concurrent mutation. The KG is an Automerge document — structural conflicts resolved by CRDT math, semantic conflicts by our code.
- **Reactive edges**: `because_of` chains need lazy query-time staleness checks when dependencies are superseded. Identified gap, not yet implemented.
- **Implementation strategy**: Keep prototyping semantics on Python/YAML. Swap storage to Automerge when Vault is ready. Test suite provides safety net for the rewrite.

### What's Next

Open questions from the architecture validation:
- `because_of` staleness check implementation (small addition to `query_knowledge`)
- Schema system as single source of truth (JSON Schema for Python/TypeScript/Rust)
- Effort manifest → graph store migration (deferred from 8f, still deferred)
- Privacy gradient interaction with Vault's E2E encryption

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
4. **Current work**: Architecture validated through 8g. Next: `because_of` staleness, schema system, or Vault convergence — see [Decision 013](decisions/013-unified-kg-architecture.md)
