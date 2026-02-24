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

**Phase boundary**: Slices 1-7 are a memory system with agent capabilities. Slices 8a-8d add the knowledge graph with topology-based confidence. Slice 8e makes the graph usable at runtime.

---

## Architectural Decisions

- [Decision 010: ONE CHAT](../decisions/010-one-chat-no-projects.md) — No projects, no sessions to manage. One global knowledge space.
- [Decision 011: Efforts Are KG Nodes](../decisions/011-efforts-are-kg-nodes.md) — Everything is a node. Efforts are one node type with a rich lifecycle.
- [Decision 012: Sessions as Audit Logs](../decisions/012-session-as-audit-log.md) — Sessions are chronological records of graph interactions + ambient conversation, not persistence boundaries.

---

## Next

Each remaining slice delivers a distinct, noticeable user experience. Scenarios map to slices — see [08-knowledge-graph-scenarios.md](08-knowledge-graph-scenarios.md) for the full narrative walkthroughs.

### Slices

| Slice | Name | Scenario | What the user experiences |
|-------|------|----------|--------------------------|
| ~~8e~~ | ~~The Agent Remembers~~ | ~~2, 4~~ | ~~Done — see Completed table above~~ |
| 8f | Everything is a Node | — | Any knowledge node expandable to its source conversation. Efforts migrate to graph store. Schema system for node types. |
| 8g | The Agent Generalizes | 3 | Patterns detected across efforts. Principles distilled automatically. Privacy gradient separates private details from shareable insights. |

Scenario 1 (First Nodes) is already delivered by 8a+8b. Scenario 5 (Accumulated Expertise) is the emergent result of 8e+8g working together over time — not a separate slice.

### 8e: The Agent Remembers

The agent uses its accumulated knowledge proactively, catches its own contradictions, and the full reasoning trail is preserved.

**What's built:**
- `query_knowledge` — internal function + user-facing tool for searching the graph
- Knowledge node eviction from system prompt — same pattern as effort eviction (Slice 4). As the graph grows, old/low-confidence nodes drop from the prompt but remain queryable.
- Interactive contradiction resolution — when contradictions are detected (8c), the agent presents both sides conversationally ("I need to flag something..."), suggests a resolution, and asks for user input. Superseded nodes are marked but preserved.
- Session audit logs ([Decision 012](../decisions/012-session-as-audit-log.md)) — each session is a chronological record of node creates, references, and ambient conversation. Traceable later.

**Scenario 2 UX**: "I need to design the auth flow for mobile..." → agent responds with standard advice plus "One thing to watch out for: I've seen auth state go stale on reused connections before..." — past experience woven in naturally, not as a raw node dump.

**Scenario 4 UX**: "Profiling shows we should validate once at entry..." → "I need to flag something: this conflicts with advice I've been applying elsewhere..." → conversational resolution flow.

### 8f: Everything is a Node

Realizes [Decision 011](../decisions/011-efforts-are-kg-nodes.md). The knowledge graph becomes the single storage layer. Any piece of knowledge can be traced to its source conversation.

**What's built:**
- Schema system — YAML type definitions per node type (fields, lifecycle, context behavior)
- Effort migration — efforts stored as graph nodes instead of separate manifest. Existing effort tools unchanged (interface stays, storage moves).
- Session log linking — knowledge nodes link back to the session log fragment where they were created. Combined with generic expand, any node is traceable.
- Generic expand/collapse — `expand_effort` generalized to work for any node type. "Show me the conversation where we decided X" works for decisions, facts, anything.

### 8g: The Agent Generalizes

The agent notices patterns across efforts and distills them into reusable principles, naturally separated by privacy level.

**What's built:**
- `principle` node type — auto-generated when enough instances converge
- Pattern detection — agent notices when multiple independent efforts resolve to the same underlying insight
- Abstraction layers — Layer 0 (raw/private) → Layer 1 (contextual) → Layer 2 (general/shareable) → Layer 3 (universal). Higher layers strip identifying details automatically.
- Privacy gradient — specific details stay private, generalized principles are shareable without manual privacy management

**Scenario 3 UX**: "Found it. The credential is validated at batch start but not at record processing time..." → "I'm noticing a pattern: this is the third time I've seen auth state go stale between validation and use..." → generalization surfaces naturally.

### Dependencies

```
8e: The Agent Remembers (query, eviction, resolution, session logs)
 ↓
8f: Everything is a Node (schema, migration, generic expand)
 ↓
8g: The Agent Generalizes (principles, abstraction, privacy)
```

8e provides the query/eviction infrastructure that 8f's unified graph needs. 8f provides the "any node is expandable" architecture that makes 8g's principle nodes first-class citizens.

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
