# Implementation Roadmap

Building a general-purpose AI system with persistent memory, tool use, and knowledge accumulation.

CCM whitepaper published (Slices 1-4). Now building toward the Knowledge Network vision ([thesis.md](../thesis.md)).

---

## Completed

| Slice | Name | What it does | Spec |
|-------|------|-------------|------|
| 1 | Core Compaction | Open efforts = raw context, concluded = summary. ~97% token savings. | [01-core-compaction-proof.md](01-core-compaction-proof.md) |
| 2 | Expansion & Multi-Effort | Concluded efforts recallable on demand. Multiple simultaneous efforts. | [02-expansion-multi-effort.md](02-expansion-multi-effort.md) |
| 3 | Salience Decay | Expanded efforts auto-collapse when no longer referenced. | [03-salience-decay.md](03-salience-decay.md) |
| 4 | Bounded Working Context | Summary eviction, ambient windowing, `search_efforts`. O(1) working memory. | [04-bounded-working-context.md](04-bounded-working-context.md) |
| 5 | Effort Reopening | Concluded efforts can be reopened and extended. Re-conclusion updates summary. | [05-effort-reopening.md](05-effort-reopening.md) |
| 6 | Cross-Session Persistence | Per-project sessions, session markers, efforts survive restarts. | — |
| 7 | Tool Use | `read_file`, `write_file`, `append_file`, `run_command`. Confirmation callback system. | — |
| 8a | Knowledge Store | `add_knowledge` tool. `fact`, `preference`, `decision` node types. `knowledge.yaml` with nodes + edges. Knowledge graph shown in system prompt. | — |
| 8b | Auto-Extract on Close | `extract_knowledge()` LLM call on effort close. 0-5 nodes auto-persisted. Extraction banner in close output. | — |
| 8c | Node Linking | Auto-linking via keyword overlap + LLM classification. `supports`/`contradicts` edges. | [08c-node-linking.md](08c-node-linking.md) |
| 8d | Confidence from Topology | Confidence levels (low/medium/high/contested) computed from edge counts + independent sources. Annotations in system prompt. | — |
| 8e | The Agent Remembers | `query_knowledge` tool, knowledge eviction (30-turn threshold), `supersedes` for contradiction resolution, session audit logs. | — |
| 8f | Traceable Knowledge | `expand_knowledge`/`collapse_knowledge` tools. Any node expandable to source conversation. Session fragment extraction. Knowledge decay. `close_effort` forwards `session_id`. | — |
| 8g | The Agent Generalizes | `principle` node type, `exemplifies` edges, pattern detection pipeline, convergence from ≥3 facts / ≥2 sources. | [08g-the-agent-generalizes.md](08g-the-agent-generalizes.md) |
| 8h | Reactive Knowledge | `because_of` edges, staleness detection, confidence cap for stale deps. | [08h-because-of-staleness.md](08h-because-of-staleness.md) |
| 9 | Unified Graph Store | Efforts migrated into `knowledge.yaml` as `type: "effort"` nodes. One store for all node types. `manifest.yaml` eliminated. | [09-unified-graph-store.md](09-unified-graph-store.md) |
| 10 | Schema System | `node_types.yaml` as single source of truth for node/edge types. Behavioral flags (`extractable`, `tool_addable`, `show_in_display`, `linkable`). All consumers wired to schema helpers. Backward compat preserved. | — |
| 11 | MCP Server Interface | Expose KG tools as MCP server for Claude Code. 8 tools (add/query knowledge, effort CRUD). Human-readable output formatting. Stdio transport. | — |
| 11b | Provenance Linking | `reasoning` field, `chatlog://` URIs auto-stamped from Claude Code logs, MCP tool call log. Schema descriptor for Claude Code log format. | [11b-provenance-linking.md](11b-provenance-linking.md) |

**Phase boundary**: Slices 1-7 are a memory system with agent capabilities. Slices 8a-8d add the knowledge graph with topology-based confidence. Slices 8e-8f make the graph usable and traceable at runtime. Slice 8g adds generalization. Slice 8h adds reactive staleness detection. Slice 9 unifies efforts and knowledge into one store. Slice 10 makes the schema extensible. Slice 11 exposes the graph to external tools via MCP. Slice 11b ensures every node links back to its source conversation via provenance URIs.

---

## Architectural Decisions

- [Decision 010: ONE CHAT](../decisions/010-one-chat-no-projects.md) — No projects, no sessions to manage. One global knowledge space.
- [Decision 011: Efforts Are KG Nodes](../decisions/011-efforts-are-kg-nodes.md) — Everything is a node. Efforts are one node type with a rich lifecycle.
- [Decision 012: Sessions as Audit Logs](../decisions/012-session-as-audit-log.md) — Sessions are chronological records of graph interactions + ambient conversation, not persistence boundaries.
- [Decision 013: Unified KG Architecture](../decisions/013-unified-kg-architecture.md) — Mutability gradient, Automerge/Vault storage layer, reactive `because_of` edges. Validated via 7 architectural traces.
- [Decision 014: Sessions as Perspectives](../decisions/014-sessions-as-perspectives.md) — Sessions develop distinct viewpoints. Enables multi-agent debate, roundtables, adversarial review.

