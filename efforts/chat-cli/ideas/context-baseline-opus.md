# Scenario Context: Core Capture (Slice 1)

## Scope Summary

Foundation for capturing knowledge from conversations and pipelines. Two capture patterns:

1. **Pipeline Capture** - Agent pipelines that produce work products via artifact status
2. **Chat Capture** - User-AI conversations using the two-log model

Both produce **artifacts** as their primary output. Artifacts are the portable knowledge.

## Out of Scope (Do Not Include)

These features are explicitly deferred to later slices - scenarios should NOT include them:

| Feature | Slice |
|---------|-------|
| Effort weight / context budget | Slice 4 |
| Progress visibility UI | Slice 3 |
| Kanban visualization | Slice 5 |
| RAG retrieval | Slice 8 |
| Chat merging | Future |
| Context building strategies | Future |

## Core Concepts

### Artifacts: The Core Primitive

Artifacts are markdown files with YAML frontmatter. The frontmatter carries state:

```yaml
---
status: backlog | ready-for-stories | in-progress | done
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, social]
priority: normal
source: artifacts/discovery/trading-churn.md  # optional
---

# Artifact Title

Content here...
```

Key properties:
- Artifacts carry their own status (no external system needed)
- Agents poll for artifacts matching their target status
- Git tracks history
- Artifact types are defined by pipelines, not hard-coded

### Storage Structure

```
~/.oi/
├── artifacts/
│   ├── brainstorms/
│   │   └── guild-system-v1.md
│   ├── discovery/
│   │   └── trading-churn.md
│   ├── stories/
│   ├── architecture/
│   ├── tests/
│   └── commits/
│
└── chats/                    # For chat capture
    └── {chat_id}/
        ├── manifest.yaml     # Summary log
        └── raw.jsonl         # Full verbatim
```

---

## Detail

### Pipeline Capture Pattern (Artifact Status)

Agents poll for artifacts, do work, update status:

```
1. Agent polls for: status: ready-for-{agent}
2. Agent claims artifact (status: in-progress-{agent})
3. Agent does work
4. Agent produces new artifact(s)
5. Agent updates status (status: ready-for-{next})
```

**Example: Story Agent**

```
1. Poll: artifacts with status: ready-for-stories
2. Claim: guild-system-v1.md → status: in-progress-stories
3. Work: Read brainstorm, write user stories
4. Produce: artifacts/stories/guild-system-v1.md
5. Update: brainstorm → status: stories-complete
         stories → status: ready-for-tests
```

No chat log needed. Artifacts are the capture.

### Chat Capture Pattern (Two-Log Model)

For user-AI collaborative sessions, maintain two logs:

| Log | Purpose | Format |
|-----|---------|--------|
| **Raw** (`raw.jsonl`) | Full verbatim, audit trail | Append-only JSONL |
| **Manifest** (`manifest.yaml`) | Summary, artifact links | YAML, updated each turn |

**Raw Log Format:**

```jsonl
{"turn": 1, "role": "user", "content": "I want to add guilds...", "ts": "..."}
{"turn": 2, "role": "assistant", "content": "Guilds can mean...", "ts": "..."}
```

**Manifest Format:**

```yaml
chat_id: "abc123"
started: "2024-01-17T10:00:00Z"
updated: "2024-01-17T11:30:00Z"
status: active | concluded

segments:
  - id: seg_1
    summary: "User proposed guild system, AI explored requirements"
    raw_lines: [1, 24]
    artifacts: []

  - id: seg_2
    summary: "Refined guild scope, decided on 25-member limit"
    raw_lines: [25, 48]
    artifacts: ["brainstorms/guild-system-v1.md"]
```

### Continuous Capture Loop

Don't wait until the end. Capture with every response:

```
User message → AI response → Capture step → Ready for next
                                  │
                                  ├─ Append to raw.jsonl
                                  ├─ Update manifest summary
                                  └─ If conclusion → create artifact
```

The manifest is always current. No end-of-session "did we capture everything?"

**Key Insight**: At any point, you can end the session - nothing lost. You can continue - full context available via manifest. Future sessions can reference - manifest links to artifacts and raw.

### Artifact Creation (From Chat)

When a conversation produces a conclusion:

1. **Detect conclusion** - User says "let's ship it", AI drafts artifact
2. **Create artifact** - Save to `artifacts/{type}/{name}.md`
3. **Link in manifest** - Add artifact ref to current segment
4. **Set status** - Artifact starts with `status: backlog`

The artifact is now independent. It can enter a pipeline regardless of chat state.

### Segment Types

| Type | Produces Artifact? | Example |
|------|-------------------|---------|
| **effort** | Yes - effort artifact | Debugging, problem-solving |
| **fact** | Yes - fact artifact | "I prefer dark mode" |
| **event** | Yes - event artifact | "Meeting scheduled for Tuesday" |
| **greeting** | No | "Hi", "Thanks" |
| **calculation** | No | "What's 15% of 200?" |
| **clarification** | No | "What did you mean by X?" |
| **meta** | No | "Let's change topic" |

---

## User Experience (from scenarios)

### The Collaborative Brainstorm Flow

A user with a rough idea talks it through with an AI assistant. The conversation is the refinement process:

```
User's Rough Idea → Conversation → Brainstorm Artifact (.md) → Pipeline
```

The AI doesn't just take notes—it challenges, clarifies, and suggests. The user doesn't just dictate—they react, redirect, and decide.

**Artifact carries state in frontmatter:**

```yaml
---
status: backlog | ready-for-stories | in-progress | done
created: 2024-01-15
tags: [enhancement, social]
---
```

Agents poll for artifacts matching their target status. No external system needed.

### What Makes This Work

1. **Conversation as Refinement** - Back-and-forth surfaces edge cases, risks, decisions
2. **AI Challenges, User Decides** - AI pushes back on assumptions but user makes final calls
3. **Artifact Captures Decisions** - Records not just WHAT was decided but WHY
4. **Clean Handoff** - Artifact contains everything next agent needs, no conversation history required
5. **Self-Contained State** - Artifact carries its own status in frontmatter
6. **Pipeline Unchanged** - Pipeline doesn't care how brainstorm happened, just needs artifact with right status

---

## Success Criteria (from scope doc)

### Pipeline Capture
- [ ] Artifacts use frontmatter for status
- [ ] Agents can poll for artifacts by status
- [ ] Status updates move artifacts through pipeline
- [ ] New artifact types can be added without code changes

### Chat Capture
- [ ] Raw log appends every turn
- [ ] Manifest updates with segment summaries
- [ ] Artifacts created on conclusion
- [ ] Manifest links to artifacts produced
- [ ] Can rebuild context from manifest + artifacts

---

## Design Principles

1. **Artifacts are primary** - Chats are process, artifacts are knowledge
2. **Status in frontmatter** - No external system to sync
3. **Types are pipeline-driven** - Not a fixed list
4. **Git is the database** - History, branching, collaboration for free
5. **Continuous capture** - Never lose knowledge mid-session

---

## Source Documents

- `docs/slices/01-core-capture.md` (scope doc)
- `docs/brainstorm/context-and-cognition.md` (sections: Two-Log Model, Continuous Capture)
- `docs/scenarios/user-ai-collaborative-scenario.md` (user experience detail)
