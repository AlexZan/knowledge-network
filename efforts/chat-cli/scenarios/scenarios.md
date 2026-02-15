# Scenario: Effort-Based Context Management

A developer has a session mixing ambient chatter with focused efforts. This demonstrates how context grows and shrinks as efforts open and conclude.

---

## The Session

### Turn 1-2: Ambient Chatter

```
TURN 1 - Alex:
"Hey, how's it going?"

TURN 2 - Assistant:
"Good! Ready to help. What are you working on today?"
```

No effort is open. Both messages logged to ambient.

**State after Turn 2:**
```
raw.jsonl: turns 1-2 (~40 tokens)
manifest.yaml: empty
efforts/: empty
───────────────────────────────
CONTEXT: ~40 tokens
```

---

### Turn 3-4: Open Effort

```
TURN 3 - Alex:
"Let's debug the auth bug - users are getting 401s after about an hour"

TURN 4 - Assistant:
[LLM calls tool: open_effort("auth-bug")]
"Got it, I've started tracking our work on the auth bug. That timing
suggests token expiration. A few questions:
1. What's your access token TTL?
2. Are you using refresh tokens?"
```

The LLM detects the user wants focused work and calls `open_effort`. The tool creates the effort log and manifest entry. The assistant then responds naturally — no "Opening effort:" prefix.

Turn 3 (user message that triggered the effort) and turn 4 (assistant response) are both logged to the effort file.

**State after Turn 4:**
```
raw.jsonl: turns 1-2 (~40 tokens)
manifest.yaml: { efforts: [{ id: auth-bug, status: open }] }
efforts/auth-bug.jsonl: turns 3-4 (~80 tokens)
───────────────────────────────
CONTEXT: 40 + 10 + 80 = ~130 tokens
```

---

### Turn 5-10: Working on Effort

```
TURN 5 - Alex:
"Access token is 1 hour, yes we have refresh tokens"

TURN 6 - Assistant:
"The 1-hour TTL matches the failure timing. Let me see your refresh logic."

TURN 7 - Alex:
"Here's the code from tokenService.ts:
[shows refresh function code]
But I don't see where it's called automatically"

TURN 8 - Assistant:
"That's the problem - the refresh function exists but nothing calls it.
You need an axios interceptor. Here's the pattern:
[shows interceptor code]"

TURN 9 - Alex:
"Oh that makes sense. So the token just expires because nothing refreshes it."

TURN 10 - Assistant:
"Exactly. The fix is:
- Root cause: refresh tokens never auto-called
- Solution: axios interceptor that refreshes proactively"
```

All messages route to the open effort's log. No tool calls needed — the effort is already open.

**State after Turn 10:**
```
raw.jsonl: turns 1-2 (~40 tokens)
manifest.yaml: { efforts: [{ id: auth-bug, status: open }] }
efforts/auth-bug.jsonl: turns 3-10 (~600 tokens)
───────────────────────────────
CONTEXT: 40 + 10 + 600 = ~650 tokens
```

---

### Turn 11-12: Conclude Effort

```
TURN 11 - Alex:
"I implemented the interceptor and it works. Bug is fixed!"

TURN 12 - Assistant:
[LLM calls tool: close_effort()]
[Tool triggers summarization LLM call → summary written to manifest]
"Nice work! I've wrapped up the auth bug effort. The summary captures
the root cause and fix so we can reference it later without loading
the full conversation."
```

The LLM detects the user signaling completion and calls `close_effort`. The tool:
1. Summarizes the effort's raw log via a separate LLM call
2. Writes the summary to manifest
3. Marks the effort as concluded
4. Removes the raw log from working context

