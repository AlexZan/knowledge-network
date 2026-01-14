# Slice 1a: Minimal Effort Artifact Compaction

The bare minimum to prove the thesis works.

---

## Goal

See automatic effort detection and compaction in action. Measure token savings.

---

## Scope

**In scope:**
- Basic CLI conversation (start, chat, exit)
- Automatic effort resolution detection
- Effort artifact extraction
- Context building (artifacts + recent messages)
- Persistence (state survives restart)
- Token stats (displayed automatically after each artifact)

**Single continuous conversation:**
- No separate chats/sessions
- Close and reopen CLI = continue where you left off
- Multiple chat support is future scope

**Out of scope (moved to 1b):**
- Manual commands (`/resolve`, `/reject`, `/expand`, `/artifacts`, `/stats`)
- Artifact lifecycle (update, correct, reject)
- Error handling polish
- Help text

---

## Core Mechanic: Resolution Detection

### The Rule

**If user does not disagree → resolve the effort.**

Default state is resolution. Only explicit disagreement keeps an effort open.

### Detection Flow

```
1. AI responds (potentially containing a resolution)
2. User responds
3. Analyze user response:
   - Disagreement detected? ("no", "that's wrong", "but what about...", "I don't think so")
     → Effort stays open, conversation continues
   - Anything else? (affirmation, topic change, new question, etc.)
     → Trigger effort artifact extraction
```

---

## Example Session

```
$ oi

You: How do I fix this auth bug?

AI: The issue is expired tokens. You need to refresh the token before making API calls.

You: Ah that makes sense, thanks!

[effort:resolved] Debug auth bug
  => Token was expired, refresh fixed it
[Tokens: 847 raw → 52 compacted | Savings: 94%]

You: Now I have a database question...
```

---

## Data Structures

### Artifact

```
{
  id: string,
  type: "effort",
  summary: string,           // What user was trying to do
  status: "open" | "resolved",
  resolution: string | null, // How it was resolved (when resolved)
  source_ref: string,        // Reference to chat log location
  created: timestamp
}
```

### Chat Log (append-only)

```
// chatlog.jsonl - permanent record
{"role": "user", "content": "...", "timestamp": "..."}
{"role": "assistant", "content": "...", "timestamp": "..."}
```

### Conversation State

```
{
  artifacts: [Artifact],
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
Context Builder ←── Artifacts (compacted) + Recent Messages
    ↓
LLM API Call
    ↓
Response → Display to user
    ↓
User responds
    ↓
Resolution Detector
    ├── Disagreement? → effort stays open
    └── No disagreement? → Extract artifact → Persist → Show stats
```

---

## Context Building

```
[System Prompt]
---
Resolved efforts from this conversation:
- [effort:resolved] Debug auth bug => Token was expired, refresh fixed it
- [effort:resolved] Fix database issue => Set max_connections=10
---
Recent conversation:
[User]: Now I have a new question...
[Assistant]: ...
```

---

## Persistence

```
~/.oi/
├── state.json      # Artifacts and stats
└── chatlog.jsonl   # Append-only message log
```

---

## Success Criteria

1. [ ] Can start CLI and have a conversation
2. [ ] When user doesn't disagree, effort artifact is automatically extracted
3. [ ] Artifact + token stats are displayed
4. [ ] Next turn uses artifacts in context (not full chat history)
5. [ ] State persists across restart
6. [ ] Token savings are measurable (>50%)
