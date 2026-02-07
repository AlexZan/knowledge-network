# Context Building and Human Cognition

How context is built, stored, and why it mirrors human cognitive needs.

---

## Core Realization: Chats Compact to Artifact References

A chat, when compacted, is essentially:
- **Pointers to artifacts** (the concluded knowledge)
- **Recent raw turns** (the active working memory)

```
CHAT ──compaction──► ARTIFACTS
                         │
                         ▼
              Artifacts are the real knowledge
              Chat was just the process that created them
```

This means:
- **Artifacts** = first-class knowledge (persistent)
- **Chat** = ephemeral process that produces artifacts
- **Context** = relevant artifacts + current conversation

---

## The Two-Log Model

Every chat maintains two logs:

### Raw Log
- Full verbatim conversation
- Append-only, never modified
- For audit, history, expand-on-demand

### Summary Log (Manifest)
- Structured overview of what happened
- Links to artifacts produced
- Links to raw log sections
- What gets loaded into context

```
RAW LOG                          SUMMARY LOG (manifest)
─────────────────────────────    ─────────────────────────────
Full verbatim conversation       Structured overview
│                                │
├─ turn 1: "Hi!"                 ├─ segment 1: greeting
├─ turn 2: "Hello..."            │   summary: "Exchanged greetings"
├─ turn 3: "Auth bug..."         │   raw_ref: lines 1-4
├─ turn 4: "Check token..."      │   artifacts: []
├─ turn 5: "That fixed it!"      │
├─ ...                           ├─ segment 2: effort
│                                │   summary: "Debugged auth bug"
│                                │   raw_ref: lines 5-42
│                                │   artifacts: [effort:456]
```

### Storage Structure

```
~/.oi/chats/chat-123/
├── manifest.yaml      # Summary log
└── raw.jsonl          # Full verbatim

~/.oi/artifacts/
├── effort-456.yaml    # Referenced by manifest
└── ...
```

### Manifest Format

```yaml
chat_id: "123"
started: "2024-01-17T10:00:00"
effort_weight: medium
status: active

segments:
  - id: seg_1
    type: greeting
    summary: "User greeted, started session"
    raw_lines: [1, 4]
    artifacts: []
    tokens_raw: 45

  - id: seg_2
    type: effort
    summary: "Debugged 401 auth error - token was expired"
    raw_lines: [5, 42]
    artifacts: ["effort:456"]
    tokens_raw: 1247
    tokens_summary: 23

  - id: seg_3
    type: calculation
    summary: "Calculated token savings"
    raw_lines: [43, 48]
    artifacts: []
    tokens_raw: 89
```

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

## Context Building Strategies

### Option A: Chat Log as Context

```
PROMPT = system + chat_history (compacted) + user_message
```

| Pros | Cons |
|------|------|
| Conversational continuity | Context grows over time |
| AI remembers everything said | Old irrelevant stuff lingers |
| Natural flow | Can't pull from other chats |
| Simple mental model | Siloed knowledge |

**Best for**: Deep focused work, debugging sessions

### Option B: Build Context Per Prompt (RAG)

```
PROMPT = system + RAG(user_message) + recent_messages + user_message
```

| Pros | Cons |
|------|------|
| Always relevant context | May lose conversational nuance |
| Can pull from ANY chat/artifact | More processing per prompt |
| Cross-chat knowledge | Less continuity |
| Never grows stale | Harder to debug "why did it know X?" |

**Best for**: Research, exploration, cross-topic work

### Option C: Hybrid

```
PROMPT = system + chat_summary + RAG(user_message) + recent_messages + user_message
```

| Pros | Cons |
|------|------|
| Best of both worlds | More complex |
| Continuity + cross-pollination | Larger prompts |
| Natural merge suggestions | Need to balance sources |

**Best for**: Long-running projects, general use

---

## Effort Weight Controls Context Budget

**Effort Weight** is the master dial:

```
EFFORT WEIGHT (low/medium/high)
       │
       ├──► Context Budget (how much context to use)
       │
       ├──► Compact Threshold (when to start compacting)
       │
       ├──► Focus Constraint (locked vs flexible)
       │
       └──► Starting Model Tier (cheap vs expensive)
```

### Context Building by Weight

```
LOW WEIGHT (cheap):
  - Use summary log only
  - Pull minimal artifact refs
  - last 2-3 raw messages only

MEDIUM WEIGHT (balanced):
  - Use summaries + artifact content
  - last 5-10 raw messages
  - Some RAG retrieval

HIGH WEIGHT (quality):
  - Use summaries + expanded raw sections
  - Full artifact content
  - Extensive RAG retrieval
  - Keep as much raw as possible until threshold
```

---

## Chat Merging

When separate chats converge on same topic:

### Manual Merge

```
User: /merge @chat-auth-bug @chat-token-issues

AI: Analyzing chats...
    - chat-auth-bug: 3 conclusions about token handling
    - chat-token-issues: 2 conclusions about refresh logic
    - Overlap detected: Both discuss JWT expiration

    Creating merged chat with combined context:
    [effort:merged] Token authentication issues
      Sources: chat-auth-bug, chat-token-issues
      Combined artifacts: 5
```

### Auto-Suggested Merge

With RAG, system notices overlap:

```
[RAG found related content]
Your other chat "chat-token-issues" has conclusions about
JWT refresh that seem relevant here.

→ Reference it: /include @chat-token-issues
→ Merge chats: /merge @chat-token-issues
→ Ignore: (continue without)
```

