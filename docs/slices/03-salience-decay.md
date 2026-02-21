# Slice 3: Salience Decay

**Goal**: Prove that expanded context is self-managing — temporarily loaded information fades automatically when no longer referenced, without explicit user action.

**Purpose**: Generate proof data for the CCM whitepaper — "context manages itself; users don't need to manually clean up expanded efforts."

---

## Core Hypothesis

> Expanded efforts should auto-collapse when the user stops referencing them. This eliminates manual context management — the system adapts to the user's focus without intervention.

---

## What Slices 1-2 Proved

- Open effort = full raw context, concluded = summary only (~80-94% savings)
- Compaction is lossless — expand restores full context, collapse returns to baseline
- Multiple efforts coexist with clean switching
- LLM correctly detects when to open/close/expand/collapse from natural language

## What Slice 2 Left Manual

In Slice 2, expanded efforts stay expanded until the LLM calls `collapse_effort`. This works but has problems:

| Problem | Example |
|---------|---------|
| LLM forgets to collapse | User asks about auth-bug, gets answer, moves to new topic — auth-bug raw stays in context |
| Context bloat | User expands 3 efforts to compare, only actively using 1 — other 2 waste tokens |
| User burden | Power users would need to say "collapse that" or rely on LLM to proactively collapse |

Salience decay solves all three: expanded efforts auto-collapse after N turns without reference.

---

## Architecture

### Decay Mechanism

Each expanded effort tracks `last_referenced_turn`. Every turn, the orchestrator checks:

```
for each expanded effort:
    turns_since_reference = current_turn - last_referenced_turn
    if turns_since_reference >= DECAY_THRESHOLD:
        auto-collapse this effort
```

**DECAY_THRESHOLD**: Start with 3 turns. This means if the user has 3 exchanges without mentioning the expanded effort's topic, it auto-collapses.

### What Counts as a "Reference"?

A reference is any mention of the expanded effort's content in the user's message OR the assistant's response. Detection approaches (from simplest to most robust):

| Approach | How | Pros | Cons |
|----------|-----|------|------|
| **Effort ID match** | Check if effort ID appears in user/assistant message | Simple, fast, no LLM | Misses indirect references |
| **Keyword match** | Extract keywords from effort's raw log, check message overlap | Catches indirect references | May false-positive on common words |
| **LLM classification** | Ask LLM "does this message reference effort X?" | Most accurate | Costs tokens every turn |

**Recommendation**: Start with effort ID match + keyword extraction from the effort summary (not full raw log). Summary keywords are high-signal. If a message mentions "auth", "401", "token", or "refresh" and auth-bug is expanded, it's referenced. Cheap, fast, good enough.

### Updated `expanded.json`

```json
{
  "expanded": ["auth-bug", "perf-fix"],
  "expanded_at": {
    "auth-bug": "2026-02-15T18:00:00",
    "perf-fix": "2026-02-15T18:05:00"
  },
  "last_referenced_turn": {
    "auth-bug": 14,
    "perf-fix": 12
  }
}
```

New field: `last_referenced_turn` — the turn number when this effort was last referenced.

### Turn Counter

The session needs a turn counter. Options:

| Option | Storage | Pros | Cons |
|--------|---------|------|------|
| Count lines in raw.jsonl + effort logs | Derived | No new state | Expensive on large sessions |
| Field in manifest.yaml | Persistent | Simple | Manifest already has other roles |
| Field in expanded.json | Co-located | Near decay logic | Only exists when something is expanded |
| Separate `session_state.json` | Dedicated | Clean separation | Another file |

**Recommendation**: `session_state.json` — clean, extensible, will be useful for Slice 4 (bounded context) too.

```json
{
  "turn_count": 14,
  "updated": "2026-02-15T18:10:00"
}
```

---

## Decay Flow

