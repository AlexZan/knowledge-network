# Big Picture Roadmap

> From knowledge graph to decentralized AI on the blockchain.

For tactical slice-by-slice progress, see [slices/README.md](slices/README.md).
For implementation history, see [JOURNEY.md](JOURNEY.md).
For the Rust port decision, see [Decision 016](decisions/016-rust-wasm-port.md).

---

## Vision

A decentralized AI system built on persistent, shared knowledge. Agents accumulate understanding across sessions. Context survives compaction. Multiple agents collaborate through a CRDT-synced graph while maintaining independent perspectives. Knowledge graph operations compile to WASM and run on-chain as smart contracts. The system starts as a dev tool and grows into the foundation for Open Systems — eventually running on its own blockchain, developed with these same AI systems.

---

## Technology Foundation

**Language**: Rust — compiles to both native binaries and WASM smart contracts. Same code, both targets. See [Decision 016](decisions/016-rust-wasm-port.md).

**Storage**: CRDT-backed `GraphStore` abstraction — Automerge, Loro, or y-crdt behind a trait. Concurrent writes, full history, eventual P2P sync. See [Decision 013](decisions/013-unified-kg-architecture.md).

**Interface**: MCP server via `rmcp` (official Rust SDK). LLM calls via `litellm-rs` or `rig`.

**Portability**: Core graph operations target `wasm32-unknown-unknown` from day one. Ensures on-chain deployment without rewriting.

---

## Phase 1: Knowledge Network (Python prototype) ✓

**What**: Persistent memory through conclusion-triggered compaction. Knowledge graph with topology-based confidence. Bulk document ingestion. MCP interface for Claude Code.

**Status**: Complete. 561 tests passing. Pipeline proven on real documents — 99-233 claims extracted per doc, topology-based conflict resolution working (auto-resolved 6/37 conflicts with zero LLM calls).

**Key capabilities**:
- Effort lifecycle (open → work → close → summary → knowledge extraction)
- Knowledge graph with typed nodes, edges, confidence from topology
- Graph-aware search (keyword → graph walk → embeddings → LLM classify)
- Bulk document ingestion (parse → extract → link → embed → conflict report)
- MCP server exposing all tools to Claude Code
- Provenance linking (every node traces to its source conversation)

**Outcome**: Validated the knowledge graph model. Python prototype serves as reference implementation during Rust port.

---

## Phase 2: Rust Port + CRDT Storage (Next)

**What**: Port the Knowledge Network from Python to Rust. Replace YAML with CRDT storage. Compile core graph ops to WASM.

**Why now**: Multiple agents already hit the graph simultaneously. YAML has no locking — concurrent writes corrupt data. Python's Automerge bindings are broken. The codebase is only 5,830 LOC — it will only get bigger. See [Decision 016](decisions/016-rust-wasm-port.md).

**Migration sequence**:

| Step | What | Depends on |
|------|------|------------|
| **A** | Rust scaffold + `GraphStore` trait + data models (`serde`) | — |
| **B** | Core graph ops: add/query, graph walk, confidence, conflicts | A |
| **C** | LLM integration (`litellm-rs`/`rig`) + MCP server (`rmcp`) + parser (`pdf_oxide`) | B |
| **D** | CRDT backend (Automerge or Loro behind `GraphStore`) + migrate `knowledge.yaml` | C |
| **E** | WASM targets for core graph ops — validate in WasmEdge/browser | D |

**Key capabilities**:
- Concurrent writes from multiple agents/processes (CRDT)
- Full mutation history (every change preserved)
- `GraphStore` trait: CRDT-agnostic, backend-swappable
- Core graph ops compile to WASM
- MCP server via `rmcp` (official Rust SDK)
- Python version remains operational throughout migration

**Outcome**: Feature parity with Python, plus concurrent storage and WASM portability.

---

## Phase 3: CCM Integration

**What**: Context Compaction Memory backed by the knowledge graph. Agents run indefinitely — context compaction preserves conclusions as graph nodes instead of discarding them. Cross-agent context sharing through the CRDT-synced graph.

