# Slice 1a: Minimal Conclusion Tracking

The bare minimum to prove the thesis works.

---

## Goal

See automatic conclusion detection and compaction in action. Measure token savings.

---

## Scope

**In scope:**
- Basic CLI conversation (start, chat, exit)
- Automatic conclusion detection
- Conclusion extraction
- Context building (conclusions + active thread)
- Persistence (state survives restart)
- Token stats (displayed automatically after each conclusion)

**Single continuous conversation:**
- No separate chats/sessions
- Close and reopen CLI = continue where you left off
- Multiple chat support is future scope

**Out of scope (moved to 1b):**
- Manual commands (`/conclude`, `/reject`, `/expand`, `/conclusions`, `/stats`)
- Conclusion lifecycle (update, correct, reject)
- Error handling polish
- Help text

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

---

## Example Session

```
$ kn

You: How do I fix this auth bug?

AI: The issue is expired tokens. You need to refresh the token before making API calls.

You: Ah that makes sense, thanks!

[Conclusion extracted: "Auth bug caused by expired tokens. Fix: refresh token before API calls."]
[Tokens: 847 raw → 52 compacted | Savings: 94%]

You: Now I have a database question...
```

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
  conclusion_id: string | null
}
```

### Conclusion

```
{
  id: string,
  content: string,
  source_thread_id: string,
  created: timestamp
}
```

### Conversation State

```
{
  threads: [Thread],
  conclusions: [Conclusion],
  active_thread_id: string,
  token_stats: {
    total_raw: number,
    total_compacted: number
  }
}
```

---

## Architecture

```
User Input
    ↓
Context Builder ←── Conclusions (compacted) + Active Thread (full)
    ↓
LLM API Call
    ↓
Response → Display to user
    ↓
User responds
    ↓
Disagreement Detector
    ├── Disagreement? → continue thread
    └── No disagreement? → Extract conclusion → Persist → Show stats
```

---

## Context Building

```
[System Prompt]
---
Previous conclusions from this conversation:
- Auth bug caused by expired tokens. Fix: refresh token before API calls.
- Database pooling issue. Fix: set max_connections=10.
---
Current conversation:
[User]: Now I have a new question...
[Assistant]: ...
```

---

## Persistence

```
~/.knowledge-network/
├── state.json
└── threads/
    └── t001.json
```

---

## Success Criteria

1. [ ] Can start CLI and have a conversation
2. [ ] When user doesn't disagree, conclusion is automatically extracted
3. [ ] Conclusion + token stats are displayed
4. [ ] Next turn uses conclusions in context (not full thread)
5. [ ] State persists across restart
6. [ ] Token savings are measurable (>50%)
