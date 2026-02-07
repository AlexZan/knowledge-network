# Session Map: Effort-Scoped Context Design

Quick reference for artifacts created/modified during this design session.

---

## Artifacts Created

| File | Type | One-liner |
|------|------|-----------|
| [effort-scoped-context.md](brainstorm/effort-scoped-context.md) | Brainstorm | **Core model**: lazy compaction, effort weight, focus constraint, escalation |
| [director-agent-scenario.md](scenarios/director-agent-scenario.md) | Scenario | Director model: 24/7 orchestrator spawning workers |
| [peer-agent-scenario.md](scenarios/peer-agent-scenario.md) | Scenario | **Peer model**: stateless agents, kanban as coordinator |
| [agent-communication.md](brainstorm/agent-communication.md) | Brainstorm | Disputes, escalation, stateless coordination |
| [human-context-management.md](brainstorm/human-context-management.md) | Brainstorm | Human needs artifact dashboard, visual mapping |
| [context-and-cognition.md](brainstorm/context-and-cognition.md) | Brainstorm | Two-log model, context strategies, human cognitive needs, continuous capture |
| [008-dev-first-pivot.md](decisions/008-dev-first-pivot.md) | Decision | **Pivot**: Generic AI → Dev-first roadmap |
| [TODO.md](TODO.md) | Tracking | 10 open design threads with links |
| SESSION-MAP.md | Meta | This file - session overview |

## Artifacts Updated

| File | Type | Changes |
|------|------|---------|
| [tech-stack.md](tech-stack.md) | Decision | Full rewrite: philosophy, layers, hackable primitives, applications |
| [thesis.md](thesis.md) | Vision | Added "Primitives and Applications" framing section |

---

## Key Decisions Made

### Architecture
1. **Python** for CLI/tools - hackable, AI ecosystem native
2. **Anti-monolith** - small composable pieces, everything is files
3. **Hackable primitives** - users modify tools, instructions, schemas directly
4. **Primitives vs Applications** - primitives are the product, applications are configurations

### Context Model
5. **Lazy compaction** - stay large as long as possible, compact at meaningful boundaries
6. **Effort weight** - quality/cost dial (high=max context, low=cheap)
7. **Focus constraint tied to weight** - high=locked, low=flexible
8. **One chat = one effort** - constraint as feature, not limitation

### Agent Coordination
9. **Peer model over director** - stateless agents, kanban as coordinator
10. **Disputes via comments** - artifact comments + kanban backflow
11. **Stateless escalation** - failure_count in item metadata + model ladder
12. **No process dependencies** - agent dies after each attempt, item persists

### Cost Management
13. **Model escalation** - start free/cheap, escalate after 2 failures
14. **Effort weight influences starting tier** - critical starts at Sonnet/Opus
15. **Configurable model ladder** - per-agent-type escalation rules

### Human Interface
16. **Human has context limit too** - needs dashboard, artifact inventory
17. **Visual mapping** - graphs, trees, timelines built on primitives (future)

### Context & Storage
18. **Two-log model** - raw log (verbatim) + summary log (manifest with artifact refs)
19. **Chats compact to artifact refs** - artifacts are primary, chats are process
20. **Context strategies** - chat-only, RAG-only, or hybrid based on use case
21. **Effort weight controls context budget** - one dial for budget, compaction, focus, model

### Human Cognition
22. **Conclusion as cognitive relief** - closed loops release mental resources
23. **Temporal grounding** - always show past/present/future state
24. **Progress visibility** - artifacts are progress bar for knowledge work
25. **Continuous capture** - summarize every response, don't wait for end-of-session

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
│  PEER AGENT MODEL                                           │
│  ─────────────────                                          │
│                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│  │  story  │───►│  arch   │───►│  dev    │───► ...         │
│  │  agent  │    │  agent  │    │  agent  │                 │
│  └─────────┘    └─────────┘    └─────────┘                 │
│       │              │              │                       │
│       ▼              ▼              ▼                       │
│   watches        watches        watches                     │
│   column         column         column                      │
│                                                             │
│  • Stateless agents (die after each effort)                │
│  • Kanban is the coordinator                                │
│  • Artifacts are the only communication                     │
│  • failure_count in item → model selection                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HACKABLE LOCATIONS (~/.oi/)                                │
│                                                             │
│  instructions/*.md    ─── just edit text                    │
│  tools/*.py           ─── drop in functions                 │
│  schemas/*.py         ─── Pydantic models                   │
│  config.yaml          ─── settings                          │
│  applications/        ─── domain configurations             │
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
