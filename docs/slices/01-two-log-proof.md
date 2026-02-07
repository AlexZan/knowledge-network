# Slice 1: Two-Log Proof of Concept

**Goal**: Prove that effort-based context management works—open efforts stay in context (raw), concluded efforts become summaries.

**Dependencies**: None (foundational slice)

**Builds toward**: Smart effort detection, ambient summarization, working context limits

---

## Core Hypothesis

> Open efforts need full context (raw). Concluded efforts only need summaries. This achieves significant token reduction while maintaining full access to active work.

---

## The Model

```
session/
├── raw.jsonl              # Ambient: everything NOT in an effort
├── manifest.yaml          # Summaries of concluded efforts
└── efforts/
    ├── auth-bug.jsonl     # Effort raw log (open or concluded)
    └── guild-feature.jsonl
```

---

## Context Each Turn

```
Context = raw.jsonl + manifest + Σ(open efforts' raw logs)
```

| Component | What it contains | When loaded |
|-----------|------------------|-------------|
| raw.jsonl | Non-effort exchanges | Always |
| manifest.yaml | Concluded effort summaries | Always |
| efforts/*.jsonl | Effort raw dialogue | Only if effort is OPEN |

---

## Effort Lifecycle

```
User: "Let's debug the auth bug"     → CREATE efforts/auth-bug.jsonl
[exchanges about auth bug]           → APPEND to auth-bug.jsonl
User: "Auth bug is fixed, looks good" → CONCLUDE:
                                         1. Summarize to manifest
                                         2. Mark auth-bug as concluded
                                         3. Remove from context
```

---

## Scope

### In Scope

- **Ambient capture**: Non-effort exchanges append to `raw.jsonl`
- **Effort creation**: User says "let's work on X" → create effort log
- **Effort capture**: Effort exchanges append to effort's raw log
- **Effort conclusion**: User signals done → summarize to manifest
- **Context assembly**: raw.jsonl + manifest + open efforts' raw logs
- **Token measurement**: Compare context size with/without effort management

### Out of Scope (Later Slices)

| Feature | Why Deferred |
|---------|--------------|
| Automatic effort detection | User explicitly opens/closes for MVP |
| Ambient summarization | raw.jsonl can grow for now |
| Smart conclusion triggers | User explicitly concludes for MVP |
| Session boundaries | What's a "session"? Defer this question |
| Working context limits (~4) | No cap on open efforts for MVP |

---

## Data Structures

### Ambient Raw Log (`raw.jsonl`)

```jsonl
{"turn": 1, "role": "user", "content": "Hey, how's it going?", "ts": "..."}
{"turn": 2, "role": "assistant", "content": "Good! What can I help with?", "ts": "..."}
{"turn": 5, "role": "user", "content": "What's the weather?", "ts": "..."}
{"turn": 6, "role": "assistant", "content": "It's 72°F and sunny.", "ts": "..."}
```

Non-effort chatter. Stays in context. May grow (that's fine for MVP).

### Effort Raw Log (`efforts/auth-bug.jsonl`)

```jsonl
{"turn": 3, "role": "user", "content": "Let's debug the auth bug", "ts": "..."}
{"turn": 4, "role": "assistant", "content": "Sure, what's happening?", "ts": "..."}
{"turn": 7, "role": "user", "content": "Users get 401 after an hour", "ts": "..."}
...
{"turn": 15, "role": "user", "content": "That fixed it, looks good", "ts": "..."}
```

### Manifest (`manifest.yaml`)

```yaml
efforts:
  - id: auth-bug
    status: concluded
    summary: "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: added axios interceptor for proactive refresh."
    raw_file: efforts/auth-bug.jsonl
    turns: [3, 4, 7-15]

  - id: guild-feature
    status: open
    summary: null  # No summary yet, still open
    raw_file: efforts/guild-feature.jsonl
    turns: [16-22]
```

---

## The Test

### Setup

1. Start a session
2. Have some ambient chatter (not efforts)
3. Explicitly open an effort: "Let's work on X"
4. Work on X for several turns
5. Conclude X: "X looks good"
6. Open another effort Y
7. Measure context at each stage

### Expected Context Sizes

| Stage | Context |
|-------|---------|
| After ambient chatter | raw.jsonl (~100 tokens) |
| After opening effort X | raw + X.jsonl (~100 + 0) |
| After working on X | raw + X.jsonl (~100 + 500) |
| After concluding X | raw + manifest (~100 + 50) |
| After opening Y | raw + manifest + Y.jsonl (~100 + 50 + 0) |

**Key**: Concluding X drops ~500 tokens of raw, adds ~50 tokens of summary = **90% reduction for that effort**

---

## Success Criteria

- [ ] Ambient exchanges captured to raw.jsonl
- [ ] User can explicitly open an effort
- [ ] Effort exchanges captured to effort's raw log
- [ ] User can explicitly conclude an effort
- [ ] Concluded effort summarized to manifest
- [ ] Concluded effort's raw log removed from context
- [ ] Context = raw + manifest + open efforts' raw logs
- [ ] Measurable token savings when efforts conclude

---

## Implementation Steps

1. **Define data structures** - raw.jsonl, manifest.yaml, efforts/*.jsonl
2. **Build router** - Detect if exchange is ambient or belongs to open effort
3. **Build effort commands** - "open effort X", "conclude effort X"
4. **Build summarizer** - On conclude, summarize effort to manifest
5. **Build context assembler** - Combine raw + manifest + open efforts
6. **Run tests** - Validate context changes through effort lifecycle
7. **Measure** - Document token savings

---

## What Success Unlocks

Slice 1 proves:
- Effort-based context management works
- Concluded = summary only (token savings)
- Open = full raw (complete context)

Then we can layer on:
- **Slice 2**: Smart effort detection + conclusion triggers
- **Slice 3**: Ambient summarization (when raw.jsonl gets big)
- **Slice 4**: Working context limits (~4 open efforts)
- **Slice 5+**: Cross-session persistence, knowledge network

---

## Related Documents

- [two-log-proof-scenario.md](../scenarios/slice-1/two-log-proof-scenario.md) - Walkthrough scenario
- [whitepaper.md](../whitepaper.md) - Full vision
- [memory-consolidation-research.md](../research/memory-consolidation-research.md) - Neuroscience foundation
