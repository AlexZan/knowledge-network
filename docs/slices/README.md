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
| 12a | Graph Walk Search | Graph walk layer between keyword seeds and result ranking. Expands candidates 1-2 hops with decay scoring (0.7x/0.4x). Convergence boosts. Plugs into `query_knowledge()` and `find_candidates()`. | [12a-graph-walk.md](12a-graph-walk.md) |
| 12b | Embedding Search | Semantic seed matching via configurable embeddings (OI_EMBED_MODEL). Cosine similarity finds vocabulary gaps (e.g. "SOA" ↔ "microservices"). Graceful fallback to keyword-only. | — |
| 12c | Batch LLM Classification | One prompt classifies all candidates instead of N per-pair calls. Fallback to per-pair on parse failure. Also: containment ratio for short queries, result cap (max_results=10). | — |
| 13a | Document Parser | Read mixed formats (markdown, PDF, plain text). Extract metadata. Chunk large docs into sections. | — |
| 13b | Claim Extraction | LLM extracts discrete knowledge nodes from each chunk (Pass 1). `skip_linking`/`skip_embed` flags for batch. | — |
| 13c | Graph-Aware Batch Linker | `link_new_nodes()` links all extracted nodes with full graph visibility (Pass 2). Symmetric pair dedup. Detect contradictions. | — |
| 13d | Conflict Resolution Report | Topology-based classification: auto_resolvable/strong_recommendation/ambiguous. `resolve_conflict`, `auto_resolve`. First run: 6/37 auto-resolved, zero LLM. | — |
| 13e | Ingestion CLI / MCP Tool | `ingest_pipeline()` orchestrator (parse→extract→write→link→embed→report). MCP `mcp_ingest_document` tool with dry-run and skip_linking. Anomaly ledger (`anomalies.yaml`). | — |

**Phase boundary**: Slices 1-7 are a memory system with agent capabilities. Slices 8a-8d add the knowledge graph with topology-based confidence. Slices 8e-8f make the graph usable and traceable at runtime. Slice 8g adds generalization. Slice 8h adds reactive staleness detection. Slice 9 unifies efforts and knowledge into one store. Slice 10 makes the schema extensible. Slice 11 exposes the graph to external tools via MCP. Slice 11b ensures every node links back to its source conversation via provenance URIs. Slices 12a-c add graph-aware search (graph walk, embeddings, batch classification). Slices 13a-e add bulk document ingestion with two-pass architecture, topology-based conflict resolution, and a unified MCP tool.

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
 ↓
12a: Graph Walk Search (expand candidates via edge traversal with decay scoring) ✓
 ↓
12b: Embedding Search (semantic seeds via configurable OI_EMBED_MODEL) ✓
 ↓
12c: Batch LLM Classification (1 prompt for N candidates, containment ratio, result cap) ✓
 ↓
13a: Document Parser (markdown/PDF/plain text, section chunking) ✓
 ↓
13b: Claim Extraction (LLM extracts nodes from chunks, batch flags) ✓
 ↓
13c: Graph-Aware Batch Linker (link_new_nodes, symmetric dedup) ✓
 ↓
13d: Conflict Resolution (topology classification, auto_resolve) ✓
 ↓
13e: Ingestion CLI / MCP Tool (ingest_pipeline, MCP tool, anomaly ledger) ✓
```

---

## Future

Ordered top-down by dependency. Each item builds on the one above it.

### Phase Transition: Python → Rust

Phase 1 (Python prototype) is complete. Phase 2 is a Rust port with CRDT storage and WASM targets. See [Decision 016](../decisions/016-rust-wasm-port.md) and [BIG-PICTURE.md](../BIG-PICTURE.md) for the full 6-phase plan.

The Python codebase remains as the reference implementation during the port. No further Python slices are planned — new development happens in Rust.

---

## Refactor Queue

Technical debt items. Not urgent — trigger conditions listed. Review when the triggering slice lands.

| Item | Current State | Trigger | What to Do |
|------|--------------|---------|------------|
| Parser registry | `parser.py` has hardcoded `if/elif` dispatch + static `_FORMAT_MAP` for 3 formats | 4th format added, or 13e needs pluggable parsers | Extract a `FormatParser` protocol, parser registry dict keyed by extension, `register_parser()` API |

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
- **12d: LLM Reranking** — LLM classify top-15 results in `query_knowledge`. Current keyword + embedding + graph walk scoring may be sufficient — revisit if search quality degrades at scale
- **Dynamic KG switching** — Easily switch active KG by effort/context (e.g. "switch to physics theory" auto-loads that KG). Needs brainstorming. Current workaround: separate MCP server entries in `.mcp.json` with different `OI_SESSION_DIR`. Long-term: effort-aware KG routing, a KG registry, or a "load KG" command.
- **Ingestion resume/checkpoint** — If ingest crashes mid-run (e.g. GPU panic, network drop), restart from where it left off. Track which files/conversations are already processed (by node provenance URI) and skip them on re-run. Critical for large expensive ingestion jobs.
- **LLM external knowledge pass** — After document ingestion, run an additional pass where the LLM uses its own training knowledge to add supporting or contradicting nodes for ingested claims — things not mentioned in the document itself. Could run different models on the same pass (e.g. a physics-specialized model for physics claims). Produces `supports`/`contradicts` edges from "model-knowledge" source nodes. Enables the KG to reflect the broader scientific context of a theory, not just what the author chose to mention.
- **Internet/citation pass** — After ingestion, search for published papers, experimental results, or authoritative sources that relate to ingested claims. Link via `related_to` or `supports`/`contradicts` depending on logical relationship. Third-party validation for theory claims. Pairs with Decision 019 (semantic vs logical edges) — citations that don't assert logical implication get `related_to`.

---

## Related Documents

- [CCM Whitepaper](../ccm-whitepaper.md) — Published (Slices 1-4)
- [Thesis](../thesis.md) — Knowledge Network vision (Theses 2-5, hybrid endgame)
- [Technical Reference](../PROJECT.md) — Architecture (needs update)
- [Scenarios](08-knowledge-graph-scenarios.md) — Slice 8 UX walkthroughs
