# Slice 2: Expansion & Multi-Effort

**Goal**: Prove that concluded effort details are recallable on demand (nothing is truly lost) and that multiple efforts can coexist with clean switching.

**Purpose**: Generate proof data for the CCM whitepaper — "compaction is lossless because expansion restores full context when needed."

---

## Core Hypothesis

> Concluded efforts appear compact in working context (summary only), but their full raw log can be temporarily expanded back into context on demand. This proves compaction is lossless — nothing is forgotten, just compressed.

---

## What Slice 1 Proved

- Open effort = full raw context, concluded = summary only
- ~80-94% token savings on conclusion
- Programmatic banners for tool transparency
- Close guardrails (only on explicit completion)

## What Slice 2 Adds

| Feature | Why It Matters |
|---------|---------------|
| `expand_effort(id)` | Proves compaction is lossless — full context recoverable |
| `collapse_effort(id)` | Proves expansion is temporary — context returns to compact |
| Multi-effort support | Removes "one at a time" constraint from Slice 1 |
| `switch_effort(id)` | Clean switching between open efforts |
| Expansion token tracking | Measures cost of recall vs keeping everything in context |

---

## Architecture

### New Tools

| Tool | Args | Effect |
|------|------|--------|
| `expand_effort(id)` | concluded effort id | Load concluded effort's raw log into working context temporarily. Adds "expanded" layer. |
| `collapse_effort(id)` | expanded effort id | Remove expanded effort's raw log from working context. Back to summary only. |
| `switch_effort(id)` | open effort id | Change which open effort is "active" (receiving new messages). |

### Modified Tools

| Tool | Change |
|------|--------|
| `open_effort(name)` | Remove "fails if one already open" constraint. Multiple efforts can be open. |
| `close_effort(id)` | Add optional `id` param. If omitted, closes the active effort. |
| `effort_status()` | Show expanded efforts, active effort indicator, expansion token cost. |

### Working Context (updated)

```
Working Context = system_prompt
               + ambient
               + manifest_summaries (concluded, non-expanded)
               + expanded_effort_raw (concluded but temporarily loaded)
               + active_effort_raw (the one receiving new messages)
```

| Layer | Source | When included |
|-------|--------|---------------|
| **Permanent** | System prompt | Always |
| **Permanent** | Ambient (`raw.jsonl`) | Always |
| **Permanent** | Manifest summaries (concluded, non-expanded) | Always |
| **Transient** | Expanded effort raw logs | Only while expanded |
| **Active** | Active open effort raw log | Only if an effort is active |

---

## Effort States

```
          open_effort()          close_effort()
              ↓                       ↓
  [none] → [open] ────────────→ [concluded]
              ↑                    ↓     ↑
              │           expand_effort() │
              │                  ↓        │
              │             [expanded] ───┘
              │                  │   collapse_effort()
              │                  │
              └──────────────────┘
                 (expanded efforts can't be re-opened,
                  only viewed then collapsed)
```

Slice 1 states: `open`, `concluded`
Slice 2 adds: `expanded` (transient view state — effort is still concluded, just temporarily loaded)

**Implementation note**: `expanded` is NOT a manifest status. The manifest stays `concluded`. Expansion state is tracked in a separate runtime structure (e.g. `session/expanded.json` or in-memory set) so that restarts don't preserve stale expansions.

---

## Multi-Effort Model

### Active Effort

