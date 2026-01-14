# Effort-Scoped Context Model

Brainstorm session exploring how context, compaction, and efforts relate.

---

## The Problem with Current Systems

**Auto-compaction at arbitrary points** (when context fills up):
- Loses details at random boundaries
- Feels like a band-aid
- Forced summary at arbitrary point misses nuance

**Growing chat logs with old summaries**:
- Old summaries may have no relevance to current work
- Loading everything in every prompt is wasteful
- Relevance decays but storage doesn't

---

## Core Insight

Compaction should happen at **meaningful boundaries** (effort completion, topic change) not arbitrary ones (context limit reached).

When a new effort/objective is expressed by the user, that signals:
- Previous efforts are not needed in full detail
- If details ARE needed, they can be referenced and pulled (RAG-style)
- Not loaded as context with every prompt

---

## The Emerging Model

```
┌─────────────────────────────────────────────────────────┐
│ CHAT                                                    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ CURRENT EFFORT (full context)                   │   │
│  │ - All turns since effort started                │   │
│  │ - Interactive, user can step through            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ PREVIOUS EFFORTS (compacted)                    │   │
│  │ - Summary list: "Fixed auth bug → token refresh"│   │
│  │ - Links to raw logs if details needed           │   │
│  │ - NOT loaded in full every prompt               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ARTIFACTS (cross-chat knowledge)                │   │
│  │ - Facts, preferences, resolved efforts          │   │
│  │ - RAG-retrieved when relevant                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Chat Management Revolution

**Problem**: Users hate managing chat lists (searching, archiving, renaming, deleting)

**Solution**: AI handles this automatically:
- Start new chat → AI finds relevant old context/artifacts
- No need to search for old chats manually
- Chat logs still exist (composed of summaries) for manual search if wanted

**Two files per chat**:
1. **Chat log** = summarized artifact of the conversation (what was done, current state)
2. **Artifacts** = extracted knowledge (facts, resolutions, cross-referenceable)

---

## Topic Change Handling

Not all topic changes are equal:

| Type | Example | Action |
|------|---------|--------|
| **Unrelated** | bug → coffee | AI suggests: "New chat?" (no context) |
| **Related** | bug → related feature | AI suggests: "Fork?" (copy context) |
| **Resolution** | bug → "thanks, fixed" | Compact effort, stay in chat |

Key principle: Each chat sticks to a **coherent subject**. AI helps enforce this by suggesting new/fork when appropriate.

---

## Agents in This Model

**Current subagent pattern**:
- Benefit = separate context window
- Main agent spawns subagent with summary + instructions
- Subagent works autonomously, returns summary

**In effort-scoped model**:
- Context is always naturally compacted, separate window not needed
- Main agent does work with full context, then compacts
- User can interact step-by-step (vs autonomous subagent)

**Key difference**: Interactive work vs autonomous execution

**Open question**: Is full context beneficial for the work, or is a focused summary better? (Subagent gets summary, effort-agent gets full context)

---

## Comparison with Current Systems

| Current Systems | Effort-Scoped Model |
|-----------------|---------------------|
| Compaction when context fills | Compaction when effort completes |
| Arbitrary boundary, loses detail | Meaningful boundary, captures resolution |
| Growing context until forced cut | Bounded effort context + summary history |
| Subagents for separate context | Same agent, effort-scoped focus |
| Subagents run autonomously | Interactive, user steps through |

---

## Two Main Goals (Early Slices)

1. **No chat management burden** - AI handles finding/organizing
2. **No forced auto-compaction** - natural compaction at effort boundaries means never hitting context limit

---

## New Thought: Constraint as Feature

> "Maybe there is a lack of rules beyond utility... maybe some constriction would be beneficial."

**Idea**: One chat = one effort

Or more precisely:
- A chat **spawns** an effort
- An "effort chat" is **locked to a single effort**
- Child efforts allowed, but must contribute to parent effort
- Enforces focus, simplifies compaction boundaries

```
EFFORT CHAT
├── Main Effort: "Build authentication system"
│   ├── Child Effort: "Research OAuth libraries"
│   ├── Child Effort: "Implement login endpoint"
│   └── Child Effort: "Debug token refresh bug"
│
│   All child efforts MUST contribute to parent
│   Unrelated topics → AI suggests new chat
```

**Benefits of constraint**:
- Clear compaction boundaries (chat ends when effort resolves)
- No ambiguity about what context is relevant
- Forces user to articulate what they're trying to accomplish
- Child efforts = natural decomposition, all roll up to parent

**Open question**: Is this too restrictive? Does it hurt flexibility?

---

## Implications for Slice 1

If we adopt "one chat = one effort":
- No need for "open/resolved" artifact state tracking
- Chat itself IS the effort state
- Resolution = chat completion (or ready for compaction)
- The "two artifacts" bug goes away - chat produces one artifact on completion

---

---

## Context Strategy: Lazy Compaction

**Old assumption**: Compact early and often to stay small
**New assumption**: Stay large as long as possible, compact only when needed

**Why more context is better**:
- Better model understanding and performance
- Raw details preserved (no premature summarization loss)
- No risk of losing something important early

**The strategy**:

```
0%────────────────────70%─────────90%────100%
│                      │          │       │
│  RAW CONTEXT         │ COMPACT  │ DANGER│ LIMIT
│  (keep granular)     │ ZONE     │       │
│                      │          │       │
└──────────────────────┴──────────┴───────┘
                       ↑
                    Start selective compaction here