**Key capabilities**:
- Conclusion-triggered compaction writes to the KG (not just summaries)
- Agents share knowledge through the graph, not by passing raw context
- Each session/agent develops its own perspective ([Decision 014](decisions/014-sessions-as-perspectives.md))
- Session history remains accessible for provenance and replay
- Compaction is lossless at the knowledge level — only raw conversation tokens are shed
- CRDT sync enables multi-agent knowledge sharing without coordination

**Depends on**: Phase 2 (CRDT storage for concurrent multi-agent writes).

---

## Phase 4: TDD Dev Workflow

**What**: Resurrect and adapt the oi-pipe TDD pipeline so that workflow artifacts become knowledge graph nodes. The pipeline feeds the graph and the graph informs the pipeline.

**Key capabilities**:
- Pipeline stages (brainstorm → scenarios → stories → tests → dev → qa) produce KG nodes
- Scenarios, stories, and test results are typed nodes with edges to motivating decisions/facts
- The graph accumulates project understanding across dev cycles
- Test failures, design decisions, and lessons learned persist as first-class knowledge
- Pipeline can query the graph for prior art, related decisions, known pitfalls
- Workflow artifacts are WASM modules in the graph (portable, verifiable)

**Depends on**: Phase 3 (CCM) so the dev agent can run indefinitely across large features.

---

## Phase 5: Open Systems — Experience System

**What**: Combine the knowledge network with the Open Systems experience system. Knowledge becomes the substrate for lived experience, learning, and adaptation.

**Key capabilities**:
- Experience system built on knowledge graph primitives
- Agents accumulate experiential knowledge (not just facts/decisions)
- Cross-domain knowledge transfer (dev insights inform design insights, etc.)
- The graph becomes a shared organizational memory
- Smart contracts govern knowledge operations (add, link, resolve conflicts)
- CRDT-synced graph spans multiple machines / agents / organizations

**Depends on**: Phase 4 (dev workflow proven at scale).

---

## Phase 6: Decentralized Knowledge — Blockchain

**What**: Knowledge graph operations run on-chain. The network itself becomes a decentralized, distributed AI system with a dynamic, ever-growing model.

**Key capabilities**:
- Core graph ops (already WASM from Phase 2) deployed as smart contracts
- CosmWASM / custom chain — knowledge operations are first-class on-chain primitives
- Topology-based confidence as on-chain consensus mechanism
- AI agents as WASM components on the network
- The knowledge network integrates into its own blockchain
- Eventually: custom blockchain developed with these same AI systems

**Architecture**:
```
Rust graph ops → compile to WASM → deploy as smart contracts
CRDT sync      → P2P between nodes → eventual consistency
AI agents      → WASM components   → portable across the network
Knowledge      → on-chain state    → decentralized, verifiable
```

**Depends on**: Phase 5 (experience system validated at scale).

---

## Principles Across All Phases

These hold from Phase 1 through Phase 6:

- **Topology is authority** — confidence from network structure, not explicit scores
- **Conclusions, not compression** — compact when reasoning resolves, not when memory fills
- **Everything is a node** — efforts, facts, decisions, principles, experiences
- **Provenance is non-negotiable** — every node links to its source
- **Perspectives, not consensus** — agents develop independent viewpoints; the graph holds all of them
- **Primitives, not frameworks** — composable building blocks, not monolithic applications
- **Write once, run anywhere** — Rust → WASM → native + on-chain from the same codebase
- **AI builds AI** — development velocity comes from AI-assisted development, not language ergonomics

---

## Key Decisions

| Decision | Summary |
|----------|---------|
| [013: Unified KG Architecture](decisions/013-unified-kg-architecture.md) | Mutability gradient, CRDT storage, reactive edges |
| [014: Sessions as Perspectives](decisions/014-sessions-as-perspectives.md) | Multi-agent perspectives, roundtable debate |
| [016: Rust + WASM Port](decisions/016-rust-wasm-port.md) | Port to Rust, CRDT-backed GraphStore trait, WASM targets |

## Research

| Doc | Topic |
|-----|-------|
| [Rust Port Analysis](research/rust-port-analysis.md) | Ecosystem evaluation, crate mapping |
| [Language & Storage Decision](research/language-and-storage-decision.md) | CRDT comparison, endgame language analysis |