### Why Merging is Simpler Than Expected

Since chats compact to artifact references:
- "Merging" = combining artifact refs + summaries
- Not merging huge chat logs
- Artifacts are already deduplicated in the pool

---

## Human Cognitive Model

### The Need for Conclusion

```
OPEN LOOPS = COGNITIVE BURDEN
───────────────────────────────
Too many open things → scattered focus → mistakes → less productive

CLOSED LOOPS = PROGRESS
───────────────────────────────
Conclude → release mental resources → focus on next → productive
```

This is the **Zeigarnik effect**: incomplete tasks occupy mental resources until closed.

### The Three-Part Awareness

Humans always want to know:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   WHERE WE CAME FROM      WHERE WE ARE       WHERE WE'RE    │
│   (concluded efforts)     (current focus)    GOING          │
│                                              (next steps)   │
│   ✓ Fixed auth bug        → Optimizing DB    → Deploy       │
│   ✓ Wrote tests             queries          → QA           │
│   ✓ Designed schema                          → Docs         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

This is **temporal grounding** - we need to locate ourselves in the flow of work.

### Artifacts as Cognitive Relief

Each concluded artifact:
- **Releases mental load** - it's done, move on
- **Provides visible progress** - I accomplished something
- **Creates a "save point"** - can return if needed
- **Allows fresh focus** - clear space for next thing

**Key insight**: Artifacts aren't just for AI context management - they're for human cognitive ergonomics.

### Visibility Requirements

The system should always show:

| Past | Present | Future |
|------|---------|--------|
| Concluded efforts | Current effort | Suggested next |
| ✓ checkmarks | → arrow/highlight | ? or bullet |
| Collapsed by default | Expanded | Optional |

```
SESSION STATE:
─────────────────────────────────────────
✓ Debug auth bug → token refresh
✓ Optimize DB → added index
→ [CURRENT] Deploy to staging
  • Run smoke tests
  • Update docs
```

This is a **progress bar for knowledge work**.

---

## Continuous Capture (vs End-of-Session)

### The Problem with Current Systems

```
CURRENT (Claude Code, etc):
───────────────────────────────────────────────────
Chat goes on... context fills...

User: "Wait, did we capture everything important?"
AI: "Let me summarize..." (but context is almost full)

[Session ends]

Next session: Raw log exists but NEVER referenced
             Knowledge effectively lost
```

Raw chat logs become orphaned files. Nothing points to them. Knowledge is lost unless manually extracted.

### The Solution: Capture Continuously

Don't wait until the end. Capture with every response:

```
EVERY RESPONSE:
  1. Generate response
  2. Append to raw log
  3. Update manifest with summary of this exchange
  4. If conclusion detected → create artifact, link in manifest

RESULT:
  - Raw log: full detail (audit/expand)
  - Manifest: always current summary + artifact links
  - Artifacts: concluded knowledge
  - Nothing depends on "remembering to capture"
```

### Two Levels of Capture

| Level | When | What |
|-------|------|------|
| **Summary** | Every response (or every N turns) | Condensed version of exchange |
| **Artifact** | On conclusion detection | Structured, cross-referenceable knowledge |

Summaries are lightweight - just enough to reconstruct what happened.
Artifacts are structured - queryable, linkable, first-class knowledge.

### The Continuous Capture Loop

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   User message                                      │
│        ↓                                            │
│   AI response                                       │
│        ↓                                            │
│   ┌─────────────────────────────────────────┐      │
│   │ CAPTURE STEP (automatic, every turn)    │      │
│   │                                         │      │
│   │ 1. Append to raw log                    │      │
│   │ 2. Summarize this exchange              │      │
│   │ 3. Update manifest                      │      │
│   │ 4. Conclusion? → Create artifact        │      │
│   └─────────────────────────────────────────┘      │
│        ↓                                            │
│   Ready for next turn                               │
│   (manifest always reflects current state)          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Comparison

| Current Systems | Continuous Capture |
|-----------------|-------------------|
| Capture is manual/end-of-session | Capture every response |
| Raw logs orphaned, never referenced | Raw logs linked via manifest |
| "Did we get everything?" anxiety | Always captured |
| Knowledge loss on session end | Knowledge preserved organically |
| Context limit = panic point | Context limit = non-event |

### Key Insight

The manifest is always up-to-date. At any point:
- You can end the session - nothing lost
- You can continue - full context available via manifest
- Future sessions can reference - manifest links to artifacts and raw

**No "remember to save" step. No end-of-session scramble. Continuous, automatic, organic.**

---

## Design Principles (from this analysis)

1. **Artifacts are primary, chats are process** - Knowledge lives in artifacts, not chat logs

2. **Two logs serve different needs** - Raw for audit/detail, summary for navigation/context

3. **Effort weight controls everything** - One dial for budget, compaction, focus, model tier

4. **Mirror human cognition** - Support natural conclusion cadence, provide temporal grounding

5. **Visible progress always** - Show past/present/future, concluded/active/next

6. **Merging is just combining refs** - Chats compact to artifact pointers, merging is trivial

---

## Open Questions

- [ ] How to detect segment boundaries automatically?
- [ ] When does RAG retrieval happen (every prompt vs on-demand)?
- [ ] How to present "suggested next" without being annoying?
- [ ] Should merged chats maintain link to originals?
