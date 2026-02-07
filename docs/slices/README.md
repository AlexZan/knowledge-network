# Implementation Slices: Dev-First Roadmap

Progressive implementation targeting development/documentation/brainstorming workflows.

See [Decision 008](../decisions/008-dev-first-pivot.md) for why we pivoted from generic AI to dev-first.

---

## Philosophy

**Primitives are the product. Dev is the first application.**

We build the core primitives (efforts, artifacts, two-log, capture) while targeting a specific use case (TDD dev pipeline). The primitives generalize; the application is configuration.

```
PRIMITIVES (this roadmap)     →    APPLICATIONS (configurations)
───────────────────────────────    ────────────────────────────
Two-log, capture, artifacts   →    coding/ (TDD pipeline)
Kanban, peer agents           →    research/ (future)
Escalation, disputes          →    writing/ (future)
Context building, RAG         →    generic/ (future)
```

---

## Slice Overview

| Slice | Name | Core Feature | Target |
|-------|------|--------------|--------|
| 1 | Core Capture | Two-log model, continuous capture, manifest | Foundation |
| 2 | Dev Artifacts | Story, spec, test contract types | Dev workflow |
| 3 | Progress Visibility | Past/present/future, session state | Human UX |
| 4 | Effort Weight | Context budget, compaction threshold | Cost control |
| 5 | Kanban Integration | Columns, claims, flow, item state | Pipeline |
| 6 | Peer Agents | Stateless agents, kanban-triggered | Automation |
| 7 | Disputes & Escalation | Comments, backflow, model ladder | Robustness |
| 8 | RAG Retrieval | Cross-artifact context, merge suggestions | Knowledge reuse |
| 9 | TDD Pipeline | Full story→test→dev→QA flow | First application |
| 10 | Human Dashboard | Artifact inventory, visual mapping | Human context |

---

## Dependencies

```
Slice 1 (core capture - foundation)
    ↓
Slice 2 (dev artifacts - what we capture)
    ↓
Slice 3 (progress visibility - human UX)
    ↓
Slice 4 (effort weight - cost control)
    ↓
Slice 5 (kanban - pipeline infrastructure)
    ↓
Slice 6 (peer agents - automation)
    ↓
Slice 7 (disputes/escalation - robustness)
    ↓
Slice 8 (RAG - knowledge reuse)
    ↓
Slice 9 (TDD pipeline - first full application)
    ↓
Slice 10 (dashboard - human context management)
```

---

## Slice Details

### Slice 1: Core Capture

**Goal**: Foundation for all capture and context.

**Features**:
- Two-log model (raw.jsonl + manifest.yaml)
- Continuous capture (summarize every response)
- Segment detection (greeting, effort, calculation, etc.)
- Artifact creation on conclusion
- Manifest always current

**Success criteria**:
- [ ] Raw log appends every turn
- [ ] Manifest updates with segment summaries
- [ ] Artifacts created on conclusion detection
- [ ] Manifest links to artifacts and raw log sections
- [ ] Can rebuild context from manifest alone

---

### Slice 2: Dev Artifacts

**Goal**: Artifact types for development workflow.

**Features**:
- Story artifact (user story with acceptance criteria)
- Spec artifact (technical specification)
- Test contract artifact (test definitions)
- Architecture artifact (design decisions)
- Implementation artifact (code summary)

**Success criteria**:
- [ ] Each artifact type has defined schema
- [ ] Artifacts link to each other (story → spec → test)
- [ ] Artifacts have status (draft, approved, implemented)
- [ ] Can query artifacts by type

---

### Slice 3: Progress Visibility

**Goal**: Human always knows where they are.

**Features**:
- Session state display (past/present/future)
- Concluded efforts with checkmarks
- Current effort highlighted
- Suggested next steps
- Token stats visible

**Success criteria**:
- [ ] Session shows concluded efforts
- [ ] Current effort clearly indicated
- [ ] Suggested next visible (if known)
- [ ] Progress feels like "save points"

---

### Slice 4: Effort Weight

