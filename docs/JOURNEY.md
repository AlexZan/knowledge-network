# Journey Log

> Where we are in implementing the thesis. For humans and agents to regain context.

## Source of Truth

- **Big picture**: [BIG-PICTURE.md](BIG-PICTURE.md) - 5 phases from KG to Open Systems
- **Thesis**: [thesis.md](thesis.md) - The 5 core theses and vision
- **Slices**: [slices/README.md](slices/README.md) - Tactical implementation roadmap
- **Technical**: [PROJECT.md](PROJECT.md) - Current architecture and code structure

Read those first. This doc tracks **implementation progress and pivots**.

---

## Current Status: Phase 1 Complete, v4 KG Rebuilt, Linking Pipeline Enhanced

Slices 1-14b complete. The Python prototype is proven — 810 unit tests (15s), full ingestion + enrichment pipeline working, MCP server live.

**Physics theory KG**: 2,361 active nodes, 0 edges (v4 rebuild — nodes extracted, linking pending GPU reboot for Ollama). v3 backed up at `/data/physics-theory-kg-v3/`.

**Rust port deferred** (2026-03-03): Python performance is acceptable. Bottleneck is LLM API calls, not Python. See [Decision 016](decisions/016-rust-wasm-port.md) for future triggers.

**White paper**: [topological-truth-paper.md](papers/02-topological-truth/topological-truth-paper.md) — "Topological Truth: Conflict Resolution Through Knowledge Graph Structure." Needs update with v3 rebuild data (1,336 nodes, false positive analysis from manual review).

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

**Test counts**: 810 unit tests (15s) + 55 LLM tests (marker-separated). 1 skipped. Three-tier test system: unit (default), integration (Ollama), llm (remote APIs).

### Session: v4 Rebuild, Auto-Linking, Test Isolation (2026-03-11)

Major session covering extraction improvements, linking pipeline enhancements, and test infrastructure overhaul.

**ChatGPT parser fix**: Conversations with browsing/code interpreter results have `tool` role messages between user and assistant. Parser now scans forward past tool/system/user messages to find the assistant response. Recovered 65 previously-missed conversations. Also handles consecutive user message merging and empty assistant prefixes (thinking steps). 7 new tests.

**v4 KG rebuild**: Full re-ingestion of 185 ChatGPT conversations + 20 project source files (markdown + PDF) + SEP cross-author documents. Extraction prompt improved to handle assistant elaborations at user's request (previously too strict — caused 53/185 conversations to return 0 claims). Added early-stop mechanism (aborts after 5 consecutive empty results) as safety net. Result: 2,361 active nodes across ~205 sources.

**Same-conversation auto-linking**: New `auto_link_same_group()` creates `related_to` edges between nodes from the same conversation/document for free (zero LLM cost). `find_candidates()` now accepts `exclude_same_group=True` to filter same-provenance candidates, focusing LLM classification on cross-source bridges. This creates intra-conversation graph depth before the expensive cross-group linking pass. 13 new tests.

**Cosine similarity analysis**: Evaluated adding cosine similarity to candidate finding on the 2,361-node KG. Keyword Jaccard already saturates (80% of nodes hit the 8-candidate cap), and candidates are high quality cross-source. Cosine would only help with divergent terminology across authors — not needed for this single-author domain. Decision: defer until multi-author KGs or visible quality degradation.

**Test isolation overhaul**: Discovered 5 test files were making real Ollama HTTP calls through `add_knowledge()` (which defaults to embedding + linking). This caused the test suite to take 45s instead of 15s. Root cause: `add_knowledge()` defaults `skip_embed=False, skip_linking=False`, and tests written before these features were added never updated.

Fix: Added autouse `_no_external_calls()` fixture to all affected files (patches `oi.embed.get_embedding` and `oi.linker.chat`). Established three-tier test system:
- **unit** (default, `pytest`): Pure logic, all I/O mocked. 810 tests, 15s.
- **integration** (`pytest -m integration`): Local services like Ollama. Free but slow.
- **llm** (`pytest -m llm`): Remote APIs (Cerebras). ~$1/run, explicit approval only.

Both `integration` and `llm` are excluded by default in `pyproject.toml`. CLAUDE.md updated with "Test Tiers" and "Unit Test Isolation" sections.

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

See [cross-author-analysis.md](research/experiments/cross-author-analysis.md) for full writeup.

### Session: Standard QM Ingestion (2026-03-05)

Ingested SEP "Philosophical Issues in Quantum Theory" (Myrvold) as a third cross-author source for three-way interaction testing.

**Results**: 118 nodes (98 claims + 20 concept clusters), 608 edges, 7 contradictions. All 7 contradictions are genuine — Everettian/pilot-wave theories (which reject collapse) vs the author's collapse-based theory.

