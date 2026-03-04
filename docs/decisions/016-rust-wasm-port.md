# Decision 016: Port to Rust with WASM Targets

**Date**: 2026-03-03
**Status**: Deferred

---

## Context

The Knowledge Network is a 5,830 LOC Python codebase (23 modules, 561 tests). Phase 1 is complete — persistent knowledge graph with topology-based confidence, bulk ingestion, MCP server. The project now faces two simultaneous pressures:

1. **Concurrent storage**: Multiple agents already write to the graph simultaneously (dev agent, paper writer, ingestion pipeline). YAML has no locking — concurrent writes corrupt data. The thesis ([Decision 013](013-unified-kg-architecture.md)) calls for Automerge/CRDT storage, but Python's Automerge bindings are broken (v0.1.2, low-level only, can't build from git).

2. **Endgame architecture**: The [big picture roadmap](../BIG-PICTURE.md) targets decentralized, distributed AI systems — smart contracts, eventually a custom blockchain, Open Systems with an experience system. Python cannot compile to WASM, cannot run in a blockchain VM, and cannot provide the memory safety guarantees required for consensus systems.

A research spike (2026-03-03) evaluated the Rust ecosystem and found every previously-assumed blocker has a production-ready solution. See [rust-port-analysis.md](../research/rust-port-analysis.md) and [language-and-storage-decision.md](../research/language-and-storage-decision.md).

## Decision

### 1. Port the Knowledge Network from Python to Rust

The codebase is small enough (5,830 LOC) that porting now is cheaper than porting later when it's larger. AI-assisted development mitigates Rust's learning curve — the token cost of a Rust implementation is comparable to Python.

### 2. Use CRDT-backed storage via a `GraphStore` abstraction

Don't commit to Automerge specifically. Build a `GraphStore` trait that hides the CRDT backend. Evaluate:

- **[Automerge](https://crates.io/crates/automerge)** — native Rust, v3, 10x memory reduction, JSON document model, full history
- **[Loro](https://loro.dev/)** — newer, Fugue algorithm (better merge), Tree data type for hierarchies, designed for embedding
- **y-crdt** — Yjs Rust port, most battle-tested CRDT (Jupyter, VS Code)

Pick based on benchmark results for our graph workload (append-heavy nodes + edges, occasional conflict resolution). The abstraction makes swapping trivial.

### 3. Compile to WASM from day one

Every module that could run on-chain should target `wasm32-unknown-unknown`. This means:

- Knowledge graph operations (add, query, link, conflict resolution) → WASM
- CRDT merge/sync logic → WASM
- LLM client calls and I/O stay native-only (network-bound, not portable)

The WASM constraint keeps the core logic pure and portable — a feature, not a burden.

### 4. Use the Rust ecosystem for all components

| Component | Crate | Notes |
|-----------|-------|-------|
| MCP server | `rmcp` (official, v0.16) | `#[tool]` macro, stdio transport |
| LLM calls | `litellm-rs` or `rig` | OpenAI-compatible, multi-provider |
| CRDT storage | `automerge` / `loro` / `y-crdt` | Behind `GraphStore` trait |
| Data models | `serde` + `garde` | Compile-time validation |
| PDF parsing | `pdf_oxide` | 5x faster than pypdf |
| HTTP/embeddings | `reqwest` | Ollama API (same HTTP interface) |
| YAML (migration) | `serde_yaml` | For reading existing knowledge.yaml during migration |
| Tokenization | `tiktoken-rs` | Already Rust under the hood |

## Rationale

### Why Rust over Python (for the endgame)

- **WASM target**: Same code runs locally (native) and on-chain (WASM smart contracts). No rewrite needed for CosmWASM, NEAR, Polkadot, or a custom chain.
- **CRDT native**: Automerge, Loro, y-crdt are all Rust-first. Python bindings are thin wrappers that don't expose the full API.
- **Blockchain ecosystem**: Solana, CosmWASM, NEAR, Polkadot, Stellar all use Rust. 1.5M+ blockchain projects use Rust as of 2026.
- **Memory safety**: Ownership model prevents entire vulnerability classes (reentrancy, use-after-free) — required for consensus systems.
- **Performance**: 5x memory, 10x latency vs Python agent frameworks (2026 AI Agent Benchmark).

### Why Rust over Go, Solidity, Move

- **Go**: Weak CRDT ecosystem, limited WASM support, limited AI tooling
- **Solidity**: EVM-only, no general-purpose programming
- **Move**: Tiny ecosystem, no CRDTs, no AI tooling

### Why now, not later

- Codebase is only 5,830 LOC — it will only grow
- Python has refactoring debt (32 delayed imports, 7 god functions, broken Automerge) — porting is cleaner than refactoring
- AI development velocity means token cost is comparable regardless of language
- CRDT storage is blocked in Python but native in Rust

### Why not a hybrid (Rust core + Python shell)

- Adds FFI complexity (PyO3 bindings) for every interface
- Two build systems, two test suites, two dependency chains
- The MCP server (the main entry point) has an official Rust SDK — no need for Python glue
- A clean port is simpler than a bridge

## Migration Strategy

### Phase A: Rust scaffold + `GraphStore` trait

Set up the Rust project structure, define the `GraphStore` trait (CRDT-agnostic), implement the data models (nodes, edges, confidence) with `serde`.

### Phase B: Core graph operations

Port `knowledge.py` (add/query), `search.py` (graph walk), `confidence.py`, `conflicts.py`. These are pure logic — no I/O, no LLM calls. Test against the Python implementation for parity.

### Phase C: LLM integration + MCP server

Port `llm.py` (via `litellm-rs` or `rig`), `linker.py`, `ingest.py`, `parser.py`. Build the MCP server with `rmcp`. This is the point where the Rust version becomes usable.

### Phase D: CRDT backend

Implement `GraphStore` with Automerge or Loro. Migrate existing `knowledge.yaml` data. Enable concurrent writes.

### Phase E: WASM targets

Compile core graph ops to WASM. Verify they run in a WASM runtime (WasmEdge or browser). This validates the on-chain path.

The Python codebase remains operational throughout — the Rust port runs in parallel until feature parity is reached.

## Consequences

**Positive**:
- Unblocks CRDT storage (currently impossible in Python)
- Same code targets native + WASM + on-chain
- 5-50x speedup on graph operations
- Memory safety for multi-agent and consensus
- Clean architecture (no more delayed import hacks)

**Negative**:
- Temporary velocity reduction during port (mitigated by AI-assisted dev)
- 561 tests need porting (Rust has excellent built-in testing)
- Team needs Rust familiarity (AI agents handle most of this)

**Neutral**:
- Python version remains as reference implementation
- Existing knowledge.yaml data migrates via serde_yaml → CRDT store

## Related

- [Decision 013: Unified KG Architecture](013-unified-kg-architecture.md) — established Automerge as storage target
- [Decision 014: Sessions as Perspectives](014-sessions-as-perspectives.md) — multi-agent perspectives require concurrent storage
- [Rust Port Analysis](../research/rust-port-analysis.md) — ecosystem evaluation
- [Language & Storage Decision](../research/language-and-storage-decision.md) — CRDT comparison + endgame language analysis
- [Big Picture Roadmap](../BIG-PICTURE.md) — 5-phase vision
