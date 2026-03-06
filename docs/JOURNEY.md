# Journey Log

> Where we are in implementing the thesis. For humans and agents to regain context.

## Source of Truth

- **Big picture**: [BIG-PICTURE.md](BIG-PICTURE.md) - 5 phases from KG to Open Systems
- **Thesis**: [thesis.md](thesis.md) - The 5 core theses and vision
- **Slices**: [slices/README.md](slices/README.md) - Tactical implementation roadmap
- **Technical**: [PROJECT.md](PROJECT.md) - Current architecture and code structure

Read those first. This doc tracks **implementation progress and pivots**.

---

## Current Status: Phase 1 Complete, White Paper Experiment In Progress

Slices 1-14b complete. The Python prototype is proven — 731 tests, full ingestion + enrichment pipeline working, MCP server live.

**Physics theory KG**: 894 active nodes, 5020 edges across 9 sources (7 author conversations + 2 cross-author SEP articles). Three-way interaction analysis (author theory vs GRW collapse vs standard QM foundations) in progress.

**Rust port deferred** (2026-03-03): Python performance is acceptable. Bottleneck is LLM API calls, not Python. See [Decision 016](decisions/016-rust-wasm-port.md) for future triggers.

**White paper**: [topological-truth-paper.md](research/topological-truth-paper.md) — "Living Knowledge Networks: Topological Truth Without Voting." Multi-source empirical data now collected, needs update with cross-author findings.

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
| 12a | Done | Graph walk layer: expand candidates 1-2 hops with decay scoring (0.7x/0.4x), convergence boosts. |
| 12b | Done | Embedding search: semantic seeds via Ollama (nomic-embed-text, local GPU). Configurable via `OI_EMBED_MODEL`. |
| 12c | Done | Batch LLM classification: 1 prompt for N candidates, containment ratio for short queries, result cap. |
| 13a | Done | Document parser: markdown/PDF/plain text, section chunking, metadata extraction. |
| 13b | Done | Claim extraction: LLM extracts discrete nodes from chunks, `skip_linking`/`skip_embed` flags for batch. |
| 13c | Done | Graph-aware batch linker: `link_new_nodes()` with full graph visibility, symmetric pair dedup. |
| 13d | Done | Conflict resolution: topology-based classification (`auto_resolvable`/`strong_recommendation`/`ambiguous`), `resolve_conflict`, `auto_resolve`. |
| 13e | Done | Pipeline orchestrator: `ingest_pipeline()` (parse→extract→write→link→embed→report), `mcp_ingest_document` MCP tool, ChatGPT export ingestion. |
| 14a | Done | Edge weight by reasoning quality (1.0x with reasoning, 0.5x without in PageRank). Salience metric from `related_to` density. `sort_by` param in query. |
| 14b | Done | Concept nodes from embedding clusters: `find_clusters()` + `synthesize_concepts()` pipeline stages, `principle` nodes with `exemplifies` edges. |

**Test counts**: 731 free tests + 55 LLM tests (marker-separated). 1 skipped.

### Session: Document Ingestion Resume (2026-03-05)

Added `skip_existing` to `ingest_pipeline()` — checks `doc://` provenance URIs in the graph before parsing/extracting. Already-ingested documents are skipped with zero LLM calls.

**Bug found during live testing**: `thesis.md` originally ingested with `source_id="knowledge-network-docs"` (provenance: `doc://knowledge-network-docs/thesis.md#...`) was **not** skipped when re-ingested without a source_id (expected: `doc://thesis.md#...`). Created 223 duplicate nodes before the issue was caught. Root cause: skip check only matched the exact prefixed form. Fix: match by filename across any source_id prefix — `p == rel_str or p.endswith(f"/{rel_str}")`. Two regression tests added (`test_skip_cross_source_id`, `test_skip_cross_source_id_reverse`).

### Session: Decision 020 — Salience, Edge Weights, Concept Nodes (2026-03-04)

Implemented [Decision 020](decisions/020-salience-confidence-separation.md) in three phases:

1. **Edge weight by reasoning quality (14a)**: `confidence.py` now weights edges 1.0x when reasoning is present, 0.5x when absent. All existing edges default to 0.5x. PageRank iteration and contribution calculation both use weights. 6 new tests, 4 existing tests updated.

2. **Salience metric (14a)**: New `compute_salience()` counts bidirectional `related_to` edges per node, normalizes to 0.0–1.0. `query_knowledge()` accepts `sort_by` param ("salience", "confidence"). MCP server displays salience in results. 6 new tests.

