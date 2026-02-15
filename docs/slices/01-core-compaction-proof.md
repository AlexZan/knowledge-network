# Slice 1: Core Compaction Proof

**Goal**: Prove that effort-based context management works — open efforts stay in context (raw), concluded efforts become summaries, with measurable token savings.

**Purpose**: Generate proof data for the CCM whitepaper.

---

## Core Hypothesis

> Open efforts need full context (raw). Concluded efforts only need summaries. This achieves significant token reduction while maintaining quality.

---

## Architecture

### Tool-Based Effort Management

The LLM manages efforts via tool calls, not text-parsed commands. Users speak naturally; the LLM decides when to call tools.

**Tools (LLM-callable)**:

| Tool | Args | Effect |
|------|------|--------|
| `open_effort(name)` | effort name/slug | Create effort log + manifest entry. Fails if one already open. |
| `close_effort()` | none | Summarize effort via LLM, update manifest, remove raw log from context. Fails if none open. |
| `effort_status()` | none | Return open/concluded efforts, summaries, token counts. |

**System prompt** (tool-usage guidance, not detection protocol):

```
You are a helpful AI assistant with effort management tools.

Use open_effort when the user wants to start focused work on a topic.
Use close_effort when the user indicates work is complete.
Use effort_status when the user asks about current efforts.

When an effort is open, stay focused on it. The user's messages relate
to the active effort unless they clearly indicate otherwise.

Do not open a new effort while one is already open.
```

**User interface**: Natural language. No commands to memorize.

---

## File Structure

```
session/
├── raw.jsonl              # Ambient messages (when no effort is open)
├── manifest.yaml          # Effort metadata + concluded summaries
└── efforts/
    └── {effort-id}.jsonl  # Effort raw log
```

---

## Data Formats

### Ambient Raw Log (`raw.jsonl`)

```jsonl
{"role": "user", "content": "Hey, how's it going?", "ts": "2026-01-01T10:00:00"}
{"role": "assistant", "content": "Good! What can I help with?", "ts": "2026-01-01T10:00:01"}
```

### Effort Raw Log (`efforts/{id}.jsonl`)

```jsonl
{"role": "user", "content": "The token expires after 1hr", "ts": "2026-01-01T10:05:00"}
{"role": "assistant", "content": "That's too short. Check the TTL config.", "ts": "2026-01-01T10:05:01"}
```

### Manifest (`manifest.yaml`)

```yaml
efforts:
  - id: auth-bug
    status: concluded
    summary: "Debugged 401 errors. Root cause: refresh tokens never auto-called. Fix: axios interceptor."
    raw_file: efforts/auth-bug.jsonl

  - id: guild-feature
    status: open
    summary: null
    raw_file: efforts/guild-feature.jsonl
```

---

## Working Context (assembled each turn)

```
Working Context = system_prompt + ambient + manifest_summaries + open_effort_raw
```

| Layer | Source | When included |
|-------|--------|---------------|
| **Permanent** | System prompt | Always |
| **Permanent** | Ambient (`raw.jsonl`) | Always |
| **Permanent** | Manifest summaries (concluded efforts) | Always |
| **Active** | Open effort raw log (`efforts/{id}.jsonl`) | Only if effort is open |
| **Transient** | Expansions (recall from concluded) | Slice 2+ |

---

## Effort Lifecycle

```
User: "Let's debug the auth bug"
  → LLM calls open_effort("auth-bug")
  → Tool creates efforts/auth-bug.jsonl, updates manifest
  → LLM responds naturally: "Got it. What error are you seeing?"

[exchanges about auth bug → appended to auth-bug.jsonl]

User: "That fixed it, looks good"
  → LLM calls close_effort()
  → Tool summarizes raw log (LLM call), writes summary to manifest
  → Tool marks effort as concluded
  → LLM responds: "Nice, I've summarized the auth bug work."
```

---

## Summarization (on close_effort)

Single LLM call with the effort's raw log:

```
Summarize this conversation into a concise paragraph.
Capture: what was worked on, key findings, resolution.
Keep it under 100 tokens.
```

Uses configurable model (same frontier model or cheaper). Summary stored in manifest.

---

## Token Measurement