**Goal**: One dial controls cost/quality tradeoff.

**Features**:
- Weight setting (low/medium/high)
- Weight → context budget mapping
- Weight → compaction threshold
- Weight → focus constraint (locked/flexible)
- Weight → starting model tier
- Default weights by effort type

**Success criteria**:
- [ ] `/weight` command works
- [ ] Low weight = cheap, aggressive compaction
- [ ] High weight = quality, lazy compaction
- [ ] Weight persists in effort metadata

---

### Slice 5: Kanban Integration

**Goal**: Pipeline infrastructure for agent flow.

**Features**:
- Column definitions (ready, in-progress, blocked, done)
- Item state (status, failure_count, escalation_tier)
- Claim/release mechanics
- Column watchers
- Backflow for blockers

**Success criteria**:
- [ ] Items can be created/moved between columns
- [ ] Items track failure_count
- [ ] Claims prevent double-processing
- [ ] Blocked items can flow backward

---

### Slice 6: Peer Agents

**Goal**: Stateless agents triggered by kanban.

**Features**:
- Agent watches specific column
- Agent claims item, does work, releases
- Agent reads failure_count, selects model
- Agent produces artifact, updates item
- Agent dies after completion (stateless)

**Success criteria**:
- [ ] Agent triggered by column change
- [ ] Agent configures model from failure_count
- [ ] Agent produces artifact on completion
- [ ] Agent is stateless (no persistent memory)

---

### Slice 7: Disputes & Escalation

**Goal**: Robustness when things go wrong.

**Features**:
- Artifact comments (threaded)
- Dispute via comment + backflow
- Circuit breaker (N rounds → human)
- Model ladder escalation
- Specialist columns (future)

**Success criteria**:
- [ ] Agents can comment on artifacts
- [ ] Disputes trigger backflow
- [ ] Escalation increases model tier
- [ ] After N failures, human notified

---

### Slice 8: RAG Retrieval

**Goal**: Cross-artifact context building.

**Features**:
- Embed artifacts on creation
- Search artifacts by similarity
- Suggest related artifacts
- Merge suggestions for convergent chats
- Context building from multiple sources

**Success criteria**:
- [ ] Artifacts embedded in vector store
- [ ] RAG retrieval works in context building
- [ ] Related artifacts suggested
- [ ] Merge command works

---

### Slice 9: TDD Pipeline

**Goal**: Full development workflow.

**Features**:
- Story agent (idea → user story)
- Architect agent (story → design)
- Test-architect agent (story → failing tests)
- Dev agent (tests → implementation)
- QA agent (implementation → verification)
- Full flow from idea to merged code

**Success criteria**:
- [ ] Pipeline flows from idea to done
- [ ] Each stage produces correct artifact
- [ ] Failures escalate appropriately
- [ ] Human gates at key points

---

### Slice 10: Human Dashboard

**Goal**: Help humans manage cognitive load.

**Features**:
- Artifact inventory view
- Session map generation
- Relationship visualization
- Search/filter
- Progress overview

**Success criteria**:
- [ ] Can see all artifacts
- [ ] Can see session summary
- [ ] Can search artifacts
- [ ] Relationships visible

---

## Future Slices (Post Dev-First)

These come after the dev pipeline is working:

| Slice | Name | From Original Thesis |
|-------|------|---------------------|
| 11 | Knowledge Graph | Cross-session connections |
| 12 | Abstraction Layers | Privacy gradient, generalization |
| 13 | Conflict Resolution | Handle contradictions |
| 14 | Emergent Confidence | Topology-based scoring |
| 15 | Generic Applications | Research, writing, etc. |

---

## Design Principles

1. **Dev-first, generalize later** - Concrete use case teaches us what primitives need
2. **Each slice is independently valuable** - Not just scaffolding
3. **Primitives over features** - Build composable blocks
4. **Human perspective matters** - Progress visibility, cognitive relief
5. **Stateless by default** - Agents die, items persist
6. **Continuous capture** - Never lose knowledge