3. **Concept nodes from embedding clusters (14b)**: New `cluster.py` — greedy cosine similarity clustering (threshold 0.85), LLM synthesis of `principle` nodes with `exemplifies` edges. Pipeline stages (optional via `skip_clustering`). 11 new tests.

4. **JSON parsing hardened**: LLMs sometimes emit control characters or truncated JSON. Extracted `_parse_llm_json()` helper that sanitizes control chars and repairs truncated arrays by finding the last complete object. 11 new tests. Addresses anomaly `llm-json-truncation` (2 occurrences).

5. **Real data validation**: Ingested `docs/thesis.md` (230 nodes, 1205 edges), `docs/BIG-PICTURE.md` (85 nodes, 424 edges), `docs/PROJECT.md` (114 nodes, 129 edges, 72 concept nodes synthesized). Graph now at 908 active nodes.

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

### Session: Search + Ingestion Pipeline (2026-03-02 to 2026-03-03)

Built the complete search infrastructure and ingestion pipeline across multiple sessions:

1. **Search Infrastructure (12a-c)**: Three-layer pipeline — keyword seeds, graph walk expansion (1-2 hops with decay), semantic embedding via Ollama (nomic-embed-text, local GPU). Batch LLM classification replaces N per-pair calls with one prompt. Switched from cloud embeddings to local Ollama for cost/speed.

2. **Document Parser (13a)**: Markdown/PDF/plain text support. Section-aware chunking with metadata extraction. Handles frontmatter, heading hierarchy, code blocks.

3. **Claim Extraction (13b)**: LLM extracts discrete knowledge nodes from document chunks. Added `skip_linking`/`skip_embed` flags to `add_knowledge()` for batch operations (link separately in Pass 2).

4. **Batch Linker (13c)**: `link_new_nodes()` with full graph visibility. Symmetric pair deduplication. Progress callbacks. First run on thesis.md: 236 nodes, 877 edges, 37 contradictions found.

5. **Conflict Resolution (13d)**: Topology-based classification. Three priority tiers: `auto_resolvable` (facts, ≥5x ratio), `strong_recommendation` (≥2-3x), `ambiguous` (equal/near-equal). Auto-resolved 6/37 with zero LLM calls. Key finding: the system validated its own thesis — topology-as-confidence (28 supports) beat voting-as-confidence (4 supports) in Resolution 6.

6. **Emergent insight**: Topology-based conflict resolution constitutes a novel form of reasoning. Independent structural convergence as a mechanical analog of scientific replication. Paper in progress.

### Session: Slice 13e + Rust Port Decision (2026-03-03)

1. **Slice 13e implementation**: Built `ingest_pipeline()` orchestrator (parse→extract→write→link→embed→report) and `mcp_ingest_document` MCP tool with dry-run and skip_linking modes. 561 tests passing (+9 new). Added anomaly tracking ledger (`anomalies.yaml`).

2. **Batch ingestion test**: Ingested `conflict-resolution-findings.md` — 99 nodes, 221 edges, 18 contradictions. One chunk failed JSON parse (LLM truncation) — first anomaly logged. Dry-ran 5 more docs: 634 claims across 120 chunks.

3. **Rust ecosystem research**: Discovered every assumed Rust blocker was wrong:
   - MCP: `rmcp` v0.16 (official Anthropic SDK)
   - LLM: `litellm-rs`, `rig` framework
   - CRDTs: Native Automerge, Loro, y-crdt (all Rust-first)
   - PDF: `pdf_oxide` (5x faster than pypdf)
   - AI agents: Multiple production frameworks (rig, agentai, AutoAgents)

4. **Big picture roadmap**: Documented 6-phase vision from current KG through decentralized AI on blockchain. Key insight: WASM is the convergence point — Rust compiles to both native and WASM smart contracts from the same codebase.

5. **Decision 016**: Port to Rust with WASM targets. CRDT-backed `GraphStore` trait (backend-agnostic). Python prototype remains as reference. See [Decision 016](decisions/016-rust-wasm-port.md).

### Session: Cross-Author Analysis (2026-03-05)

Re-ingested all 7 physics theory conversations + SEP "Collapse Theories" article into a fresh v2 graph with all current pipeline features (Decisions 019, 020, 021). Key findings:

1. **Cross-author edges**: 293 total (24 supports, 24 contradicts, 245 related_to). All flow SEP → theory.
2. **95% of theory nodes have zero cross-author contact** — the theory extends far beyond what GRW/CSL collapse theories address.
3. **Contact surface**: Only 34 theory nodes connected, all clustered around double-slit experiment and collapse mechanism.
4. **Core disagreement**: Conditional (entropy-triggered) vs unconditional (spontaneous) collapse — 22/24 contradictions trace to this single fork.
5. **Unique theory territory**: Parent/child universe cosmology, anchors/fluctuations as novel primitives, dark matter/energy replacement, emergence of spacetime, named formal principles.
6. **False positive rate**: 3/27 contested nodes (11%), up from 0% in v1. Cross-author content introduces scope/framing mismatches.

