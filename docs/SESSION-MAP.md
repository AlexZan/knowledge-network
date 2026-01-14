# Session Map: Effort-Scoped Context Design

Quick reference for artifacts created/modified during this design session.

---

## Artifacts Created

| File | Type | One-liner |
|------|------|-----------|
| [effort-scoped-context.md](brainstorm/effort-scoped-context.md) | Brainstorm | **Core model**: lazy compaction, effort weight, focus constraint, escalation |
| [director-agent-scenario.md](scenarios/director-agent-scenario.md) | Scenario | Future vision: 24/7 director spawning workers |
| [human-context-management.md](brainstorm/human-context-management.md) | Brainstorm | Human needs artifact dashboard, visual mapping |
| [TODO.md](TODO.md) | Tracking | 10 open design threads with links |
| SESSION-MAP.md | Meta | This file - session overview |

## Artifacts Updated

| File | Type | Changes |
|------|------|---------|
| [tech-stack.md](tech-stack.md) | Decision | Full rewrite: philosophy, layers, hackable primitives, examples |

---

## Key Decisions Made

### Architecture
1. **Python** for CLI/tools - hackable, AI ecosystem native
2. **Anti-monolith** - small composable pieces, everything is files
3. **Hackable primitives** - users modify tools, instructions, schemas directly

### Context Model
4. **Lazy compaction** - stay large as long as possible, compact at meaningful boundaries
5. **Effort weight** - quality/cost dial (high=max context, low=cheap)
6. **Focus constraint tied to weight** - high=locked, low=flexible
7. **One chat = one effort** - constraint as feature, not limitation

### Cost Management
8. **Model escalation** - start free/cheap, escalate after 2 failures
9. **Effort weight influences starting tier** - critical starts at Sonnet/Opus

### Human Interface
10. **Human has context limit too** - needs dashboard, artifact inventory
11. **Visual mapping** - graphs, trees, timelines built on primitives (future)

---

## Mental Model

```
┌─────────────────────────────────────────────────────────────┐
│                    EFFORT-SCOPED CONTEXT                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  EFFORT WEIGHT ──► CONTEXT BUDGET ──► COMPACTION THRESHOLD  │
│       │                                                     │
│       ├──────────► FOCUS CONSTRAINT (locked/flexible)       │
│       │                                                     │
│       └──────────► MODEL TIER (free/standard/expensive)     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PRIMITIVES (Python)              VIEWS (Future)            │
│  ─────────────────────            ──────────────            │
│  artifacts, schemas    ─────────► graph, tree, kanban       │
│  relationships         ─────────► timeline, 3D map          │
│  tools, instructions   ─────────► custom views              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HACKABLE LOCATIONS (~/.oi/)                                │
│                                                             │
│  instructions/*.md    ─── just edit text                    │
│  tools/*.py           ─── drop in functions                 │
│  schemas/*.py         ─── Pydantic models                   │
│  config.yaml          ─── settings                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Open Threads (from TODO.md)

| # | Thread | Status | Priority |
|---|--------|--------|----------|
| 1 | Child efforts design | Open | High |
| 2 | Chat log format | Open | High |
| 3 | Slice 1 redesign | Open | High |
| 4 | Fork mechanics | Open | Medium |
| 5 | Vector filtering | Open | Medium |
| 6 | AI chat retrieval | Open | Medium |
| 7 | Agents revisited | Open | Lower |
| 8 | Effort weight inference | Partial | Lower |
| 9 | Human context dashboard | Open | Medium |
| 10 | Model escalation | Captured | Lower |

---

## Slice Progression (Proposed)

| Slice | Focus | Builds Toward |
|-------|-------|---------------|
| **1** | Single effort lifecycle | Worker agents |
| **2** | Effort weight | Cost control |
| **3** | Focus constraint + topic detection | Clean boundaries |
| **4** | Context building with artifacts | Director context |
| **5** | Child efforts | Sub-task orchestration |
| **6** | RAG retrieval | On-demand details |
| **7** | Spawn/return pattern | Worker model |
| **8** | Director orchestration | Full scenario |

---

## Tech Stack Summary

```
Python 3.11+ (core)
├── litellm      (LLM calls, any provider)
├── typer        (CLI)
├── pydantic     (schemas)
├── chromadb     (vectors)
├── sentence-transformers (embeddings)
└── rich         (terminal UI)

Future: TypeScript/React (dashboard), Rust (hot paths)
```

---

## Related Docs

| Doc | Relevance |
|-----|-----------|
| [refined-chat-model.md](brainstorm/refined-chat-model.md) | Earlier chat model thinking |
| [thesis.md](thesis.md) | Original vision (5 theses) |
| [1a-minimal.md](slices/1a-minimal.md) | Slice 1 spec (needs revision) |
| [pipeline.md](pipeline.md) | TDD pipeline structure |
| [PROJECT.md](PROJECT.md) | Technical architecture |
