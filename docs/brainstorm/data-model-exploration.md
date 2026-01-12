# Data Model Exploration

## Evolution of Thinking

### Started With
- **Threads** = conversations
- **Conclusions** = extracted knowledge
- **History** = chronological log of threads

### Problem Discovered
Scenario 4: User says "I'm thinking about adding multiplayer", session ends without resolution. Next day: "Okay I decided - let's do co-op".

**Problem**: No conclusion exists for open/unresolved work. The AI wouldn't know about the pending decision.

### New Model: Efforts + Conclusions

**Effort** = what we're trying to accomplish
- Can be **open** (in progress) or **resolved**
- Can have **child efforts** (hierarchical)
- Tracks the journey, not just the outcome
- Has metadata: tokens spent, time, sessions

**Conclusion** = resolution of an effort
- Tied to parent effort
- Multiple possible (failed attempts + final success)

```
Effort: "Fix player collision bug" (3 days, 50k tokens)
├── Effort: "Try increasing collider size"
│   └── Conclusion: "Failed - still falls through on slopes"
├── Effort: "Try ground check raycast"
│   └── Conclusion: "Works! Added raycast before movement"
└── Conclusion: "Fixed using ground check raycast"

Effort: "Add multiplayer mode" [OPEN - no conclusion yet]
└── (waiting for user decision on co-op vs competitive)
```

## Scenarios Tested

### ✓ Works Well

| Scenario | Why It Works |
|----------|--------------|
| Recency: "Where did we leave off?" | Scan recent efforts (open + closed) |
| Fresh start: "New idea" | Past conclusions provide project context |
| Search: "That bug we fixed?" | Search efforts/conclusions |
| Learning: "Explain X to me" | Learning IS an effort with resolution |
| Creative: "Write a story" | Iterative child efforts |
| Planning: "Plan trip to Japan" | Hierarchical efforts |

### ? Uncertain

| Scenario | Issue |
|----------|-------|
| Simple Q&A: "Capital of France?" | Works but feels heavyweight - is this really an "effort"? |

### ✗ Doesn't Fit

| Scenario | Issue |
|----------|-------|
| Casual chat: "How's it going?" | No goal, no resolution, just social exchange |

## Open Questions

1. **Is everything an effort?**
   - Simple Q&A works but feels like overkill
   - Casual chat has no goal - not an effort?
   - Maybe: efforts vs exchanges (lightweight non-goal interactions)?

2. **Effort types/weights?**
   - Maybe efforts have types: `project`, `question`, `learning`, `planning`
   - Or weights: `major`, `minor`, `trivial`

3. **What about casual chat?**
   - Not everything has a goal
   - Still want to remember "user mentioned they were tired"?
   - Or just discard social noise?

4. **How does AI build context?**
   - Scan recent efforts (summaries)
   - See open efforts = pending work
   - See closed efforts = completed work with conclusions
   - Drill into child efforts or raw thread if needed

5. **Data structure?**
   ```
   Effort:
     id
     summary (always present - the "what")
     status: open | resolved
     parent_effort_id (nullable - for hierarchy)
     conclusion_ids[] (can have multiple)
     thread_id (raw conversation if needed)
     metadata: {tokens, sessions, created, updated}

   Conclusion:
     id
     content (the knowledge/resolution)
     effort_id
     created
   ```

## Next Steps

- Decide: Is casual chat an effort, a different type, or discarded?
- Decide: Are simple Q&As lightweight efforts or something else?
- Once model is solid, update schema and code

## Key Insight (v1)

> The network is **efforts linked to efforts**, with conclusions as leaves.
> Open efforts = pending work. Closed efforts = resolved work.
> This captures the journey, not just the outcomes.

---

## Breakthrough: Self-Evolving Artifact Schemas

### The Realization

Effort/Conclusion is just ONE artifact type - not THE model.

The chat log is the **raw artifact**. Everything else is a **learned compression format**.

```
Chat Log (raw)
    ↓
[Artifact Type A: Effort/Conclusion] - for goal-oriented work
[Artifact Type B: ???] - for casual exchanges
[Artifact Type C: ???] - for learning journeys
[Artifact Type D: ???] - user-specific, emerges from usage
    ↓
[Higher-order artifacts] - patterns across artifacts
```

### Core Ideas

1. **Multiple compression formats** - Different "lenses" on the same conversation
2. **Self-evolving schemas** - System learns what formats work for THIS user
3. **Human-readable neural network** - Emergent structure that's still inspectable/auditable
4. **Contractual by review** - User can see and correct what it learned

### The System Learns HOW to Store Knowledge

Not just WHAT to store.

| User Type | Emergent Schemas |
|-----------|-----------------|
| Developer | `bug_fix`, `feature`, `refactor`, `architecture_decision` |
| Researcher | `hypothesis`, `finding`, `contradiction`, `source` |
| Writer | `draft`, `revision`, `feedback`, `character_note` |
| Planner | `goal`, `milestone`, `blocker`, `decision` |

### Analogy to Neural Networks

- Neural networks learn compressed representations (embeddings)
- But they're opaque - you can't inspect them
- This system learns compressed representations too
- But they're **human-readable** and **auditable**
- Like a neural network you can review and correct

### Thesis Evolution

> The network learns both **content** AND **structure**.
> The schemas themselves evolve based on usage patterns.
> Compression formats are first-class, evolvable entities.

### Open Questions

- How does a new schema emerge? (User defines? System proposes? Hybrid?)
- How do schemas evolve over time?
- Can schemas be shared across users? (Community schemas?)
- What's the "base" schema everything starts with?
- How does the system know which schema to apply to a new conversation?