See [cross-author-analysis.md](research/cross-author-analysis.md) for full writeup.

### Session: Standard QM Ingestion (2026-03-05)

Ingested SEP "Philosophical Issues in Quantum Theory" (Myrvold) as a third cross-author source for three-way interaction testing.

**Results**: 118 nodes (98 claims + 20 concept clusters), 608 edges, 7 contradictions. All 7 contradictions are genuine — Everettian/pilot-wave theories (which reject collapse) vs the author's collapse-based theory.

**Three-way graph totals**: 894 active nodes, 5020 edges (1198 supports, 3618 related_to, 163 contradicts, 41 exemplifies). Sources: 730 theory nodes, 66 SEP-collapse nodes, 98 SEP-QT nodes.

**Cross-author edges (QT article)**: 391 total (373 related_to, 11 supports, 7 contradicts). The QT article has broader topical overlap (391 edges vs SEP-collapse's 293) but fewer contradictions (7 vs 24) — because it describes the measurement problem landscape rather than advocating a specific mechanism.

**Inter-SEP edges**: Only 5 edges between the two SEP articles (all related_to) — they cover different aspects of the same field without directly contradicting each other.

See [v2-reingestion-findings.md](research/v2-reingestion-findings.md) for the full experiment writeup.

### What's Next

See [BIG-PICTURE.md](BIG-PICTURE.md) for big picture. Immediate:
1. **Run conflict resolution** on the full 3-source graph (free, no LLM calls)
2. **Three-way interaction analysis** — where do all 3 sources agree? Where does each stand alone?
3. **White paper update**: Incorporate multi-source data, cross-author findings, revised limitations
4. **Batch physics conversations**: Process remaining ~181 physics theory ChatGPT conversations (resume/checkpoint implemented)

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

1. **Read [BIG-PICTURE.md](BIG-PICTURE.md)** — big picture (6 phases, KG → blockchain)
2. **Read [thesis.md](thesis.md)** — understand the vision (5 theses)
3. **Read [Decision 016](decisions/016-rust-wasm-port.md)** — Rust port decision + migration sequence
4. **Current work**: White paper experiment — multi-source physics KG analysis. Python prototype is the reference implementation.

### Key Research Docs

| Doc | Contents |
|-----|----------|
| [v2-reingestion-findings.md](research/v2-reingestion-findings.md) | Full v2 experiment: v1 vs v2 metrics, contested node classification, pipeline performance |
| [cross-author-analysis.md](research/cross-author-analysis.md) | SEP collapse theories vs physics theory: edge analysis, unique concepts, contact surface |
| [ingestion-pipeline-experiments.md](research/ingestion-pipeline-experiments.md) | Iterative linker improvement (5 runs, same doc, prompt tuning) |
| [conflict-resolution-findings.md](research/conflict-resolution-findings.md) | First conflict resolution run: topology-based classification |
| [ingestion-resume-findings.md](research/ingestion-resume-findings.md) | skip_existing feature and cross-source-id bug |
| [topological-truth-paper.md](research/topological-truth-paper.md) | White paper draft: "Living Knowledge Networks" |
| [paper-roadmap.md](research/paper-roadmap.md) | Paper strategy and publication targets |

### Physics Theory KG

**Location**: `/data/physics-theory-kg/`
**MCP server**: `physics-theory` (configured in `.mcp.json`)
**Source conversations**: `/data/physics-theory/*.json` (188 total, 7 ingested so far)
**Cross-author docs**: `/data/physics-theory/cross-author/` (2 SEP articles ingested)

### Environment Notes

- **OS**: CachyOS (Arch-based), migrated from NixOS on 2026-03-06
- **MCP wrapper**: `bin/oi-mcp` — thin wrapper calling `.venv/bin/oi-mcp`
- **Venv**: `.venv/` in project root (Python 3.14)
- **Test command**: `.venv/bin/python -m pytest` (see CLAUDE.md for details)
- **LLM**: Cerebras `gpt-oss-120b` via `OI_MODEL` in `.env`. API key: `CEREBRAS_API_KEY`
- **Embeddings**: Local Ollama `nomic-embed-text` (GPU)
- **Budget**: ~$12 Cerebras credits remaining as of 2026-03-05