---

## Dependency Chain (Complete)

```
8e: The Agent Remembers (query, eviction, resolution, session logs) ✓
 ↓
8f: Traceable Knowledge (session log linking, expand_knowledge) ✓
 ↓
8g: The Agent Generalizes (principles, abstraction, privacy) ✓
 ↓
8h: Reactive Knowledge (because_of edges, staleness detection) ✓
 ↓
9: Unified Graph Store (efforts into knowledge.yaml) ✓
 ↓
10: Schema System (node_types.yaml, behavioral flags) ✓
 ↓
11: MCP Server Interface (Claude Code integration) ✓
 ↓
11b: Provenance Linking (reasoning field, chatlog:// URIs, tool call log) ✓
```

---

## Future

Ordered top-down by dependency. Each item builds on the one above it.

### Search Infrastructure

Graph-aware retrieval replacing flat keyword scan. See [Decision 015](../decisions/015-graph-aware-search-and-ingestion.md).

| Slice | What |
|-------|------|
| 12a | **Graph Walk** — Expand candidates by following edges 1-2 hops from seed matches. Decay scoring (0.7x/0.4x). Convergence signal from multiple paths. |
| 12b | **Embeddings** — Vector layer for semantic seed matching. Catches terminology drift (e.g. "SOA" ↔ "microservices"). Embedding model + storage TBD. |
| 12c | **Batch LLM Classification** — One prompt for N candidates instead of N calls. Major cost reduction at scale. |
| 12d | **Hybrid Retrieval** — Wire 12a-c into three-layer pipeline: seed match → graph walk → LLM classify top-15. |

### Bulk Document Ingestion

Two-pass architecture: extract then link. See [Decision 015](../decisions/015-graph-aware-search-and-ingestion.md). Depends on Search Infrastructure.

| Slice | What |
|-------|------|
| 13a | **Document Parser** — Read mixed formats (markdown, PDF, plain text). Extract metadata (date, title, source path). Chunk large docs into sections. |
| 13b | **Claim Extraction** — LLM extracts discrete knowledge nodes from each chunk (Pass 1). Temporal metadata preserved. Order-independent, parallelizable. |
| 13c | **Graph-Aware Batch Linker** — Link all extracted nodes with full graph visibility (Pass 2). Detect contradictions across eras. |
| 13d | **Conflict Resolution Report** — Interactive report: subjective conflicts need user sign-off (with provenance chain), factual conflicts auto-resolved. System prioritizes ambiguous vs obvious. |
| 13e | **Ingestion CLI / MCP Tool** — `oi ingest <path>` or MCP tool. Progress reporting, cost estimates, dry-run mode, resume-on-failure. |

**Rollout plan**: Small test batch (5-10 docs) → medium batch (50-100) → full Open Systems corpus (hundreds of docs, decades of history). Confidence in the pipeline must be high before scaling.

### Storage & Scale

| Slice | What |
|-------|------|
| Vault/Automerge | CRDT storage layer. Replace YAML with Automerge. Concurrent sessions, P2P sync, full history. See [Decision 013](../decisions/013-unified-kg-architecture.md). Needed when concurrency/multi-agent demands it — after ingestion proves the graph at scale. |

### Exploratory (needs brainstorming)

| Slice | What |
|-------|------|
| Tool Nodes | Tool definitions as a KG node type. Agent capabilities become part of the graph — edges to motivating decisions, supersedes when replaced, confidence from usage. |
| Workflow Integration | oi-pipe as a subsystem, workflow orchestration through tool calls. |

Multi-agent debate transport is developed independently (separate project using MCP). Sessions naturally develop perspectives ([Decision 014](../decisions/014-sessions-as-perspectives.md)) — no KG integration needed for that.

---

## Icebox

Capabilities that may be valuable but aren't blocking the core vision. Revisit as needed.

- **Web search tool** — Dedicated web search beyond `run_command` + `curl`
- **Codebase search tool** — Structured grep/find with semantic output
- **Tool error recovery** — Retry logic, better error classification
- **Model ladder** — Escalation from cheap → expensive models per task
- **Dashboard** — Visual entry point to the knowledge graph (developed separately)
- **Schema-detection agent** — Auto-propose new node types from conversation patterns
- **`because_of` multi-hop** — Deep chain staleness. Only if dogfooding shows 1-hop is insufficient

---

## Related Documents

- [CCM Whitepaper](../ccm-whitepaper.md) — Published (Slices 1-4)
- [Thesis](../thesis.md) — Knowledge Network vision (Theses 2-5, hybrid endgame)
- [Technical Reference](../PROJECT.md) — Architecture (needs update)
- [Scenarios](08-knowledge-graph-scenarios.md) — Slice 8 UX walkthroughs
