# Language & Storage Decision Analysis (2026-03-03)

Two open questions for the Knowledge Network's future architecture, evaluated against the endgame: **decentralized, distributed AI systems running on smart contracts, eventually on a custom blockchain, with the knowledge graph as the substrate.**

---

## Question 1: Why Automerge? Are There Alternatives?

### The Requirement

The knowledge graph needs concurrent writes from multiple agents, eventual consistency across distributed nodes, and merge without coordination. This is textbook CRDT territory.

### Options Evaluated

| Library | Language | Python Support | Maturity | Notes |
|---------|----------|---------------|----------|-------|
| **Automerge** | Rust (native) | Broken (v0.1.2 on PyPI, high-level API not published) | Production (v3, 10x memory reduction) | JSON document model. Used by Ink & Switch. Rich history tracking. |
| **Loro** | Rust (native) | [loro-py](https://github.com/loro-dev/loro-py) exists | Active, newer | Fugue algorithm (less interleaving). Text, List, Map, Tree, Counter. Designed to be embedded. |
| **Yjs** | JS (native) | [y-py](https://pypi.org/project/y-py/) (Rust port with Python bindings) | Production, most widely deployed | YATA algorithm. Best text collaboration. Modular. Garbage collection for memory. |
| **Diamond Types** | Rust | No Python bindings | Experimental | Fastest benchmarks but feature-incomplete. Text only. |

### Assessment

**Automerge is not the only option.** We settled on it because [Decision 013](../decisions/013-unified-kg-architecture.md) was written when it was the most visible Rust CRDT. But:

- **Loro** is newer, faster, has working Python bindings, and was designed for exactly our use case (embeddable CRDT engine with rich data types). Its Tree type is interesting for hierarchical knowledge structures.
- **y-py** (Yjs Rust port) has production Python bindings and is the most battle-tested CRDT in production (used by Jupyter, VS Code, etc.).
- **If we port to Rust**, all three become native options. The choice between them is an implementation detail, not an architectural commitment.

**Key insight**: The CRDT choice matters less than the **storage abstraction**. If we build a clean `GraphStore` trait/interface, we can swap Automerge for Loro or Yjs without touching the rest of the system. The decision is about the interface, not the backend.

### Python-Only Path

If we stay in Python:
- **y-py** is the most viable (production bindings, actively maintained)
- **loro-py** is promising but younger
- **automerge-py** is broken and should not be used

**Verdict on Q1**: Don't commit to Automerge specifically. Commit to a **CRDT-backed storage abstraction**. If we port to Rust, we pick whichever CRDT performs best for our graph workload. If we stay in Python, use y-py or loro-py.

---

## Question 2: Why Rust? Is It the Right Endgame Language?

### The Endgame Requirements

1. **Decentralized AI** — agents running on distributed nodes, no central coordinator
2. **Smart contracts** — deterministic, verifiable execution of knowledge graph operations
3. **Custom blockchain** — eventually, a chain where knowledge graph operations are first-class
4. **Dynamic, ever-growing model** — the knowledge network *is* the model, growing without retraining
5. **Multi-agent** — many systems (Open Systems) sharing and building on the same graph
6. **Experience system** — persistent experiential knowledge accumulated over agent lifetimes

### Language Candidates

| Language | Blockchain | Smart Contracts | CRDT | AI/LLM | WASM Target |
|----------|-----------|----------------|------|--------|-------------|
| **Rust** | Solana, NEAR, Polkadot, Cosmos (CosmWASM), Stellar | Native (Solana, CosmWASM, Soroban) | Native (Automerge, Loro, y-crdt) | litellm-rs, rig, rmcp | First-class (`wasm32-unknown-unknown`) |
| **Go** | Ethereum (Geth), Cosmos (Tendermint) | Limited (mostly chain-level) | Some libraries | Limited LLM ecosystem | Partial (TinyGo) |
| **TypeScript** | Limited (scripts, not chains) | Limited | Yjs (native), Automerge (WASM) | Rich LLM ecosystem | Via WASM (AssemblyScript) |
| **Python** | None (too slow for chain infra) | None | Broken/limited bindings | Best LLM ecosystem | No |
| **Solidity** | Ethereum (EVM only) | Native (EVM) | None | None | No |
| **Move** | Aptos, Sui | Native | None | None | No |

### The WASM Angle

This is the most important finding. The endgame isn't "what language do we write the chain in" — it's **"what compiles to the execution target?"**

Modern blockchain VMs are moving to **WebAssembly**:
- CosmWASM (Cosmos ecosystem)
- NEAR (WASM contracts)
- Polkadot/Substrate (WASM runtime)
- SpaceVM (MultiversX, WASM + parallel sharding)
- DTVM (0.95ms JIT, 20x faster than current WASM VMs)

WASM is becoming the universal execution layer for smart contracts AND AI agents. Teams are distributing AI capabilities as portable WASM components that run in browsers, on edge, in cloud, inside MCP servers, on any platform.

**Rust compiles to WASM natively.** This means:
- Knowledge graph operations written in Rust → compile to WASM → run as smart contracts
- Same code runs locally (native Rust) or on-chain (WASM)
- AI agent logic can be a WASM module deployed across a network
- The knowledge network itself could be a set of WASM modules on a CRDT-backed chain

### Why Not Stay in Python?

Python cannot:
- Compile to WASM (not meaningfully)
- Run in a blockchain VM
- Provide deterministic execution for smart contracts
- Match Rust's memory safety guarantees (critical for financial/consensus systems)
- Match Rust's performance at scale (10x latency, 5x memory)

Python's only advantage is **iteration speed** and **LLM ecosystem richness** — but `litellm-rs` and `rig` close the LLM gap, and AI-assisted development closes the iteration speed gap.

### Why Not Go, Move, or Solidity?

- **Go**: Strong for chain infrastructure (Geth, Tendermint) but weak CRDT ecosystem, no WASM smart contracts, limited AI tooling
- **Solidity**: EVM-only, no general-purpose programming, no AI integration
- **Move**: Interesting for asset-oriented programming but tiny ecosystem, no CRDTs, no AI tooling

### The Hybrid Path: Rust Core + WASM Distribution

The architecture that serves all five phases:

```
Phase 1-2: Rust native binary (local agent, MCP server, CRDT storage)
Phase 3:   Same code, distributed via CRDT sync between agents
Phase 4:   TDD workflow artifacts as WASM modules in the graph
Phase 5:   Knowledge graph ops compiled to WASM smart contracts
           → deployed on CosmWASM / custom chain
           → agents as WASM components on the network
```

Rust is the only language that serves as both the local implementation AND the on-chain execution target without rewriting.

### Verdict on Q2

**Rust is the right choice for the endgame.** Not because it's fast (though it is), but because:

1. **WASM target** — same code runs locally and on-chain
2. **CRDT native** — Automerge, Loro, y-crdt are all Rust-first
3. **Blockchain ecosystem** — Solana, CosmWASM, NEAR, Polkadot all use Rust
4. **Memory safety** — required for consensus systems
5. **MCP support** — official SDK (rmcp)
6. **AI tooling** — litellm-rs, rig, agent frameworks maturing rapidly

The risk is iteration speed during early development. Mitigation: AI-assisted development (which we're already doing) largely eliminates this concern.

---

## Recommendation

1. **Build a `GraphStore` abstraction** (interface/trait) that hides CRDT choice
2. **Port to Rust** while the codebase is small (5,830 LOC)
3. **Start with Loro or Automerge** behind the abstraction (evaluate both)
4. **Compile WASM targets** from day one — ensures on-chain portability
5. **Keep Python as a thin MCP client** during transition if needed

## Sources

- [Loro CRDT](https://loro.dev/) / [loro-py](https://github.com/loro-dev/loro-py)
- [y-py (Yjs Python bindings)](https://pypi.org/project/y-py/)
- [Automerge (Rust)](https://crates.io/crates/automerge)
- [Rust in Blockchain & Decentralized Systems (2026)](https://dasroot.net/posts/2026/02/rust-blockchain-decentralized-systems-performance-security/)
- [SpaceVM (WASM + sharding)](https://medium.com/@DBCrypt0/spacevm-the-custom-virtual-machine-that-leaves-evm-in-the-dust-d2fb5f072141)
- [WASM-Powered Interchain AI Smart Contracts](https://arxiv.org/html/2502.17604v1)
- [WasmEdge Runtime](https://github.com/WasmEdge/WasmEdge)
- [WASM Native AI Runtimes](https://medium.com/wasm-radar/the-rise-of-wasm-native-runtimes-for-ai-tools-91b2da07b2ad)
- [CosmWASM](https://docs.terra.money/develop/module-specifications/spec-wasm/)
- [rmcp - Official Rust MCP SDK](https://github.com/modelcontextprotocol/rust-sdk)
