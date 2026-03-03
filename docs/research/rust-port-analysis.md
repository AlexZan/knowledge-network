# Rust Port Analysis (2026-03-03)

## Context

Evaluated whether to port the Knowledge Network from Python to Rust. Initial assessment assumed Rust lacked MCP support, LLM client libraries, and other essentials. Web research proved every assumption wrong.

## Codebase Profile

- **5,830 LOC** across 23 Python modules in `src/oi/`
- **561 tests** (all passing)
- Well-structured: no circular imports (cycles broken by delayed imports), clear module boundaries
- External deps: litellm, pydantic, pyyaml, pypdf, click, mcp (fastmcp)

## Rust Ecosystem Mapping (All Production-Ready)

| Need | Python | Rust | Status |
|------|--------|------|--------|
| MCP server | `fastmcp` | `rmcp` v0.16 (official Anthropic SDK) | Production. `#[tool]` macro, stdio transport. |
| LLM calls | `litellm` | `litellm-rs`, `rig` framework | Active. OpenAI-compatible, multi-provider. |
| CRDT storage | `automerge` 0.1.2 (broken) | `automerge` (native Rust, Automerge 3) | Production. 10x memory reduction in v3. |
| PDF parsing | `pypdf` | `pdf_oxide` (5x faster, Python bindings) | Production. 0.8ms mean extraction. |
| Data models | `pydantic` | `serde` + `garde`/`validator` | Production. Compile-time guarantees. |
| YAML | `pyyaml` | `serde_yaml` / `serde-saphyr` | Production. |
| HTTP/embeddings | `requests` → Ollama | `reqwest` → Ollama | Trivial. Same HTTP API. |
| Agent framework | — | `rig`, `agentai`, `AutoAgents` | Active. Tool calling, function calling. |
| Token counting | `tiktoken` (Rust via PyO3) | `tiktoken-rs` (native) | Production. Already Rust under the hood. |

## Performance Expectations

From 2026 AI Agent Benchmark data:
- 5x lower memory usage vs Python agent frameworks
- 10x latency improvement for 99th percentile operations
- MCP: 16x speed, 50x memory reduction vs TypeScript (pmcp crate)

## Hot Paths That Benefit from Rust

| Operation | Current (Python) | Rust Speedup | Notes |
|-----------|-----------------|-------------|-------|
| Embedding search (cosine similarity) | Linear scan | 10-50x | SIMD, rayon parallel |
| Graph walk (BFS + scoring) | Dict lookups | 5-20x | CSR graph, cache-friendly |
| Candidate search (keyword matching) | Set intersection | 3-10x | Bitmask operations |
| Conflict detection | Edge scanning | 2-5x | Pre-indexed adjacency |
| Document parsing | Regex + split | 2-10x | pdf_oxide already 5x faster |

## What Rust Wouldn't Speed Up

- LLM inference (network-bound, same HTTP calls regardless of language)
- File I/O (disk-bound)
- MCP transport (stdio JSON-RPC, negligible overhead)

## Key Insight: Automerge

The strongest argument for Rust isn't speed — it's **Automerge**. The Python bindings (v0.1.2) are broken (low-level, no fork/merge, can't build from git on NixOS). The Rust crate is the native implementation with full CRDT support. Porting to Rust gives us real concurrent storage *for free*.

## Refactoring Debt (Current Python)

- 7 god functions >100 lines
- 32 delayed imports (masking 2 circular dependency cycles)
- 8 modules without direct unit tests
- `tools.py` is 1,067 lines (god module)
- No state caching (reloads full graph every operation)
- 2 missing deps in pyproject.toml (tiktoken, requests)
- ~50% of functions missing type hints

## Sources

- [rmcp - Official Rust MCP SDK](https://github.com/modelcontextprotocol/rust-sdk)
- [litellm-rs](https://crates.io/crates/litellm-rs)
- [Rig - Rust LLM framework](https://rig.rs/)
- [Automerge (Rust native)](https://crates.io/crates/automerge)
- [pdf_oxide](https://crates.io/crates/pdf_oxide)
- [Why Rust Is Winning for AI Tooling in 2026](https://dasroot.net/posts/2026/02/why-rust-winning-ai-tooling-2026/)
- [mcpkit - macro MCP server](https://github.com/praxiomlabs/mcpkit)
