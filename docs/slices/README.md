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
| 14a | Edge Weights + Salience | Edge weight by reasoning quality (1.0x/0.5x in PageRank). Salience metric from `related_to` density. `sort_by` param in `query_knowledge` + MCP. | [Decision 020](../decisions/020-salience-confidence-separation.md) |
| 14b | Concept Nodes | Embedding cluster detection (`find_clusters`), LLM concept synthesis (`synthesize_concepts`), `principle` nodes with `exemplifies` edges. Optional pipeline stages. Robust JSON parsing (`_parse_llm_json`). | [Decision 020](../decisions/020-salience-confidence-separation.md) |

**Phase boundary**: Slices 1-7 are a memory system with agent capabilities. Slices 8a-8d add the knowledge graph with topology-based confidence. Slices 8e-8f make the graph usable and traceable at runtime. Slice 8g adds generalization. Slice 8h adds reactive staleness detection. Slice 9 unifies efforts and knowledge into one store. Slice 10 makes the schema extensible. Slice 11 exposes the graph to external tools via MCP. Slice 11b ensures every node links back to its source conversation via provenance URIs. Slices 12a-c add graph-aware search (graph walk, embeddings, batch classification). Slices 13a-e add bulk document ingestion with two-pass architecture, topology-based conflict resolution, and a unified MCP tool. Slices 14a-b add enrichment: reasoning-weighted confidence, salience as a distinct metric, and concept node synthesis from embedding clusters.

---

## Architectural Decisions

- [Decision 010: ONE CHAT](../decisions/010-one-chat-no-projects.md) — No projects, no sessions to manage. One global knowledge space.
- [Decision 011: Efforts Are KG Nodes](../decisions/011-efforts-are-kg-nodes.md) — Everything is a node. Efforts are one node type with a rich lifecycle.
- [Decision 012: Sessions as Audit Logs](../decisions/012-session-as-audit-log.md) — Sessions are chronological records of graph interactions + ambient conversation, not persistence boundaries.
- [Decision 013: Unified KG Architecture](../decisions/013-unified-kg-architecture.md) — Mutability gradient, Automerge/Vault storage layer, reactive `because_of` edges. Validated via 7 architectural traces.
- [Decision 014: Sessions as Perspectives](../decisions/014-sessions-as-perspectives.md) — Sessions develop distinct viewpoints. Enables multi-agent debate, roundtables, adversarial review.
- [Decision 019: Semantic vs Logical Edges](../decisions/019-semantic-vs-logical-edges.md) — `related_to` excluded from PageRank. Semantic layer feeds salience, not confidence.
- [Decision 020: Salience, Edge Weights, Concept Nodes](../decisions/020-salience-confidence-separation.md) — Three distinct metrics (salience, corroboration, logical confidence). Reasoning-weighted edges. Concept nodes from embedding clusters.

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
 ↓
14a: Edge Weights + Salience (reasoning-weighted PageRank, salience metric, sort_by) ✓
 ↓
