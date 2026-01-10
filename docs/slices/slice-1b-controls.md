# Slice 1b: Manual Controls & Polish

Add manual overrides and conclusion lifecycle management.

---

## Goal

Give users control over conclusions when automatic detection isn't enough.

---

## Prerequisites

- Slice 1a complete (automatic detection working)

---

## Features

### Commands

| Command | Action |
|---------|--------|
| `/conclude` | Force conclude current thread |
| `/reject <id>` | Mark a conclusion as wrong |
| `/expand <id>` | Show full thread for a conclusion |
| `/conclusions` | List all conclusions |
| `/stats` | Show token savings summary |
| `/help` | Show available commands |

### Conclusion Lifecycle

Conclusions can evolve:

```
Created ──→ Active ──→ Updated (append new info)
                   ──→ Corrected (was partially wrong)
                   ──→ Rejected (turned out to be wrong)
```

### Extended Data Structure

```
{
  id: string,
  content: string,
  status: "active" | "updated" | "rejected",
  source_thread_id: string,
  created: timestamp,
  updates: [
    { content: string, timestamp: string, type: "append" | "correct" }
  ]
}
```

---

## Use Cases

### Force Conclude

User wants to close a thread even though they haven't affirmed:

```
You: What about option B?
AI: Option B would work but has tradeoffs...
You: /conclude

[Conclusion extracted: "Option B viable with tradeoffs: ..."]
```

### Reject Conclusion

Previous conclusion was wrong:

```
You: /reject c001

[Conclusion c001 marked as rejected]
[Previously: "Auth bug caused by expired tokens"]
```

### Expand Thread

View full context that led to a conclusion:

```
You: /expand c001

--- Thread t001 (concluded) ---
[User]: How do I fix this auth bug?
[AI]: The issue is expired tokens...
[User]: Makes sense!
--- Conclusion: "Auth bug caused by expired tokens. Fix: refresh..." ---
```

---

## Success Criteria

1. [ ] `/conclude` forces conclusion extraction
2. [ ] `/reject` marks conclusion as rejected (excluded from context)
3. [ ] `/expand` shows full thread history
4. [ ] `/conclusions` lists all with status
5. [ ] `/stats` shows cumulative token savings
6. [ ] `/help` documents all commands
7. [ ] Rejected conclusions don't appear in context