```
Turn N: User asks about auth-bug details
  → LLM calls expand_effort("auth-bug")
  → last_referenced_turn["auth-bug"] = N

Turn N+1: User asks follow-up about auth-bug
  → Reference detected (keyword match)
  → last_referenced_turn["auth-bug"] = N+1

Turn N+2: User changes topic to something unrelated
  → No reference detected
  → auth-bug: 1 turn without reference

Turn N+3: User continues unrelated topic
  → No reference detected
  → auth-bug: 2 turns without reference

Turn N+4: User continues unrelated topic
  → No reference detected
  → auth-bug: 3 turns without reference → DECAY_THRESHOLD reached
  → Auto-collapse auth-bug
  → Banner: "--- Auto-collapsed effort: auth-bug (inactive for 3 turns) ---"
```

### Decay Banner

Auto-collapse produces a distinct banner so the user knows what happened:

```
--- Auto-collapsed effort: auth-bug (inactive for 3 turns) ---
```

Different from manual collapse banner (`"--- Collapsed effort: auth-bug (back to summary) ---"`).

### Re-expansion

If the user asks about a decayed effort again, the LLM just calls `expand_effort` again. Decay is not punishment — it's cleanup. The effort is still there, still expandable.

---

## Reference Detection

### Keyword Extraction

On expand, extract salient keywords from the effort's summary (not raw log — summary is small and high-signal):

```python
def extract_keywords(summary: str) -> set[str]:
    """Extract salient keywords from effort summary for reference detection."""
    # Simple approach: split, lowercase, filter stopwords, keep 3+ char words
    # Could use TF-IDF or LLM extraction later
    stopwords = {"the", "a", "an", "is", "was", "were", "been", ...}
    words = set()
    for word in summary.lower().split():
        word = word.strip(".,;:!?\"'()-")
        if len(word) >= 3 and word not in stopwords:
            words.add(word)
    return words
```

### Reference Check

```python
def is_referenced(message: str, effort_id: str, keywords: set[str]) -> bool:
    """Check if a message references an expanded effort."""
    msg_lower = message.lower()

    # Direct ID mention
    if effort_id.replace("-", " ") in msg_lower or effort_id in msg_lower:
        return True

    # Keyword overlap (require 2+ matches to avoid false positives)
    msg_words = set(msg_lower.split())
    overlap = keywords & msg_words
    return len(overlap) >= 2
```

### What Messages to Check

Check both user message and assistant response each turn. If either references the expanded effort, it's still salient.

---

## Working Context (updated)

No change to context structure — decay only affects *when* expanded efforts are removed, not *how* they appear in context.

```
Working Context = system_prompt
               + ambient
               + manifest_summaries (concluded, non-expanded)
               + expanded_effort_raw (concluded but temporarily loaded)  ← auto-removed by decay
               + non-active_open_effort_raw
               + active_effort_raw
```

---

## Orchestrator Changes

### Per-Turn Decay Check

After processing a turn (user message + assistant response), before returning:

1. Increment turn counter
2. For each expanded effort:
   a. Check if user message or assistant response references it
   b. If yes: update `last_referenced_turn`
   c. If no: check if `current_turn - last_referenced_turn >= DECAY_THRESHOLD`
   d. If threshold reached: auto-collapse, emit banner
3. Save updated state

### Process Turn Flow (updated)

```
process_turn(session_dir, user_message):
    1. Increment turn counter
    2. Build working context (existing)
    3. Send to LLM, handle tool calls (existing)
    4. Log messages (existing)
    5. [NEW] Check decay for all expanded efforts
    6. Return response (+ any decay banners appended)
```

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `DECAY_THRESHOLD` | 3 | Turns without reference before auto-collapse |
| `MIN_KEYWORD_OVERLAP` | 2 | Keyword matches needed to count as reference |

Stored as constants initially. Slice 4 may make these configurable per-session.

---

## Metrics

Track and report for the whitepaper:

| Metric | What | Why |
|--------|------|-----|
| `auto_collapses` | Count of auto-collapse events | Proves decay is happening |
| `avg_expansion_duration` | Average turns an expansion stays active | Shows typical usage pattern |
| `manual_vs_auto_collapse` | Ratio of explicit collapse_effort calls vs decay | Shows how much manual work decay eliminates |
| `false_decay_rate` | Times user re-expands within 2 turns of auto-collapse | Measures if threshold is too aggressive |
| `tokens_saved_by_decay` | Tokens that would have stayed in context without decay | Proves decay value |

