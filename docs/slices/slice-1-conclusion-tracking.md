# Slice 1: Single-Session Conclusion Tracking

The foundation. A CLI chat that automatically detects conclusions and compacts them.

---

## Goal

Prove that conclusion-triggered compaction works and saves tokens without losing information.

---

## Decisions

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| Interface | CLI (terminal) | Fast to build, fits developer workflow |
| Detection | Fully automatic | Seamless UX, system handles it |
| Threads | Single linear | Simplest MVP, one conversation stream |
| Persistence | Always persistent | Conclusions survive restarts, enables future slices |

---

## Core Mechanic: Conclusion Detection

### The Rule

**If user does not disagree → conclude.**

Default state is resolution. Only explicit disagreement keeps a thread open.

### Detection Flow

```
1. AI responds (potentially containing a resolution)
2. User responds
3. Analyze user response:
   - Disagreement detected? ("no", "that's wrong", "but what about...", "I don't think so")
     → Thread stays open, conversation continues
   - Anything else? (affirmation, topic change, new question, etc.)
     → Trigger conclusion extraction
```

### Why This Works

- User is the authority on whether something is resolved
- No false positives from AI thinking it solved something
- Simple to implement: detect disagreement, everything else concludes
- Natural conversation flow, no explicit commands needed

---

## Conclusion Lifecycle

Conclusions are not final. They can evolve:

```
Created ──→ Active ──→ Updated (append new info)
                   ──→ Corrected (was partially wrong)
                   ──→ Rejected (turned out to be wrong entirely)
```

A rejected conclusion becomes evidence for its replacement (ties to confidence mechanics in later slices).

---

## Data Structures

### Thread

```
{
  id: string,
  messages: [
    { role: "user" | "assistant", content: string, timestamp: string }
  ],
  status: "open" | "concluded",
  conclusion_id: string | null  // if concluded
}
```

### Conclusion

```
{
  id: string,
  content: string,              // the compact summary
  status: "active" | "updated" | "rejected",
  source_thread_id: string,     // link to full history
  created: timestamp,
  updates: [                    // for appends/corrections
    { content: string, timestamp: string, type: "append" | "correct" }
  ]
}
```

### Conversation State

```
{
  threads: [Thread],            // full history, never deleted
  conclusions: [Conclusion],    // extracted conclusions
  active_thread_id: string,     // current open thread
  token_stats: {
    total_raw: number,          // tokens if we kept everything
    total_compacted: number,    // tokens with conclusions
    savings_percent: number
  }
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLI Interface                  │
├─────────────────────────────────────────────────┤
│  User Input                                      │
│      ↓                                           │
│  Context Builder                                 │
│      │← Conclusions (compacted)                  │
│      │← Active Thread (full)                     │
│      ↓                                           │
│  Prompt Assembly                                 │
│      ↓                                           │
│  API Call (Claude)                               │
│      ↓                                           │
│  Response Handler                                │
│      ↓                                           │
│  Disagreement Detector                           │
│      │                                           │
│      ├── Disagreement? → continue thread         │
│      └── No disagreement? → extract conclusion   │
│             ↓                                    │
│      Conclusion Extractor (LLM call)             │
│             ↓                                    │
│      Update State + Persist                      │
│      ↓                                           │
│  Output to User                                  │
└─────────────────────────────────────────────────┘
```

---

## Context Building Strategy

When building the prompt for an API call:

1. **System prompt**: Instructions for the AI
2. **Conclusions**: All active conclusions (compacted form)
3. **Active thread**: Full messages from current open thread

```
[System Prompt]
---
Previous conclusions from this conversation:
- C001: Auth failed due to expired tokens. Solution: refresh before API calls.
- C002: Database connection pooling was causing memory leak. Fixed with max_connections=10.
---
Current conversation:
[User]: I'm seeing a new error now...
[Assistant]: ...
```

This way, context grows slowly (conclusions) while keeping full detail for active work.

---

## Token Accounting

Track and display savings:

```
Session Stats:
- Raw tokens (no compaction): 12,450
- Compacted tokens: 2,180
- Savings: 82.5%
- Conclusions extracted: 7
```

This proves the thesis works.

---

## Persistence

Store in local JSON files:

```
~/.knowledge-network/
├── state.json          # current conversation state
├── threads/            # archived full threads
│   ├── t001.json
│   └── t002.json
└── conclusions.json    # all conclusions
```

---

## Commands (Optional Overrides)

While detection is automatic, power users might want manual control:

| Command | Action |
|---------|--------|
| `/conclude` | Force conclude current thread |
| `/reject <id>` | Mark a conclusion as rejected |
| `/expand <id>` | Show full thread for a conclusion |
| `/conclusions` | List all conclusions |
| `/stats` | Show token savings |

---

## Success Criteria

1. [ ] Can have a multi-turn conversation via CLI
2. [ ] Conclusions are automatically detected and extracted
3. [ ] Full thread history is preserved but not loaded into context
4. [ ] Token savings are measurable and significant (>50% on typical sessions)
5. [ ] State persists across restarts
6. [ ] Can view/reject/update conclusions manually

---

## Out of Scope (Future Slices)

- Multiple named threads
- Cross-session knowledge graph
- Confidence scoring
- Sharing/privacy layers
- Multi-model support