14b: Concept Nodes (embedding clusters, LLM synthesis, robust JSON parsing) ✓
```

---

## Future

Ordered top-down by dependency. Each item builds on the one above it.

### Phase Transition: Python → Rust

Phase 1 (Python prototype) is complete. Phase 2 is a Rust port with CRDT storage and WASM targets. See [Decision 016](../decisions/016-rust-wasm-port.md) and [BIG-PICTURE.md](../BIG-PICTURE.md) for the full 6-phase plan.

The Python codebase remains as the reference implementation. Rust port is deferred — Python performance is acceptable while the LLM API is the bottleneck. New Python slices continue as needed.

---

## Refactor Queue

Technical debt items. Not urgent — trigger conditions listed. Review when the triggering slice lands.

| Item | Current State | Trigger | What to Do |
|------|--------------|---------|------------|
| Parser registry | `parser.py` has hardcoded `if/elif` dispatch + static `_FORMAT_MAP` for 3 formats | 4th format added, or 13e needs pluggable parsers | Extract a `FormatParser` protocol, parser registry dict keyed by extension, `register_parser()` API |

---

## Planned

Improvements identified during conflict review (2026-03-08). Ordered by dependency.

1. ~~**Extraction source quotes**~~ ✅ — Extraction LLM returns `source_quote` per claim (verbatim text from source, 1-3 sentences). Stored on nodes via `add_knowledge()`, surfaced in `query_knowledge()`. Block-level anchors (`#turn-3:L12-L18`) deferred — the quote itself is sufficient for context-aware linking (#2) and can be located in source text programmatically when precise anchors are needed. 5 tests.
2. ~~**Context-aware linking (Tier 2)**~~ ✅ — Linker now receives `source_quote` alongside summaries in both single-pair and batch classification prompts. Prompt instructs: "Summaries can be misleading — the quote shows what was actually said." Addresses 7/37 false positives from scope/framework mismatches. 7 tests (5 linker prompt tests, 2 end-to-end flow tests). Tier 3 (agentic KG navigation for persistent ambiguity) remains future work — move to icebox if needed.
3. ~~**Canvas-aware extraction routing**~~ ✅ — Canvas chunks (`#canvas-N`) routed to per-chunk `extract_from_chunk()`, conversation turns to `extract_from_conversation()`. Canvas errors don't block conversation extraction. 6 tests.
4. ~~**Extraction-phase deduplication**~~ ✅ — Addressed with prompt instruction ("do not split composite principles into separate nodes") in both extraction prompts. A post-extraction dedup pass was considered but rejected: the problem (S17) occurred once in 190 contradictions — an upstream prompt fix is proportionate, a dedup pass would add O(n²) overhead to every extraction for a rare edge case.
5. ~~**Terminology conflict resolution flow**~~ ✅ — `correct_terminology()` in knowledge.py + `mcp_correct_terminology` MCP tool. Flow: create corrected node (supersedes original, inherits source_quote + provenance) → remove old contradicts edge → LLM re-classifies relationship between corrected node and conflicting node → create new edge → save review provenance. 8 tests. First case ready: fact-501 vs fact-176.
6. ~~**Process/sequence edge types**~~ → moved to Icebox (see below)
7. ~~**Attribution-aware extraction with epistemic status**~~ ✅ (prompt-level) — Addressed with extraction prompt instructions: user is primary author/source of authority, don't extract assistant's elevated restatements over user's actual framing, tentative language ("maybe", "I wonder", "spitballing") means not a settled position. New `attribution`/`epistemic_status` fields deferred — the prompt fix targets the root cause (assistant-elevation pattern from S16) without schema changes. If the problem persists at scale, revisit with structured fields.
8. **TOTP review attestation** — See [Decision 024](../decisions/024-totp-review-attestation.md). Human reviewer types a TOTP code to cryptographically attest approval. Prevents AI from forging `reviewed_by` metadata. Build when provenance needs to be stronger (multi-user or published research).
9. **Topology-based support weight** — Replace binary edge weight (1.0/0.5) in `compute_all_confidences()` with a computed weight from embedding dissimilarity + source independence. Paraphrases (high cosine, same source) contribute near-zero support; independent evidence (low cosine, different source) contributes full weight. Fixes duplicate node inflation (see `docs/research/auto-resolution-review-findings.md`). No new edge types, no linker changes — one function in `confidence.py`. Requires embeddings on all nodes. See `docs/research/support-weight-from-topology.md` for full design.

---

## Icebox

Capabilities that may be valuable but aren't blocking the core vision. Revisit as needed.