With multiple open efforts, one is **active** — it receives new messages. The rest are open but "backgrounded" (their raw logs are still in context but new messages don't append to them).

```yaml
# manifest.yaml
efforts:
  - id: auth-bug
    status: open
    active: true      # ← new field
  - id: guild-feature
    status: open
    active: false     # open but backgrounded
  - id: old-work
    status: concluded
    summary: "..."
```

### Switching

`switch_effort(id)` changes which effort is active. Both efforts' raw logs stay in context — switching just changes where new messages are appended.

### Message Routing

| Scenario | Messages go to |
|----------|---------------|
| One effort open (active) | That effort's log |
| Multiple efforts open, one active | Active effort's log |
| No effort open | Ambient (`raw.jsonl`) |

---

## Expansion Flow

```
User: "What exactly did we do for the auth bug?"
  → LLM calls expand_effort("auth-bug")
  → Tool loads auth-bug.jsonl into working context
  → Banner: "--- Expanded effort: auth-bug (423 tokens loaded) ---"
  → LLM now has full raw log and can answer detailed questions

User: "Got it, thanks"
  → LLM calls collapse_effort("auth-bug")
  → Tool removes auth-bug.jsonl from working context
  → Banner: "--- Collapsed effort: auth-bug (back to summary) ---"
  → Context returns to compact form
```

### Expansion Rules

- Only concluded efforts can be expanded (open efforts are already in context)
- Multiple efforts can be expanded simultaneously
- Expansion is temporary — lasts until explicitly collapsed or (Slice 3) decays
- Expanded effort raw logs appear in context AFTER ambient but BEFORE active effort
- Expansion token cost is tracked and reported

---

## File Structure (additions)

```
session/
├── raw.jsonl              # Ambient (unchanged)
├── manifest.yaml          # Effort metadata (adds: active field)
├── expanded.json          # Currently expanded effort IDs (runtime state)
└── efforts/
    └── {effort-id}.jsonl  # Effort raw logs (unchanged)
```

### `expanded.json`

```json
{
  "expanded": ["auth-bug"],
  "expanded_at": {"auth-bug": "2026-02-15T18:00:00"}
}
```

Simple file. Cleared on session restart (expansions are transient by design).

---

## Token Measurement

Track and report:

| Metric | What |
|--------|------|
| `context_tokens` | Total working context tokens this turn |
| `expansion_tokens` | Tokens added by expanded efforts |
| `expansion_overhead` | `expansion_tokens / context_tokens` — cost of recall |
| `savings_vs_naive` | Tokens saved vs keeping all effort raw logs in context always |

### The Proof

```
Turn 1:  context: 150 tokens  (ambient + 2 concluded summaries)
Turn 2:  expand auth-bug → context: 750 tokens  (+600 raw log)
Turn 3:  answer question from expanded context
Turn 4:  collapse auth-bug → context: 150 tokens  (back to compact)
```

**Key metric**: Expansion is on-demand. Without expansion, context stays at 150. With naive approach (keep everything), context would be 750+ permanently. CCM gives you 150 most of the time, 750 only when you need it.

---

## System Prompt Additions

```
### expand_effort
Call when the user asks about details of a concluded effort that the
summary alone can't answer. Loads the full conversation back temporarily.

### collapse_effort
Call when the user is done reviewing an expanded effort.
Also call proactively if the user moves on to a different topic.

### switch_effort
Call when the user wants to work on a different open effort.
```

---

## Testing Strategy

| What | How | LLM needed? |
|------|-----|-------------|
| expand_effort loads raw log into context | Unit test | No |
| collapse_effort removes raw log from context | Unit test | No |
| Expanded effort appears in _build_messages | Unit test | No |
| Multiple open efforts in manifest | Unit test | No |
| switch_effort changes active effort | Unit test | No |
| Message routing to active effort | Unit test | No |
| expand + answer + collapse preserves info | Integration test | Yes |
| LLM expands when user asks detailed question | E2e test | Yes |
| Multi-effort switching works naturally | E2e test | Yes |
| Token measurement: expansion overhead | Unit test | No |

---

## Proof Run (Scripted)

| Step | Action | Context Tokens | Delta |
|------|--------|---------------|-------|
| Setup | 2 concluded efforts (auth-bug, perf-fix) + ambient | ~180 | — |
| Turn 1 | User asks about auth-bug detail | ~180 | — |
| Turn 2 | LLM expands auth-bug | ~780 | +600 |
| Turn 3 | User asks specific question, LLM answers from raw | ~780 | — |
| Turn 4 | LLM collapses auth-bug | ~180 | **-600** |
| Turn 5 | Open new effort "guild-feature" | ~250 | +70 |
| Turn 6 | Open second effort "api-refactor" | ~320 | +70 |
| Turn 7 | Switch to guild-feature | ~320 | 0 |
| Turn 8 | Message logged to guild-feature (active) | ~400 | +80 |

**Key metrics**:
- Expansion adds exact raw log size, collapse removes it completely
- Multiple open efforts coexist without interference
- Active effort receives messages, backgrounded effort doesn't

---

## Scope

### In Scope

- `expand_effort(id)` — load concluded effort raw log into context
- `collapse_effort(id)` — remove expanded effort from context
- `switch_effort(id)` — change active effort
- Multiple simultaneous open efforts
- Active effort tracking (which one receives messages)
- `expanded.json` runtime state file
- Expansion token tracking and reporting
- Programmatic banners for expand/collapse/switch
- Updated system prompt with expansion/switching guidance
- Proof run: expand → query → collapse cycle with measurements

### Out of Scope (Later Slices)

| Feature | Slice | Why Deferred |
|---------|-------|--------------|
| Auto-collapse after N turns (salience decay) | 3 | Depends on turn tracking |
| Working context limit (~4 items) | 4 | No cap needed yet |
| Cross-session persistence of expansions | 4+ | Expansions are transient |
| Interruption detection (ambient during effort) | 3 | Routing is simple enough for now |

---

## Success Criteria

- [ ] Concluded effort expandable back to full raw context
- [ ] Expanded effort collapsible back to summary only
- [ ] Expansion/collapse cycle preserves zero information loss
- [ ] Multiple efforts can be open simultaneously
- [ ] Active effort receives new messages, others don't
- [ ] switch_effort changes active without data loss
- [ ] Token measurement shows expansion is on-demand (not permanent)
- [ ] Proof run demonstrates: compact → expand → answer → collapse cycle
- [ ] LLM naturally expands when user asks detailed questions about concluded efforts

---

## Related Documents

- [Slice 1 spec](01-core-compaction-proof.md) — Foundation this builds on
- [Slices README](README.md) — Roadmap overview
- [Whitepaper](../whitepaper.md) — CCM whitepaper draft
