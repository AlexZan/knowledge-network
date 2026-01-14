# Refined Chat Model

## Evolution of Thinking

Started with: Sessions as first-class context containers with dashboards

Refined to: **Chats + Artifacts** - simpler, closer to original thesis

## The Core Model

```
Chat = series of messages (like traditional AI systems)
      ↓
Compaction happens naturally as conversation progresses
      ↓
Artifacts = extracted value (facts, efforts, events)
      ↓
Context = artifacts + recent messages (not full history)
```

### Key Insight

**We're not replacing chat logs - we're augmenting them with auto-compaction.**

Traditional AI systems:
```
Chat grows → Token limit → Truncate/summarize → Information loss
```

This system:
```
Chat grows → Artifacts extracted → Context stays small → Nothing lost
```

## Terminology

| Term | Definition |
|------|------------|
| **Chat** | Full conversation container (series of messages) |
| **Session** | Subset of chat (work period) - future feature, not critical now |
| **Artifact** | Extracted value from conversation (fact, effort, event) |
| **Context** | Artifacts + recent messages (what gets sent to LLM) |
| **Fork** | Copy chat history, continue with branched context |

## The Artifacts Are the Memory

Raw chat contains noise:
- Greetings ("hello", "thanks")
- Confirmations ("yes", "okay")
- Back-and-forth technical discussion
- Exploratory tangents

Artifacts contain signal:
- Decisions made
- Facts learned
- Goals pursued
- Resolutions reached

**Cross-reference artifacts, not raw chat.**

## Starting a New Conversation

When user expresses intent, the system:

1. **Searches** artifacts and chats for relevance
2. **Presents** options with context

```
User: "I want to work on the payment integration"

AI: I found related context:

RELATED CHATS:
  1. "Payment Gateway Research" (3 days ago)
     Summary: Compared Stripe vs PayPal, decided on Stripe
     Artifacts: 4 (2 facts, 1 resolved effort, 1 open effort)

  2. "API Design Session" (last week)
     Summary: Designed REST endpoints for checkout flow
     Artifacts: 6 (3 facts, 3 resolved efforts)

RELEVANT ARTIFACTS:
  • [fact] Using Stripe API v2023-10
  • [fact] Webhook endpoint: /api/webhooks/stripe
  • [effort:open] Implement refund logic

Options:
  1. Continue "Payment Gateway Research" (has open effort)
  2. Fork from "API Design Session"
  3. New chat with selected artifacts
  4. Start fresh (no prior context)
```

### User Response Options

```
> 1                    → Continue existing chat
> 2                    → Fork, maintains shared history
> 3, include 1,2       → New chat, imports selected artifacts
> 3, exclude 3         → New chat, imports all except specified
> 4                    → Completely fresh start
> just continue        → AI picks most relevant
```

## Forking

Fork = copy chat history, continue with branched context

```
Original Chat A (messages 1-50, artifacts 1-5)
       │
    [Fork at current point]
       │
       ├── Chat A continues (messages 51+, artifacts 6+)
       │
       └── Chat B (forked)
             New messages, new artifacts
             Shares history with A up to fork point
```

Like git branches for conversations.

## Cross-Referencing Knowledge

Artifacts are portable across chats:

```
Chat A: "Payment research"
  → [fact] Using Stripe API
  → [fact] Webhook endpoint

Chat B: "Checkout UI"
  → [fact] Form uses React
  → [effort] Validation logic

Chat C: New chat about "payment form bugs"
  → Imports: Stripe fact + Form fact + Validation effort
  → Has context from BOTH without loading full history
```

**Artifacts are the index into your knowledge.**

## Context Builder Behavior

### At Chat Start (or explicit search)

1. Search artifacts for relevance to user intent
2. Find source chats for those artifacts
3. Present options: continue, fork, new+artifacts, fresh
4. Load selected context
5. Done - conversation proceeds

### During Chat

- Artifacts extracted continuously (via cascading inference)
- Context = current chat's artifacts + recent messages
- No rebuilding needed until fork/new

### Context Caching