**Three-way graph totals**: 894 active nodes, 5020 edges (1198 supports, 3618 related_to, 163 contradicts, 41 exemplifies). Sources: 730 theory nodes, 66 SEP-collapse nodes, 98 SEP-QT nodes.

**Cross-author edges (QT article)**: 391 total (373 related_to, 11 supports, 7 contradicts). The QT article has broader topical overlap (391 edges vs SEP-collapse's 293) but fewer contradictions (7 vs 24) — because it describes the measurement problem landscape rather than advocating a specific mechanism.

**Inter-SEP edges**: Only 5 edges between the two SEP articles (all related_to) — they cover different aspects of the same field without directly contradicting each other.

See [v2-reingestion-findings.md](research/experiments/v2-reingestion-findings.md) for the full experiment writeup.

### Session: CachyOS Migration + Conflict Resolution (2026-03-06)

Migrated from NixOS to CachyOS. Updated all paths, rebuilt venv (Python 3.14), verified MCP servers, 731 tests passing.

Ran conflict resolution on the full 3-source physics graph:
- 163 contradictions → 112 auto-resolved (67% rate, up from 16% on the 236-node graph)
- 36 remaining: 11 strong recommendations, 25 ambiguous
- Three-way analysis updated: all 4 "battleground" nodes survived, only 1 cross-author contradicts edge remains

**Major finding during conflict review**: The current ingestion pipeline extracts claims per-turn-pair in isolation, causing false intra-author contradictions (same person refining their position across turns). See [Decision 022](decisions/022-conversation-aware-extraction.md). This invalidates the current physics KG — rebuild required after pipeline improvement.

### Session: Conversation-Aware Extraction + KG Rebuild (2026-03-07 to 2026-03-08)

Implemented Decision 022 (conversation-aware extraction), rebuilt the physics KG at full scale, and began manual conflict review.

**Phase 1-2: Pipeline upgrade**
- `extract_from_conversation()`: Full-conversation LLM calls instead of per-turn-pair chunking. Single-call path for conversations within context window, iterative node-carry-forward for larger ones.
- Wired into `ingest_chatgpt_export()`. Document ingestion (.md/.pdf) unchanged.
- Removed all zip file references from codebase (lesson learned from earlier).
- LLM model: `cerebras/gpt-oss-120b` ($0.35/M input, 128K context). Previous `llama-3.3-70b` no longer available on Cerebras.

**Phase 3: Full KG rebuild**
- Backed up old KG (894 nodes) to `knowledge.yaml.pre-022-backup`
- Ingested **all 120 conversations** + 2 SEP articles (previously only 7+2)
- Results: **1,336 nodes** (1,263 active), **8,022 edges** (5,981 related_to, 1,849 supports, 113 supersedes, 79 contradicts after auto-resolution)
- Sources: 1,104 physics-theory nodes, 99 SEP-QT nodes, 59 SEP-collapse nodes
- 1 failed conversation (`68028f8e` — LLM returned experimental plan instead of JSON, logged as anomaly)
- Auto-resolved 111 conflicts, 37 remained for manual review (14 strong recommendations, 23 ambiguous)

**Decision 023: Edge reclassification with review provenance**
- `reclassify_edge()` changes edge types with reasoning + raw chat excerpt saved to `{session_dir}/reviews/`
- `mark_reviewed()` annotates edges as reviewed without changing type (deferred/uncertain/approved)
- Review provenance files referenced via `review://` URI scheme

**Decision 024: TOTP review attestation (draft)**
- Time-based one-time password for cryptographically attributing human review sign-off
- Solves: AI has full write access to KG/git/metadata — TOTP is the only unforgeable proof of human involvement
- Deferred until multi-user or high-stakes scenarios

**Decision 025: Effort-edge linking via metadata**
- Optional `effort` field on edges links deferred conflicts to investigation efforts
- Lightweight: no new edge types, no graph bloat, grep-discoverable

**Manual conflict review (20/37 reviewed)**
- 7 reclassified `contradicts` → `related_to` (false positives from scope/framework mismatch)
- 2 reclassified `contradicts` → `supports` (contrapositives and split principles)
- 5 kept as `contradicts` (genuine: terminology conflicts, speculative vs firm, cross-source rivalries)
- 3 deferred with efforts (theory evolution, low-confidence claim, attribution gap)
- 17 deferred batch (S18-S34, intra-theory, domain expert review needed)
- 2 reverted (S9, S14): initially reclassified to `related_to`, then reverted to `contradicts` after realizing terminology conflicts should keep their signal until the node is superseded
- `/review-conflicts` skill created for the review workflow

**Key findings from review**:
1. **Five false positive patterns**: scope mismatch, framework difference, evolutionary refinement, terminology conflict, assistant-elevation (assistant restates user spitballing as firm principle).
2. **Temporal signal**: `authored_at` timestamps reveal theory evolution — conflicts between nodes authored weeks apart often represent refinements, not contradictions.
3. **Context gap**: The linker LLM had full conversation context during extraction but only node summaries during linking. This causes misclassification.
4. **The revert pattern** (paper-worthy): Terminology conflicts should keep their `contradicts` edge — the signal is valid *as written* even when underlying concepts are compatible. Don't lose information prematurely. No other KG system reports this nuance.
5. **Cross-source validation**: System correctly identifies known scientific rivalries (GRW vs Bohm) and intentionally presented debates in survey articles. Also exposed attribution gap — third-party knowledge in user chat gets wrong source attribution.
6. **Gaps identified** (added to Planned, 8 items total):
   - Block-level provenance, context-aware linking, canvas-aware routing
   - Extraction-phase deduplication (split principles)
   - Terminology conflict resolution flow
   - Process/sequence edge types (`precedes`/`leads_to`)
   - Attribution-aware extraction with epistemic status
   - TOTP review attestation

See [v3-rebuild-findings.md](research/experiments/v3-rebuild-findings.md) for full results.

**Test counts**: 787 free tests passing, 1 skipped (pre-existing).

**Extraction improvements** (2026-03-09):
- `_chat_with_retry()` — 1 retry on JSON parse failure, no retry on other errors
- Canvas-aware extraction routing — canvas chunks (`#canvas-N`) routed to per-chunk extraction, conversation turns to conversation-aware path
- Prompt fixes: composite principle splitting (#4), attribution/epistemic awareness (#7) — both addressed with extraction prompt instructions rather than post-processing passes
- Source quote extraction (#1) — `source_quote` field on claims and nodes, verbatim text from source for downstream context-aware linking
- Context-aware linking (#2) — linker prompts now include `source_quote` alongside summaries for both single-pair and batch classification
- Terminology correction flow (#5) — `correct_terminology()` + MCP tool for fixing terminology conflicts without losing contradiction signal

### What's Next

**Planned features**: See [slices/README.md](slices/README.md#planned). Remaining: #6 process/sequence edges, #8 TOTP attestation.

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
| [v2-reingestion-findings.md](research/experiments/v2-reingestion-findings.md) | Full v2 experiment: v1 vs v2 metrics, contested node classification, pipeline performance |
| [cross-author-analysis.md](research/experiments/cross-author-analysis.md) | SEP collapse theories vs physics theory: edge analysis, unique concepts, contact surface |
| [ingestion-pipeline-experiments.md](research/experiments/ingestion-pipeline-experiments.md) | Iterative linker improvement (5 runs, same doc, prompt tuning) |
| [conflict-resolution-findings.md](research/experiments/conflict-resolution-findings.md) | First conflict resolution run: topology-based classification |
| [v3-rebuild-findings.md](research/experiments/v3-rebuild-findings.md) | Full-scale rebuild: 120 conversations, conversation-aware extraction, conflict review |
| [ingestion-resume-findings.md](research/experiments/ingestion-resume-findings.md) | skip_existing feature and cross-source-id bug |
| [topological-truth-paper.md](papers/02-topological-truth/topological-truth-paper.md) | White paper draft: "Topological Truth" |
| [paper-roadmap.md](papers/paper-roadmap.md) | Paper strategy and publication targets |

### Physics Theory KG

**Location**: `/data/physics-theory-kg/`
**MCP server**: `physics-theory` (configured in `.mcp.json`)
**Source conversations**: `/data/physics-theory/*.json` (188 total, 120 ingested, 1 failed)
**Cross-author docs**: `/data/physics-theory/cross-author/` (2 SEP articles ingested)
**Reviews**: `/data/physics-theory-kg/reviews/` (8 conflict review provenance files)

### Environment Notes

- **OS**: CachyOS (Arch-based), migrated from NixOS on 2026-03-06
- **MCP wrapper**: `bin/oi-mcp` — thin wrapper calling `.venv/bin/oi-mcp`
- **Venv**: `.venv/` in project root (Python 3.14)
- **Test command**: `.venv/bin/python -m pytest` (see CLAUDE.md for details)
- **LLM**: Cerebras `gpt-oss-120b` via `OI_MODEL` in `.env`. API key: `CEREBRAS_API_KEY`
- **Embeddings**: Local Ollama `nomic-embed-text` (GPU)
- **Budget**: ~$12 Cerebras credits remaining as of 2026-03-05