- **Web search tool** — Dedicated web search beyond `run_command` + `curl`
- **Codebase search tool** — Structured grep/find with semantic output
- **Tool error recovery** — Retry logic, better error classification
- **Model ladder** — Escalation from cheap → expensive models per task
- **Dashboard** — Visual entry point to the knowledge graph (developed separately)
- **Process/sequence edge types** (`precedes`, `leads_to`) — Capture causal/temporal ordering within a theory's processes. Identified from 1 case (S12: fluctuation → collapse → memory spectrum). Requires schema change, linker prompt updates, and graph walk changes for directional traversal. Current `related_to` works — loses directionality but no downstream consumer needs it yet. Revisit when process-flow queries or visualization need ordering. Moved from Planned #6 (2026-03-09).
- **Schema-detection agent** — Auto-propose new node types from conversation patterns
- **`because_of` multi-hop** — Deep chain staleness. Only if dogfooding shows 1-hop is insufficient
- **12d: LLM Reranking** — LLM classify top-15 results in `query_knowledge`. Current keyword + embedding + graph walk scoring may be sufficient — revisit if search quality degrades at scale
- **Dynamic KG switching** — Easily switch active KG by effort/context (e.g. "switch to physics theory" auto-loads that KG). Needs brainstorming. Current workaround: separate MCP server entries in `.mcp.json` with different `OI_SESSION_DIR`. Long-term: effort-aware KG routing, a KG registry, or a "load KG" command.
- **Ingestion resume/checkpoint** — If ingest crashes mid-run (e.g. GPU panic, network drop), restart from where it left off. Track which files/conversations are already processed (by node provenance URI) and skip them on re-run. Critical for large expensive ingestion jobs.
- **LLM external knowledge pass** — After document ingestion, run an additional pass where the LLM uses its own training knowledge to add supporting or contradicting nodes for ingested claims — things not mentioned in the document itself. Could run different models on the same pass (e.g. a physics-specialized model for physics claims). Produces `supports`/`contradicts` edges from "model-knowledge" source nodes. Enables the KG to reflect the broader scientific context of a theory, not just what the author chose to mention.
- **Internet/citation pass** — After ingestion, search for published papers, experimental results, or authoritative sources that relate to ingested claims. Link via `related_to` or `supports`/`contradicts` depending on logical relationship. Third-party validation for theory claims. Pairs with Decision 019 (semantic vs logical edges) — citations that don't assert logical implication get `related_to`.
- **Effort progress tracking & child node association** — Two related gaps in effort management:
  1. **Automatic child node linking.** When an effort is active, nodes created via `add_knowledge` (or extracted during ingestion) should automatically get a `belongs_to` edge to the active effort. In OI chat, conversation context links nodes to efforts naturally. In MCP mode (Claude Code), there's no automatic association — nodes are created in a vacuum. The effort node exists but has no structural connection to the facts, conclusions, and preferences produced during it.
  2. **Progress log.** A lightweight `mcp_log_effort` tool that appends timestamped entries (milestones, findings, blockers, decisions) to the effort. Not full knowledge nodes — just a chronological log stored in the effort's `log` list or raw file. `effort_status` should surface recent log entries + child node count.
  3. **`effort_status` enrichment.** Show child node count (nodes with `belongs_to` edge to effort), recent progress entries, and edge summary (how many supports/contradicts/related_to were created during this effort).

  **Why it matters**: Without this, efforts are just open/close bookends with no internal structure. The work that happens *during* an effort — the nodes created, the contradictions found, the decisions made — isn't connected to the effort in the graph. This makes it impossible to ask "what did we learn during theory-ingestion?" and get a structured answer. The OI chat model handles this via conversation threading; MCP needs explicit plumbing.

  **Note**: This item may be superseded by "Hierarchical effort KGs" below, which solves child node association by giving each effort its own graph.

- **Typed contradiction classification** — Replace the single undifferentiated `contradicts` edge with typed subtypes: logical, semantic, scope, temporal, narrative. Decision 017 explored a five-type taxonomy but was shelved in favor of prompt-level prevention. Manual review data (Paper 2, Section 4.2) now provides empirical grounding: 55% of post-resolution conflicts were construction artifacts classifiable by type (scope mismatch, context loss, extraction splitting, terminology conflict, attribution gap). Each type needs a different resolution mechanism — only logical contradictions have winners in the topological sense; the rest need disambiguation, hierarchy, timeline analysis, or provenance tracking. Pairs with tiered linking (Tier 2 implemented, Tier 3 in icebox) as part of a broader construction-phase improvement story. Consider whether classification belongs in the resolution algorithm, the linker, or both.

- **Conflict review UI** — Agent-generated conflict report (with timestamps, delta, source context, analysis) displayed in a web app. User sets resolution type from UI, interfaced back via MCP. Replaces the current chat-based one-by-one review workflow. Needs: web app scaffold, MCP endpoints for listing conflicts and submitting resolutions, report generation agent.