```

**Selective compaction order** (when needed):
1. First: Drop low-relevance turns (vector filtered - greetings, filler)
2. Then: Summarize oldest exchanges (preserve recent detail)
3. Last resort: Aggressive summarization

---

## Effort Weight: Quality vs Cost Tradeoff

More context = better results but more expensive. Need a dial.

**Effort Weight** (or "context budget"):

```
EFFORT WEIGHT: low ◄─────────────────► high
               │                        │
CONTEXT:       minimal                  maximal (90%)
COST:          cheap                    expensive
COMPACTION:    aggressive, early        lazy, late
USE CASE:      casual learning          critical dev work
```

**Examples**:

| Effort Type | Weight | Context Strategy |
|-------------|--------|------------------|
| "Tell me about WW2" | low | Compact aggressively, keep it cheap |
| "Debug prod outage" | high | Max context, preserve every detail |
| "Plan vacation" | medium | Balanced |
| "Refactor auth system" | high | Full context, no shortcuts |

**How weight is set**:
1. **User explicit**: `/weight high` or `--priority critical`
2. **Inferred from keywords**: "production", "urgent", "debug" → high
3. **Effort type defaults**: dev work → high, general questions → low
4. **Global user preference**: "I'm a cheapskate" vs "quality over cost"

**The formula**:
```
context_budget = base_limit * effort_weight
compact_threshold = context_budget * 0.7

if current_context > compact_threshold:
    compact(strategy=weight_based)
```

**Ties into "one chat = one effort"**: Weight set once for the chat, governs entire context strategy.

---

## Focus Constraint: Tied to Effort Weight

The "one chat = one effort" constraint isn't binary - it's a spectrum tied to effort weight.

**The spectrum**:

```
FLEXIBLE                                              LOCKED
(current systems)                               (one effort = one chat)
     │                                                    │
     │  casual learning    planning    dev work   prod bug│
     │       ←─────────────────────────────────────────→  │
     │                                                    │
   "tell me about WW2"                    "fix auth bug"  │
   topic drift OK                         deviation = warning
```

**Constraint level by weight**:

| Weight | Constraint | Behavior on Deviation |
|--------|------------|----------------------|
| **low** | flexible | AI follows along, maybe gentle "this seems different" |
| **medium** | soft | AI notes deviation, asks "new chat or continue?" |
| **high** | locked | AI enforces: "This deviates from [effort]. New chat?" |

**Example enforcement (high weight dev effort)**:
```
You: "Actually, what's a good recipe for pasta?"

Agent: "⚠️ This deviates from current effort: Fix auth bug
        → Start new chat for pasta question?
        → Or mark auth effort as paused/abandoned?"
```

**Default weights by effort type**:

| Effort Type | Default Weight | Default Constraint |
|-------------|----------------|-------------------|
| Dev work | high | locked |
| Bug fix | high | locked |
| Code review | high | locked |
| Planning | medium | soft |
| Research | low | flexible |
| Learning | low | flexible |
| Casual chat | low | flexible |

**User overrides**:
- `/lock` - enforce constraint regardless of weight
- `/unlock` - allow flexibility regardless of weight
- `/weight high|medium|low` - change weight (and thus constraint)

**Benefits of enforcement for dev work**:
- Keeps you focused (rubber duck effect)
- Prevents context pollution with irrelevant tangents
- Clean git history (one effort = one branch)
- Token budget stays on-task
- Forces explicit decisions about context switching

**When flexibility helps**:
- Learning/research (rabbit holes are the point)
- Brainstorming (tangents spark ideas)
- Casual chat (no stakes)

---

## Model Escalation Strategy

**Goal**: Use cheap/free models by default, escalate to expensive models only on repeated failure.

**The tier ladder**:
```
FREE/CHEAP          STANDARD           EXPENSIVE
────────────────────────────────────────────────►
GLM 4 / Haiku       Sonnet             Opus
     │                  │                 │
     │ 2 failures       │ 2 failures      │
     └─────────────────►└────────────────►│
                                          │
                                    Last resort
```

**Escalation triggers**:
- ✅ Task fails 2+ times at current tier
- ✅ Complexity detected (multi-step reasoning needed)
- ✅ User explicitly requests higher tier
- ❌ NOT: "I'm not sure" (ask user instead)
- ❌ NOT: "Test seems wrong" (review with test-architect instead)

**De-escalation**:
- After success, future similar tasks start cheap again
- Track task-type success rates per model
- Learn which tasks need which tier

**Integration with effort weight**:

| Effort Weight | Starting Model | Max Escalation |
|---------------|----------------|----------------|
| low | free tier | Sonnet (cap) |
| medium | free tier | Opus |
| high | Sonnet | Opus (faster escalation) |
| critical | Opus | Opus (start at top) |

**Cost tracking**:
- Log tokens per model tier
- Show user: "This effort used 80% free tier, 20% Sonnet"
- Highlight expensive escalations for review

**Future refinement**:
- Fine-tune cheap models on successful expensive completions
- Build task→model mapping from usage data
- Auto-detect task complexity before starting

---

## Next Steps

- Debate: Is "one chat = one effort" too restrictive?
- Define: What constitutes a "child effort" vs unrelated topic?
- Design: How does forking work with effort hierarchy?
- Design: How is effort weight inferred vs explicit?
- Prototype: Try the constrained model and see if it feels right