Artifact portion of context can be cached:
- Rebuild only when new artifacts created
- Recent messages added each turn
- Hash-based cache invalidation

## The Value Proposition

| Aspect | Traditional | This System |
|--------|-------------|-------------|
| Chat history | Grows unbounded | Compacted to artifacts |
| Finding context | Search chat titles | Search artifacts + AI assists |
| Token usage | Linear growth | Bounded by artifact count |
| Cross-reference | Not possible | Via portable artifacts |
| Forking | Not possible | Branch from any point |
| Information loss | At token limit | Never (raw chat preserved) |

## Implementation Priority

### Slice 1: Proof of Concept

**Scope:**
- Single artifact type: **effort** (with resolution)
- Compact on **conclusion only** (when user accepts/resolves)
- No sub-efforts, no token limit fallback
- Accept context limit as known limitation

**When compaction triggers:**
```
User: "I'm getting a 401 error"
  → No artifact yet (conversation ongoing)

[... back and forth debugging ...]

User: "Oh! Token was expired, works now!"
  → DETECTOR: User accepted solution
  → COMPACT: Extract effort + resolution
  → SAVE: Artifact persists for future sessions
```

**What Slice 1 proves:**
- Conclusion-triggered compaction works
- Artifacts can replace verbose exchanges
- Context stays small while knowledge persists
- Cross-session memory via artifacts

### Future: Smart Chunking (Sub-efforts)

A debugging effort could have multiple attempts as sub-efforts:

```
[effort] Debug auth bug
  ├── [sub-effort] Try refreshing token → failed
  ├── [sub-effort] Check headers → failed
  └── [sub-effort] Inspect JWT payload → FOUND IT
      => Token had wrong audience claim
```

Each sub-effort compacts as it concludes (success or failure), keeping context bounded even during long investigations.

### Future: Token Limit Fallback

Even without natural compaction points, system needs emergency compaction:

```python
if approaching_context_limit() and no_natural_compact_point():
    # Force summarize oldest uncompacted exchanges
    force_summarize_oldest()
    # Or prompt user: "We've been at this a while, let me summarize..."
```

This ensures the system never crashes due to context overflow.

### Slice 1 vs Future Comparison

| Feature | Slice 1 | Future |
|---------|---------|--------|
| Effort artifacts | ✅ | ✅ |
| Compact on conclusion | ✅ | ✅ |
| Fact/event artifacts | ❌ | ✅ |
| Sub-efforts | ❌ | ✅ |
| Token limit fallback | ❌ | ✅ |
| Mid-effort checkpoints | ❌ | ✅ |
| Effort as subagent | ❌ | ✅ |
| Cross-chat search | ❌ | ✅ |
| Fork/continue flow | ❌ | ✅ |

### Soon (Post Slice 1)
- Search/match for continuing chats
- Continue/fork/new+artifacts flow
- Cross-chat artifact references
- Fact and event artifact types

### Later
- Sessions (subdivisions of chats)
- Dashboard views
- Fork visualization
- Artifact graphs
- Sub-efforts and smart chunking
- Token limit fallback

## Relationship to Original Thesis

This IS the thesis:
- **Conclusion-triggered compaction** → Artifacts extracted when understanding reached
- **Keep threads open until resolution** → Open efforts persist
- **Dual storage** → Raw chat + compressed artifacts
- **Context as reasoning, not storage** → Artifacts are reasoned extraction

We just refined the terminology and simplified the model.

## Open Questions

### 1. Artifact Ownership
- Do artifacts belong to a chat or are they global?
- If global, how to handle conflicts between chats?

### 2. Forking Mechanics
- Do forked chats share artifacts or copy them?
- How to visualize fork relationships?

### 3. Search Quality
- How to match user intent to relevant artifacts?
- Semantic search? Keyword? Hybrid?

### 4. Artifact Lifecycle
- When do facts become stale?
- Can resolved efforts be reopened?
- Garbage collection for orphaned artifacts?

### 5. Chat Naming
- Auto-generate names from first message/main effort?
- User can rename?
- Searchable summaries?