---

## Testing Strategy

| What | How | LLM needed? |
|------|-----|-------------|
| Turn counter increments correctly | Unit test | No |
| Keyword extraction from summary | Unit test | No |
| Reference detection (ID match) | Unit test | No |
| Reference detection (keyword match) | Unit test | No |
| Auto-collapse after N turns without reference | Unit test | No |
| Reference resets decay counter | Unit test | No |
| Decay banner generated correctly | Unit test | No |
| Re-expansion after decay works | Unit test | No |
| Multiple expanded efforts decay independently | Unit test | No |
| Decay doesn't affect open efforts (only expanded) | Unit test | No |
| LLM re-expands after decay when user asks again | Integration test | Yes |
| Full cycle: expand → reference → stop referencing → decay | Proof run | No (mocked) |
| Decay metrics collection | Unit test | No |

---

## Proof Run (Scripted)

| Step | Action | Expanded | Context Tokens | Decay Counter |
|------|--------|----------|---------------|---------------|
| Setup | 2 concluded efforts + ambient | none | ~180 | — |
| Turn 1 | Expand auth-bug | auth-bug | ~780 | auth-bug: 0 |
| Turn 2 | Ask about auth-bug (referenced) | auth-bug | ~860 | auth-bug: 0 (reset) |
| Turn 3 | Ask unrelated question | auth-bug | ~940 | auth-bug: 1 |
| Turn 4 | Another unrelated exchange | auth-bug | ~1020 | auth-bug: 2 |
| Turn 5 | Another unrelated exchange | auth-bug | ~1100 | auth-bug: 3 → **AUTO-COLLAPSE** |
| Turn 6 | Continue (auth-bug gone) | none | ~580 | — |
| Turn 7 | Ask about auth-bug again | auth-bug | ~1180 | auth-bug: 0 (re-expanded) |

**Key metrics**:
- Auto-collapse fires at exactly DECAY_THRESHOLD turns
- Reference resets the counter
- Re-expansion works seamlessly after decay
- Tokens freed = raw log size of decayed effort

---

## Scope

### In Scope

- Turn counter (`session_state.json`)
- Reference detection (effort ID match + keyword overlap from summary)
- Auto-collapse after DECAY_THRESHOLD turns without reference
- Decay banner (`"--- Auto-collapsed effort: X (inactive for N turns) ---"`)
- Updated `expanded.json` with `last_referenced_turn`
- Decay metrics tracking
- Proof run: expand → reference → stop → decay → re-expand cycle

### Out of Scope (Later Slices)

| Feature | Slice | Why Deferred |
|---------|-------|--------------|
| LLM-based reference detection | 4+ | Keyword match is good enough; LLM adds cost per turn |
| Configurable decay threshold per effort | 4+ | Single threshold is fine for proof |
| Working context token budget | 4 | Decay reduces context but doesn't enforce a cap |
| Cross-session turn counting | 4+ | Single session is sufficient for proof |
| Decay of open efforts (background aging) | 4 | Only expanded efforts decay for now |

---

## Success Criteria

- [ ] Turn counter tracks conversation progress
- [ ] Keyword extraction produces reasonable keywords from effort summaries
- [ ] Reference detection catches direct ID mentions
- [ ] Reference detection catches indirect keyword mentions (2+ overlap)
- [ ] Expanded effort auto-collapses after DECAY_THRESHOLD turns without reference
- [ ] Reference resets the decay counter
- [ ] Auto-collapse produces distinct banner
- [ ] Re-expansion after decay works (effort is still concluded, still expandable)
- [ ] Multiple expanded efforts decay independently
- [ ] Decay does not affect open efforts
- [ ] Proof run demonstrates full decay cycle with measurements
- [ ] Decay metrics show tokens saved vs always-expanded baseline

---

## Related Documents

- [Slice 1 spec](01-core-compaction-proof.md) — Core compaction
- [Slice 2 spec](02-expansion-multi-effort.md) — Expansion & multi-effort (foundation for decay)
- [Slices README](README.md) — Roadmap overview
- [Whitepaper](../whitepaper.md) — CCM whitepaper draft
