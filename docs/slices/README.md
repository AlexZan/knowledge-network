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

**Phase boundary**: Slices 1-7 are a memory system with agent capabilities. Slices 8a-8d add the knowledge graph with topology-based confidence. Slices 8e-8f make the graph usable and traceable at runtime. Slice 8g adds generalization — the system detects patterns and distills principles.

---

## Architectural Decisions

- [Decision 010: ONE CHAT](../decisions/010-one-chat-no-projects.md) — No projects, no sessions to manage. One global knowledge space.
- [Decision 011: Efforts Are KG Nodes](../decisions/011-efforts-are-kg-nodes.md) — Everything is a node. Efforts are one node type with a rich lifecycle.
- [Decision 012: Sessions as Audit Logs](../decisions/012-session-as-audit-log.md) — Sessions are chronological records of graph interactions + ambient conversation, not persistence boundaries.
- [Decision 013: Unified KG Architecture](../decisions/013-unified-kg-architecture.md) — Mutability gradient, Automerge/Vault storage layer, reactive `because_of` edges. Validated via 7 architectural traces.
- [Decision 014: Sessions as Perspectives](../decisions/014-sessions-as-perspectives.md) — Sessions develop distinct viewpoints. Enables multi-agent debate, roundtables, adversarial review.

---

## Next

Each remaining slice delivers a distinct, noticeable user experience. Scenarios map to slices — see [08-knowledge-graph-scenarios.md](08-knowledge-graph-scenarios.md) for the full narrative walkthroughs.

### Slices

| Slice | Name | Scenario | What the user experiences |
|-------|------|----------|--------------------------|
| ~~8e~~ | ~~The Agent Remembers~~ | ~~2, 4~~ | ~~Done — see Completed table above~~ |
| ~~8f~~ | ~~Traceable Knowledge~~ | ~~—~~ | ~~Done — see Completed table above~~ |
| ~~8g~~ | ~~The Agent Generalizes~~ | ~~3~~ | ~~Done — see Completed table above~~ |
| 8h | Reactive Knowledge | — | `because_of` edges express dependency. Stale justifications detected at query time and surfaced conversationally. |

Scenario 1 (First Nodes) is already delivered by 8a+8b. Scenario 5 (Accumulated Expertise) is the emergent result of 8e+8g working together over time — not a separate slice.

### 8h: Reactive Knowledge

When a preference or decision depends on a fact (`because_of` edge), and that fact is later superseded or contested, the system detects the stale justification and asks the user if the dependent knowledge still holds.

**Spec**: [08h-because-of-staleness.md](08h-because-of-staleness.md)

**What's built:**
- `because_of` edge type — "this node's validity depends on that node being true"
- Staleness detection — `query_knowledge` checks 1-hop `because_of` targets for superseded/contested status
- Confidence cap — nodes with stale deps never report higher than "medium" confidence
- System prompt guidance — LLM surfaces staleness naturally in conversation

**Origin**: [Decision 013](../decisions/013-unified-kg-architecture.md), Trace 6 (deep `because_of` chain).

### Deferred: Unified Graph Store

Effort migration (efforts as knowledge graph nodes) and schema system. Deferred until there's a concrete need to query efforts and knowledge together. Current dual storage (manifest.yaml + knowledge.yaml) works fine.

### Dependencies

```
8e: The Agent Remembers (query, eviction, resolution, session logs)
 ↓
8f: Traceable Knowledge (session log linking, expand_knowledge) ✓
 ↓
8g: The Agent Generalizes (principles, abstraction, privacy) ✓
 ↓
8h: Reactive Knowledge (because_of edges, staleness detection)
```

8e provides the query/eviction infrastructure that 8f's unified graph needs. 8f provides the "any node is expandable" architecture that makes 8g's principle nodes first-class citizens. 8g provides the pattern detection that 8h's reactive edges build on — principles depend on their exemplifying facts, so staleness detection matters most for high-abstraction nodes.

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
- [Thesis](../thesis.md) — Knowledge Network vision (Theses 2-5, hybrid endgame)
- [Technical Reference](../PROJECT.md) — Architecture (needs update)
- [Scenarios](08-knowledge-graph-scenarios.md) — Slice 8 UX walkthroughs