---

## Future Insight: Artifacts as Execution Contexts (Subagents)

> **Note**: This is a future unification concept, NOT for Slice 1. Captured here for architectural clarity.

### The Observation

When a user starts working on a bug, the conversation might look like:

```
[user] I'm getting a weird error in auth
[AI] Let's investigate...
[user] Here's the error log
[AI] Try X
[user] Didn't work
[AI] What about Y?
...
```

An artifact detector could recognize: "This is an effort - debugging bug X"

But here's the insight: **that effort isn't just data - it's a scoped execution context.**

### The Pattern

```
Chat Log (full context)
    │
    └── DETECTOR: "This is an effort - extract it"
            │
            ↓
        ┌─────────────────────────────┐
        │ EFFORT ARTIFACT             │
        │ "Debugging bug X"           │
        │ Status: open                │
        │                             │
        │ [Focused thread/context]    │
        │ ├── error details           │
        │ ├── attempt 1: failed       │
        │ ├── attempt 2: trying...    │
        │                             │
        │ (This IS a subagent)        │
        └─────────────────────────────┘
```

### The Generalization

**An artifact isn't just passive data - it's a potential execution context that can be spawned, worked on, and collapsed.**

| Artifact State | Subagent Analogy |
|---------------|------------------|
| Effort created | Subagent spawned with goal |
| Working on it | Subagent executing with focused context |
| Writes findings | Subagent updates its own state |
| Resolved | Subagent returns result, terminates |
| Summary remains | Result merged back to parent |

### Token Economics

```
Before extraction:
  Chat: [msg1][msg2][msg3][msg4][msg5]... (growing)
  Main context: 2500 tokens (and growing)

After extraction:
  Main context: [artifact-ref] = 100 tokens
  Effort context: [focused thread] = 2000 tokens (only when active)

When effort resolves:
  Main context: 100 tokens (summary + resolution)
  Effort context: 0 (collapsed, no longer needed)
```

**Key**: You only load the effort's thread when actively working on it.

### Multi-Topic Conversations

This enables parallel work without context pollution:

```
User: "I'm getting a weird error in auth"
  → Spawns: EFFORT "Debug auth error" (focused context)

User: "also, remind me to call mom later"
  → Creates: EVENT "Call mom" (in main context, not effort)

User: "back to that bug - I tried X"
  → Detects: relates to open effort
  → Loads: effort context
  → Continues: work in focused thread

User: "that fixed it!"
  → Resolves: effort with resolution
  → Collapses: effort context back to summary
  → Reclaims: tokens for main context
```

### Artifact Types as Context Types

| Type | Execution Model |
|------|-----------------|
| **Effort** | Active subagent - has goal, does work, returns resolution |
| **Fact** | Passive data - no execution, just knowledge |
| **Event** | Temporal context - expires, no execution |

Efforts are special - they're **active contexts** that do work.

### Conceptual Code

```python
# Future implementation concept
effort = spawn_context(
    goal="Debug bug X",
    context=relevant_messages,  # Focused, not full chat
    parent=main_chat
)

while not effort.resolved:
    effort.work()  # Operates with focused context
    effort.update_artifact()  # Writes findings to itself

# When done:
main_chat.receive(effort.summary)  # Collapsed result
effort.context = None  # Reclaim tokens
```

### Why This Matters

This unifies three concepts:
1. **Memory** - artifacts as stored knowledge
2. **Agents** - efforts as spawnable workers with goals
3. **Context management** - scoped windows that expand/collapse dynamically

### Implementation Notes (Future)

For Slice 1: Artifacts are just data with artifact_type field.

Future slices could:
- Track which messages belong to which effort's "thread"
- Load/unload effort contexts dynamically
- Allow efforts to run semi-autonomously (check in periodically)
- Visualize effort threads as branches

This is a significant architectural evolution that would require careful design.

---

*Refined: 2026-01-14*
*Status: Core model clarified*
*Supersedes: sessions-and-dashboard.md (sessions now optional future feature)*