- **Hierarchical effort KGs** — Each effort gets its own knowledge graph rather than being a node inside a flat global KG. The effort node in the parent KG holds the summary; expanding it opens the full sub-KG. Core design:
  1. **Effort = scoped KG.** When an effort opens, it gets its own `knowledge.yaml` (or equivalent). All `add_knowledge`, linking, and confidence computation during the effort operates on this scoped graph. No noise from unrelated work.
  2. **Closing = merge/promotion.** When the effort closes, high-confidence nodes and resolved conclusions get promoted into the parent KG as summary nodes. Low-confidence leaf nodes, working hypotheses, and noise stay in the sub-KG — accessible but not polluting the parent. This is CCM (Paper 1) applied to graph structure: conclusion-triggered compaction for knowledge graphs.
  3. **Expand/collapse traversal.** The agent sees the effort as a summary node in the parent KG by default. If it needs deeper detail, it expands into the effort's sub-KG — same pattern as Slice 8f (traceable knowledge) but applied to entire graphs instead of individual nodes. The agent chooses its traversal depth.
  4. **Recursive nesting.** Efforts can contain sub-efforts, each with their own KG. A research project is an effort containing per-document ingestion efforts, each containing per-chunk sub-graphs. Zoom in or out at any level. The hierarchy mirrors how humans naturally organize research.
  5. **Independence guarantee strengthened.** If two effort KGs are structurally isolated during work, convergence detected at merge time is genuine corroboration — the claims were produced independently. Stronger independence signal than same-KG linking where nodes can influence each other during extraction.
  6. **Confidence propagates hierarchically.** A `high` confidence node inside an effort's KG surfaces as a strong claim in the parent. A `contested` node may not surface at all unless expanded. The parent KG stays clean — executive summary level — while full reasoning chains live in sub-KGs.

  **Open design question: cross-effort linking.** Isolated effort KGs can't link nodes across siblings. If effort A discovers "collapse creates time" and effort B independently discovers the same claim, they can't connect because the linker only sees within one KG. Three candidate approaches:
  - **(a) Link at merge time only.** Cross-effort edges form only when nodes meet in the parent KG after both efforts close. Simplest. Preserves independence guarantee. But misses real-time cross-pollination — effort B can't benefit from effort A's established knowledge while still open.
  - **(b) Read-only parent visibility (preferred).** An effort's KG can *read* the parent KG and sibling summaries for linking candidates, but only *writes* to its own graph. Cross-effort edges get stored in the parent. The effort stays isolated for writes but aware for reads. Mirrors how humans work: your own notebook, but you can reference the shared library.
  - **(c) Lazy upward linking.** When a node is created in an effort's sub-KG, the linker checks parent KG nodes as additional candidates. Matches produce edges in the parent KG pointing to the sub-node via a reference. Sub-KG stays clean, parent accumulates cross-effort structure.

  Option (b) balances isolation with awareness. The independence guarantee weakens slightly (the effort *saw* parent context) but write isolation means the effort's own conclusions are still self-contained. The parent KG acts as shared context, not shared workspace.

  **Relationship to existing architecture**: Currently efforts are nodes *inside* the KG (Decision 011). This flips the hierarchy — the KG lives *inside* the effort. The effort node in the parent becomes a portal to a sub-graph, not just metadata. This is a significant architectural shift but aligns with the multi-layer vision in Decision 020 and the expand/collapse pattern already validated in Slice 8f. The existing `OI_SESSION_DIR` mechanism already supports separate KG directories — the plumbing exists, it just needs orchestration.

  **Supersedes**: "Effort progress tracking & child node association" (above) — if efforts have their own KGs, child node association is automatic (nodes live in the effort's graph), and progress tracking becomes graph-level metrics (node count, edge count, confidence distribution over time).

---

## Near-Term Goals

- **Full physics theory batch ingestion.** Get the ingest pipeline (extraction + linking) working reliably for scientific content, then switch the LLM to a local model and run the entire physics theory ChatGPT export (~188 conversations) as an unattended multi-day batch job. This eliminates API cost as a constraint and produces the first complete single-author knowledge graph — the dataset Paper 3 needs for its headline claims. Prerequisites: ingestion resume/checkpoint (icebox item), local model validation (confirm extraction + linking quality matches Cerebras `gpt-oss-120b`), and confidence that the pipeline won't produce garbage at scale.

---

## Related Documents

- [CCM Whitepaper](../ccm-whitepaper.md) — Published (Slices 1-4)
- [Thesis](../thesis.md) — Knowledge Network vision (Theses 2-5, hybrid endgame)
- [Technical Reference](../PROJECT.md) — Architecture (needs update)
- [Scenarios](08-knowledge-graph-scenarios.md) — Slice 8 UX walkthroughs