**State after Turn 12:**
```
raw.jsonl: turns 1-2 (~40 tokens)
manifest.yaml:
  efforts:
    - id: auth-bug
      status: concluded
      summary: "Debugged 401 errors after 1 hour. Root cause: refresh tokens
               never auto-called. Fix: axios interceptor for proactive refresh."
      raw_file: efforts/auth-bug.jsonl
efforts/auth-bug.jsonl: turns 3-12 (~700 tokens) ← STILL EXISTS but NOT IN CONTEXT
───────────────────────────────
CONTEXT: 40 + 60 = ~100 tokens  ← DROPPED from 650!
```

**Token savings: 650 → 100 = ~85% reduction**

---

### Turn 13-14: Open New Effort

```
TURN 13 - Alex:
"Now let's work on the guild feature - I want to add a member limit"

TURN 14 - Assistant:
[LLM calls tool: open_effort("guild-feature")]
"Tracking our work on the guild feature. For member limits:
1. What's the max you're thinking?
2. Should it be configurable per guild or global?"
```

**State after Turn 14:**
```
raw.jsonl: turns 1-2 (~40 tokens)
manifest.yaml:
  efforts:
    - id: auth-bug, status: concluded, summary: "..."
    - id: guild-feature, status: open
efforts/auth-bug.jsonl: (~700 tokens) ← NOT in context
efforts/guild-feature.jsonl: turns 13-14 (~60 tokens) ← IN context
───────────────────────────────
CONTEXT: 40 + 60 + 60 = ~160 tokens
```

---

## Context Size Through Session

| Point | Context Size | What Changed |
|-------|--------------|--------------|
| After ambient (turn 2) | ~40 tokens | Just chatter |
| After opening auth-bug (turn 4) | ~130 tokens | +effort overhead |
| After working on auth-bug (turn 10) | ~650 tokens | Effort grew |
| **After concluding auth-bug (turn 12)** | **~100 tokens** | **-550 tokens!** |
| After opening guild-feature (turn 14) | ~160 tokens | New effort |

---

## What This Proves

1. **Efforts isolate context** — auth-bug work doesn't pollute ambient
2. **Open efforts = full raw** — complete context while working
3. **Concluded efforts = summary only** — massive token savings
4. **Context is predictable** — always: ambient + manifest + open effort
5. **Natural language interface** — LLM manages tools, user never types commands

---

## File Structure After Session

```
session/
├── raw.jsonl                    # 40 tokens (ambient only)
├── manifest.yaml                # 60 tokens (auth-bug summary + guild-feature entry)
└── efforts/
    ├── auth-bug.jsonl           # 700 tokens (preserved on disk, not in context)
    └── guild-feature.jsonl      # 60 tokens (in context, effort is open)
```

---

## How Tool Calls Work

The LLM has three tools available:

| Tool | When LLM calls it | What the tool does |
|------|-------------------|-------------------|
| `open_effort(name)` | User wants to start focused work | Creates effort log + manifest entry. Fails if one already open. |
| `close_effort()` | User signals work is complete | Summarizes raw log, writes to manifest, removes from context. |
| `effort_status()` | User asks about efforts | Returns open/concluded efforts with summaries and token counts. |

The LLM decides WHEN to call tools based on conversation context. The tools decide IF the action is valid (e.g., rejecting `open_effort` when one is already open). This separates intent detection (LLM) from state management (code).

---

## Slice 1 Boundaries

**In this scenario (Slice 1)**:
- One effort at a time (must close before opening another)
- All messages go to effort log when effort is open
- No ambient interruption routing
- Tool-based effort management (LLM calls tools, no commands)

**Future slices will add**:
- Multiple simultaneous open efforts with switching (Slice 2)
- Expansion on demand — recall concluded effort details (Slice 2)
- Salience decay — expanded context fades naturally (Slice 3)
- Working context limits (Slice 4)

---

## Related Documents

- [01-core-compaction-proof.md](../../../docs/slices/01-core-compaction-proof.md) — Slice 1 spec
- [whitepaper.md](../../../docs/whitepaper.md) — CCM whitepaper
- [publication-strategy.md](../../../docs/publication-strategy.md) — Why this exists
