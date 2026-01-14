# Human Context Management

The human has a context limit too. We've focused on AI context, but the user needs help managing their cognitive load.

---

## The Problem

Just in one brainstorming session, we created:
- 3+ new documents
- Multiple edits to existing docs
- Decisions scattered across files
- Relationships between artifacts that aren't explicit

**Result**: User says "I have lost track of them, it's hard to access them, I often forget what we created"

The AI assistant remembers everything (until context limit). The human doesn't.

---

## What Humans Need

### 1. Artifact Inventory
"What have we created?"
- List of all artifacts from this chat/effort
- Grouped by type (brainstorm, scenario, decision, code, etc.)
- Timestamps (when created, last modified)

### 2. Relationship Map
"How do these connect?"
- Which artifacts reference which
- Parent/child relationships (effort hierarchy)
- Project associations
- Topic clustering

### 3. Context Reinforcement
"Why did we create this?"
- Brief reminder of the decision/discussion that led to artifact
- Link back to chat log moment
- Tags/keywords for quick scanning

### 4. Easy Navigation
"How do I find X?"
- Search across artifacts
- Filter by type, project, date, effort
- Recent artifacts prominently displayed
- Favorites/pinned artifacts

### 5. Progress Visibility
"What's the state of things?"
- Open efforts and their status
- Completed efforts and outcomes
- Blockers/open questions
- What's next

---

## Interface Ideas

### Session Summary View
After each session (or on demand), show:
```
SESSION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Created:
  📄 effort-scoped-context.md (brainstorm)
     Core model: lazy compaction, effort weight, focus constraint

  📄 director-agent-scenario.md (scenario)
     Future vision: 24/7 director with workers

  📄 TODO.md (tracking)
     8 open design threads

Modified:
  📝 1a-minimal.md - updated terminology
  📝 pipeline.md - added naming convention

Decisions Made:
  ✓ Constraint tied to effort weight (high=locked, low=flexible)
  ✓ Effort types have default weights
  ✓ User can override with /lock, /unlock

Open Questions:
  ? How to detect effort type reliably
  ? Child effort mechanics
  ? Fork mechanics
```

### Artifact Dashboard
```
┌─────────────────────────────────────────────────────────────┐
│ KNOWLEDGE NETWORK - Artifact Dashboard                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ RECENT                          PROJECTS                    │
│ ├─ effort-scoped-context.md     ├─ knowledge-network/       │
│ ├─ director-scenario.md         │   └─ 28 artifacts         │
│ └─ TODO.md                      └─ open-colony/             │
│                                     └─ 45 artifacts         │
│ BY TYPE                                                     │
│ ├─ Brainstorms (7)              OPEN EFFORTS                │
│ ├─ Scenarios (3)                ├─ Slice 1 redesign         │
│ ├─ Decisions (7)                ├─ Child effort design      │
│ ├─ Slices (5)                   └─ Human interface design   │
│ └─ Stories (2)                                              │
│                                                             │
│ [Search artifacts...]                                       │
└─────────────────────────────────────────────────────────────┘
```

### Relationship Graph
Visual map showing:
- Artifacts as nodes
- Links as edges (references, parent/child)
- Clusters by topic/project
- Highlight current effort's artifacts

---

## Integration with Effort Model

The artifact view ties directly to efforts:

```
EFFORT: Design effort-scoped context model
├─ ARTIFACTS CREATED
│   ├─ effort-scoped-context.md (core doc)
│   ├─ director-agent-scenario.md (future vision)
│   └─ TODO.md (tracking)
│
├─ DECISIONS MADE
│   ├─ Lazy compaction (compact late, not early)
│   ├─ Effort weight controls cost/quality
│   └─ Focus constraint tied to weight
│
├─ OPEN QUESTIONS
│   ├─ Child effort mechanics
│   └─ Fork mechanics
│
└─ RELATED EFFORTS
    ├─ Slice 1 design (depends on this)
    └─ TDD pipeline exploration (informed this)
```

When an effort resolves, this becomes the artifact - not just a text summary, but a **structured record** of what was produced.

---

## Key Insight

The system should help **both** AI and human manage context:

| AI Context | Human Context |
|------------|---------------|
| Token limit | Cognitive limit |
| Compaction | Summarization |
| RAG retrieval | Search/filter |
| Effort focus | Dashboard/inventory |
| Artifact storage | Easy navigation |

**Same problem, different interfaces.**

---

## For Slice Roadmap

This suggests a slice focused on human interface:

**Slice N: Human Context Dashboard**
- Session summary generation
- Artifact inventory view
- Relationship visualization
- Search/filter capabilities
- Effort-artifact linking

Could be a TUI (terminal UI) for CLI, or web dashboard, or both.

---

---

## Visualization Layer (Future)

Humans are visual interpreters. Text lists aren't enough.

**Primitives** (data model):
- Artifacts with metadata
- Relationships (links, parent/child)
- Efforts with status
- Tags, timestamps, projects

**Views** (built on primitives):

| View Type | Use Case |
|-----------|----------|
| **Graph** | Relationship map - nodes and edges |
| **Tree** | Hierarchy - effort/child structure |
| **Timeline** | Chronological - when things happened |
| **Kanban** | Status flow - open/in-progress/done |
| **3D Map** | Spatial clustering - topic neighborhoods |
| **Flow chart** | Process - how work moves through pipeline |

**Custom views**: Users build their own views on the primitives. Like SQL views but visual.

```
PRIMITIVES (data)          VIEWS (visual)
─────────────────          ──────────────
artifacts      ──────────► graph view
relationships  ──────────► tree view
efforts        ──────────► kanban view
metadata       ──────────► custom view
```

**Later slices** - not slice 1, but foundational thinking.

---

## Open Questions

- [ ] TUI vs web dashboard vs both?
- [ ] How to auto-generate session summaries?
- [ ] How to track artifact relationships automatically?
- [ ] Integration with existing tools (Obsidian, Notion, etc.)?
- [ ] Real-time updates vs on-demand refresh?
- [ ] What visualization library/framework?
- [ ] 3D mapping - Three.js? WebGL?