Count tokens using tiktoken (cl100k_base). Log at each turn:

```
[turn 2]  context: 45 tokens  (ambient: 45, manifest: 0, effort: 0)
[turn 4]  context: 135 tokens (ambient: 45, manifest: 10, effort: 80)
[turn 10] context: 655 tokens (ambient: 45, manifest: 10, effort: 600)
[turn 14] context: 105 tokens (ambient: 45, manifest: 60, effort: 0)  ← COMPACTED
```

---

## The Proof Run

### Scripted version (repeatable, deterministic)

Mocked LLM responses. Produces the token measurement table.

| Step | Action | Expected Context | Delta |
|------|--------|-----------------|-------|
| Turns 1-2 | Ambient chat | ~40 tokens | — |
| Turn 3 | LLM calls `open_effort("auth-bug")` | ~130 tokens | +90 |
| Turns 5-10 | Work on effort | ~650 tokens | +520 |
| Turn 14 | LLM calls `close_effort()` | ~140 tokens | **-510** |
| Turn 15 | LLM calls `open_effort("guild-feature")` | ~200 tokens | +60 |

**Key metric**: 650 → 140 = **~80% token reduction** on effort conclusion.

### Live version (real LLM, end-to-end)

Real LLM (deepseek-chat). Verifies:
1. LLM correctly detects when to open/close efforts from natural language
2. Token measurements match predictions
3. Summary quality — ask about concluded effort, verify answer from summary alone

### Quality preservation test

After concluding auth-bug, ask: "What was the fix for the auth bug?"
- **With CCM**: LLM answers from manifest summary only (~60 tokens of context)
- **Baseline**: LLM answers from full raw log (~600 tokens of context)
- **Compare**: Are the answers equivalent? If yes, compaction preserved quality.

---

## Testing Strategy

| What | How | LLM needed? |
|------|-----|-------------|
| Tool functions (open/close/status) | Unit tests | No |
| Context assembly | Unit tests | No |
| Token measurement | Unit tests | No |
| File I/O (logs, manifest) | Unit tests | No |
| Summarization quality | Integration test | Yes |
| Intent detection (LLM calls right tool) | E2e test | Yes |
| Full proof run | E2e test | Yes |

---

## Scope

### In Scope

- Natural language effort management via LLM tool calls
- One effort open at a time
- Two-log separation (ambient vs effort)
- Effort conclusion with LLM-generated summary
- Context assembly (ambient + manifest + open effort)
- Token measurement at each turn
- Scripted proof run (deterministic measurements)
- Live proof run (real LLM, end-to-end)
- Quality preservation comparison test

### Out of Scope (Later Slices)

| Feature | Slice | Why Deferred |
|---------|-------|--------------|
| Multiple simultaneous open efforts | 2 | Needs routing mechanism |
| Expansion on demand (recall raw log) | 2 | Core claim doesn't need it |
| Salience decay (expanded context fades) | 3 | Depends on expansion |
| Working context limits (~4 items) | 4 | No cap needed for MVP |
| Interruption detection | 2 | One effort at a time avoids this |
| Working context cache file | 3 | Assembly is cheap for Slice 1 |
| Cross-session persistence | 4+ | Single session proof is sufficient |
| `/effort` commands (manual override) | 2+ | Nice-to-have for power users |

---

## Success Criteria

- [ ] LLM opens effort via tool call on natural language request
- [ ] LLM closes effort via tool call on natural language signal
- [ ] Effort exchanges captured to effort's raw log
- [ ] Ambient exchanges captured to raw.jsonl
- [ ] Concluded effort summarized to manifest
- [ ] Concluded effort's raw log removed from working context
- [ ] Working context = ambient + manifest summaries + open effort raw
- [ ] Token measurement shows ~80% reduction on effort conclusion
- [ ] Quality preservation test passes (summary answers match full-context answers)

---

## Related Documents

- [Publication strategy](../publication-strategy.md) — Why this slice exists
- [Whitepaper](../whitepaper.md) — CCM whitepaper draft
- [Brainstorm notes](../brainstorm/slice1-redesign-notes.md) — Design decisions
- [Scenario](../../efforts/chat-cli/scenarios/scenarios.md) — Conversation walkthrough (needs update)
