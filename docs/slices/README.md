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

**Phase boundary**: Slices 1-7 are a memory system with agent capabilities. Slice 8 builds the knowledge graph — the core vision.

---

## Architectural Decisions for Slice 8

- [Decision 010: ONE CHAT](../decisions/010-one-chat-no-projects.md) — No projects, no sessions. One global knowledge space. User launches `oi` and talks.
- [Decision 011: Efforts Are KG Nodes](../decisions/011-efforts-are-kg-nodes.md) — Everything is a node in the knowledge graph. Efforts are one node type. Every node has a summary (in context) and raw log (expandable). Schema + tools + instructions per type.

---

## Next: Slice 8 — Knowledge Graph

The knowledge graph is the single persistent layer. Every node has a summary (compacted knowledge in context) and a raw log (source conversation, expandable on demand). This is CCM generalized beyond efforts.

Ordered to prove the thesis early: 8a builds the foundation, 8b proves confidence and conflict resolution work before investing in convenience features.

### Sub-slices

| Slice | Name | Thesis | What it does |
|-------|------|--------|-------------|
| 8a | Graph Foundation | 2 | ONE CHAT CLI. Common node base (summary + raw log). Graph store. `fact` node type. `add_knowledge` tool. Basic edges (support, contradiction). |
| 8b | Conflict + Confidence | 4, 5 | Contradiction detection. Truth vs preference classification. Confidence from topology (inbound support, failed contradictions, independent convergence). |
| 8c | Schema System + Types | 2 | YAML schema definitions. Effort migration to graph store. `preference`, `decision` node types. `query_knowledge` tool. Generic expand/collapse for all types. |
| 8d | Abstraction + Privacy | 3 | `principle` node type. Auto-generalization from multiple related nodes. Privacy gradient (raw → contextual → principle → universal). Schema-detection agent. |

### Dependencies

```
8a: Graph Foundation (nodes + edges)
 ↓
8b: Conflict + Confidence (proves the thesis)
 ↓
8c: Schema System + Types (convenience, more node types)
 ↓
8d: Abstraction + Privacy (highest-level knowledge)
```

### Scenarios

See [08-knowledge-graph-scenarios.md](08-knowledge-graph-scenarios.md) — narrative walkthroughs of the full Slice 8 user experience. Written before the 010/011 architectural decisions; will be updated per sub-slice.

---

## Future

### Slice 9: Workflow Integration

Workflows (like TDD pipeline) become tools the system can invoke.

- oi-pipe as a subsystem, not a separate project
- Workflow orchestration through tool calls
- Reassess priority after Slice 8

---

## Icebox

Capabilities that may be valuable but aren't blocking the core vision. Revisit as needed.

- **RAG / document ingestion** — Ingest external documents into knowledge graph
- **Web search tool** — Dedicated web search beyond `run_command` + `curl`
- **Codebase search tool** — Structured grep/find with semantic output
- **Tool error recovery** — Retry logic, better error classification
- **Model ladder** — Escalation from cheap → expensive models per task
- **Dashboard** — Visual entry point to the knowledge graph (brainstorm: `docs/brainstorm/sessions-and-dashboard.md`)
- **Schema-detection agent** — Auto-propose new node types from conversation patterns (could move earlier)

---

## Related Documents

- [CCM Whitepaper](../ccm-whitepaper.md) — Published (Slices 1-4)
- [Thesis](../thesis.md) — Knowledge Network vision (Theses 2-5)
- [Technical Reference](../PROJECT.md) — Architecture (needs update)
- [Scenarios](08-knowledge-graph-scenarios.md) — Slice 8 UX walkthroughs
