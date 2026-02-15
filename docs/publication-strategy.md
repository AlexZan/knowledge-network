# Publication Strategy

> The whitepapers are the product. The software is the proof.

## Three Papers

| Paper | Topic | Status | Repo |
|-------|-------|--------|------|
| **CCM** | Cognitive Context Management — conclusion-triggered compaction | Whitepaper exists (`docs/whitepaper.md`), proof incomplete | `knowledge-network` |
| **TDD Workflow** | AI-driven TDD pipeline for multi-model development | Data collected, paper not started | `oi/pipeline` |
| **KN** | Knowledge Network — persistent knowledge graph from artifacts | Vision only (`docs/thesis.md`), no implementation | `knowledge-network` |

## What Each Paper Needs to Prove

### CCM: Conclusion-Triggered Compaction

**Core claim**: Open efforts keep full raw context; concluded efforts compact to summaries. Measurable token savings with preserved context quality.

**Proof points needed**:

1. **Token measurement** — run a conversation, show context size drops ~80% when effort concludes
2. **Quality preservation** — show LLM can still answer questions about concluded effort using only the summary (not the raw log)
3. **Comparison** — same conversation through traditional system (full history) vs CCM (compacted). Side-by-side token counts.
4. **Scaling** — show that with N efforts, only open ones cost tokens. Concluded efforts are O(summary) not O(conversation).

**Minimum implementation**: Enough to run the scenario end-to-end and capture numbers. Explicit `/effort` and `/effort close` commands. No auto-detection needed.

### TDD Workflow: Multi-Model AI Development

**Core claim**: A TDD pipeline where AI agents write tests and implementations achieves high pass rates across multiple models, with measurable productivity gains.

**Proof points already collected**:

- Model benchmarks (Opus, GLM, Kimi, deepseek-reasoner) — pass rates and times
- 55/55 test generation across 9 stories
- Unit test vs integration test discovery (all models pass unit tests, most fail integration)
- Partial progress feature for retry loops

**Proof points still needed**:

- End-to-end: from scenario → working software, with metrics at each stage
- Token cost per feature (how many tokens to go from story to passing tests)
- Comparison: manual dev vs pipeline dev for same feature
- Pipeline gap analysis (what the pipeline misses — system prompts, stubs)

### KN: Knowledge Network (Future)

**Core claim**: Compacted artifacts form a knowledge graph where confidence emerges from network topology (support links, failed contradictions, independent convergence).

**Blocked until**: CCM produces artifacts worth persisting.

## Development Priority

1. **CCM Slice 1** — minimum implementation to generate proof data for CCM paper
2. **TDD Workflow paper** — write the paper using data already collected
3. **KN** — starts when CCM artifacts exist

## Related Documents

- [whitepaper.md](whitepaper.md) — CCM whitepaper draft
- [thesis.md](thesis.md) — KN vision and 5 theses
- [slices/01-two-log-proof.md](slices/01-two-log-proof.md) — CCM Slice 1 spec (needs update)
- [brainstorm/slice1-redesign-notes.md](brainstorm/slice1-redesign-notes.md) — Redesign context
