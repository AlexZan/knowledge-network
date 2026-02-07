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

**State after Turn 2:**
```
raw.jsonl: turns 1-2 (~40 tokens)
manifest.yaml: empty
efforts/: empty
───────────────────────────────
CONTEXT: ~40 tokens
```

---

### Turn 3: Open Effort

```
TURN 3 - Alex:
"Let's debug the auth bug - users are getting 401s after about an hour"

TURN 4 - Assistant:
"Opening effort: auth-bug

That timing suggests token expiration. A few questions:
1. What's your access token TTL?
2. Are you using refresh tokens?"
```

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

**State after Turn 10:**
```
raw.jsonl: turns 1-2 (~40 tokens)
manifest.yaml: { efforts: [{ id: auth-bug, status: open }] }
efforts/auth-bug.jsonl: turns 3-10 (~600 tokens)
───────────────────────────────
CONTEXT: 40 + 10 + 600 = ~650 tokens
```

---

### Turn 11: Ambient Interruption

```
TURN 11 - Alex:
"Quick question - what's the weather in Seattle?"

TURN 12 - Assistant:
"72°F and sunny in Seattle today."
```

**State after Turn 12:**
```
raw.jsonl: turns 1-2, 11-12 (~80 tokens)  ← ambient grew
manifest.yaml: { efforts: [{ id: auth-bug, status: open }] }
efforts/auth-bug.jsonl: turns 3-10 (~600 tokens)  ← unchanged
───────────────────────────────
CONTEXT: 80 + 10 + 600 = ~690 tokens
```

---

### Turn 13: Conclude Effort

```
TURN 13 - Alex:
"Back to auth - I implemented the interceptor and it works. Bug is fixed!"

TURN 14 - Assistant:
"Concluding effort: auth-bug

Summary: Debugged 401 errors occurring after 1 hour. Root cause was refresh
tokens existing but never being called automatically. Fixed by adding axios
interceptor in tokenService.ts that proactively refreshes tokens before expiry.

Effort concluded and summarized. Context freed up."
```

**State after Turn 14:**
```
raw.jsonl: turns 1-2, 11-12 (~80 tokens)
manifest.yaml:
  efforts:
    - id: auth-bug
      status: concluded
      summary: "Debugged 401 errors after 1 hour. Root cause: refresh tokens
               never auto-called. Fix: axios interceptor for proactive refresh."
      raw_file: efforts/auth-bug.jsonl
efforts/auth-bug.jsonl: turns 3-10, 13-14 (~700 tokens) ← STILL EXISTS but NOT IN CONTEXT
───────────────────────────────
CONTEXT: 80 + 60 = ~140 tokens  ← DROPPED from 690!
```

**Token savings: 690 → 140 = 80% reduction**

---

### Turn 15: Open New Effort

```
TURN 15 - Alex:
"Now let's work on the guild feature - I want to add a member limit"

TURN 16 - Assistant:
"Opening effort: guild-feature

For member limits, a few questions:
1. What's the max you're thinking?
2. Should it be configurable per guild or global?"
```

**State after Turn 16:**
```
raw.jsonl: turns 1-2, 11-12 (~80 tokens)
manifest.yaml:
  efforts:
    - id: auth-bug, status: concluded, summary: "..."
    - id: guild-feature, status: open
efforts/auth-bug.jsonl: (~700 tokens) ← NOT in context
efforts/guild-feature.jsonl: turns 15-16 (~60 tokens) ← IN context
───────────────────────────────
CONTEXT: 80 + 60 + 60 = ~200 tokens
```

---

## Context Size Through Session

| Point | Context Size | What Changed |
|-------|--------------|--------------|
| After ambient (turn 2) | ~40 tokens | Just chatter |
| After opening auth-bug (turn 4) | ~130 tokens | +effort overhead |
| After working on auth-bug (turn 10) | ~650 tokens | Effort grew |
| After ambient interruption (turn 12) | ~690 tokens | Ambient grew |
| **After concluding auth-bug (turn 14)** | **~140 tokens** | **-550 tokens!** |
| After opening guild-feature (turn 16) | ~200 tokens | New effort |

---

## What This Proves

1. **Efforts isolate context** - auth-bug work doesn't pollute ambient
2. **Open efforts = full raw** - Complete context while working
3. **Concluded efforts = summary only** - Massive token savings
4. **Context is predictable** - Always: ambient + manifest + open efforts
5. **Natural pressure** - Big efforts incentivize concluding before opening more

---

## File Structure After Session

```
session/
├── raw.jsonl                    # 80 tokens (ambient only)
├── manifest.yaml                # 60 tokens (auth-bug summary + guild-feature entry)
└── efforts/
    ├── auth-bug.jsonl           # 700 tokens (preserved, not in context)
    └── guild-feature.jsonl      # 60 tokens (in context, effort is open)
```

---

## Later: Referencing Concluded Effort

```
TURN 20 - Alex:
"Wait, what was the exact interceptor code we used for auth?"

TURN 21 - Assistant:
"From the auth-bug effort summary, you added an axios interceptor.
Let me pull the exact code from the raw log...

[EXPANSION: reads efforts/auth-bug.jsonl, turns 7-8]

Here's the code:
[shows exact interceptor code from turn 8]"
```

**Expansion is on-demand** - only when detail needed, only the specific effort.

---

## Implementation Notes

For MVP:
- User explicitly opens efforts: "Let's work on X"
- User explicitly concludes: "X is done" / "looks good"
- Ambient = anything not during an open effort
- AI summarizes on conclusion

Slice 2+ will add:
- Smart effort detection (AI recognizes "let's debug..." as effort start)
- Smart conclusion triggers (AI recognizes "looks good" as conclusion)
- Ambient summarization (when raw.jsonl gets too big)

---

## Related Documents

- [01-two-log-proof.md](../../slices/01-two-log-proof.md) - Slice definition
- [whitepaper.md](../../whitepaper.md) - Full vision
