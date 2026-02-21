# Slice 5: Effort Reopening

**Goal**: Prove that concluded efforts can be reopened and extended, not just viewed. When a user returns to a past topic, the system finds the relevant concluded effort and offers to reopen it — or reopens it directly when the intent is unambiguous.

**Purpose**: Complete the effort lifecycle. Slices 1-4 treat conclusion as permanent. Real work isn't linear — users revisit, extend, and iterate. Reopening proves CCM handles non-linear workflows without losing history.

---

## Core Hypothesis

> Concluded efforts should be reopenable, not just viewable. When a user starts discussing a topic that matches a concluded effort, the system should surface that effort and let the user choose: reopen it (continue where they left off) or start fresh (new effort). The original raw log is preserved and extended, and the summary updates on re-conclusion.

---

## What Slices 1-4 Proved

| Slice | What | Status |
|-------|------|--------|
| 1 | Open effort = raw context, concluded = summary only (~80% savings) | Done |
| 2 | Expansion restores full context on demand, multi-effort switching | Done |
| 3 | Expanded efforts auto-collapse after 3 turns without reference | Done |
| 4 | Working memory stays bounded — summary eviction, ambient windowing, search | Planned |

## What's Missing

Currently a concluded effort can only be **viewed** (expand_effort loads raw log read-only). There's no way to:

- Reopen a concluded effort to add new messages
- Automatically detect that a new conversation relates to a past effort
- Let the user choose between reopening vs starting fresh

The `close_effort` tool description even says "permanently conclude" and "irreversible" — Slice 5 changes this.

---

## What Changes

### 1. `reopen_effort` Tool

New LLM-callable tool. Changes a concluded effort's status back to `open`, preserves the existing raw log, and sets it as active.

```
reopen_effort(id: str) -> JSON
```

**Mechanics**:
- Validates effort exists and status is `concluded`
- Flips status to `open`, sets `active: true`, deactivates other open efforts
- Preserves the existing raw log (new messages append to it)
- Removes from expanded set if it was expanded (it's now open, not expanded)
- Adds a separator line to the raw log: `{"role": "system", "content": "--- Effort reopened ---", "ts": "..."}`
- Returns `{status: "reopened", effort_id: "...", prior_summary: "..."}`

**When re-concluded**: `close_effort` summarizes the entire raw log (original + new messages). The summary replaces the old one.

### 2. LLM Behavior: When to Reopen vs Ask vs Open New

Three cases, handled via system prompt guidance:

**Case 1: Explicit reopen** — User clearly names a concluded effort:
- "Let's reopen the auth-bug effort"
- "I want to continue working on auth-bug"
- "Reopen auth-bug, I found another issue"

LLM action: Call `reopen_effort("auth-bug")` directly. No confirmation needed.

**Case 2: Ambiguous match** — User starts a topic that overlaps with a concluded effort, but doesn't name it explicitly:
- "I'm seeing 401 errors again" (matches concluded `auth-bug`)
- "We need to look at the database connections" (matches concluded `db-pool-fix`)

LLM action: Call `search_efforts(query)` (from Slice 4). If a match is found, ask the user:
> "I found a related concluded effort: **auth-bug** — 'Fixed 401 errors by adding axios interceptor for token refresh.' Want to reopen it, or start a new effort?"

Wait for user response before acting.

**Case 3: No match** — User starts a new topic with no concluded effort match:

LLM action: Call `open_effort(name)` as normal (existing behavior).

### 3. `search_efforts` Integration

Slice 4 introduces `search_efforts(query)` for finding evicted summaries. Slice 5 extends its use: the LLM calls it not just when a summary is missing from working memory, but also when detecting a potential overlap with a concluded effort before opening a new one.

The search uses the same keyword matching from `decay.py` (`extract_keywords` + `is_referenced`), applied to all concluded efforts.

### 4. Updated `close_effort` Description

Remove "permanently" and "irreversible" from the tool description. New wording:

```
"Conclude an effort. Summarizes the conversation and removes raw log from working context.
Concluded efforts can be reopened later with reopen_effort if the user returns to the topic.
Only call when the user explicitly says the work is DONE or COMPLETE."
```

### 5. Updated System Prompt

Add reopen guidance:

```
### reopen_effort
Call when the user wants to continue working on a concluded effort.
- If the user names a specific concluded effort: call reopen_effort directly
- If the user starts a topic similar to a concluded effort but doesn't name it:
  use search_efforts to find the match, then ASK the user if they want to
  reopen it or start a new effort. Only ask when ambiguous.

When reopening, the original conversation history is preserved. New messages
append to the existing log. When re-concluded, the summary covers everything.
```

---

## Updated Effort Lifecycle

Before (Slices 1-4):
```
open → [work] → concluded (permanent)
                     ↓
                expand (read-only view) → collapse
```

After (Slice 5):
```
open → [work] → concluded
                     ↓              ↑
                expand (view)    reopen (continue working)
                     ↓              ↑
                  collapse      [more work] → re-conclude
```

---

## Flow Examples

### Example 1: Explicit reopen

```
Turn 1-20:  User works on auth-bug, concludes it.
Turn 30:    User: "Let's reopen auth-bug, I found another edge case"
            LLM calls reopen_effort("auth-bug")
            → auth-bug status: open, active. Raw log preserved.
Turn 31-35: User works on the edge case.
Turn 36:    User: "Fixed, let's close it again."
            LLM calls close_effort()
            → Summary updated to cover original + new work.
```

### Example 2: Ambiguous match — LLM asks

```
Turn 1-15:  User works on db-pool-fix, concludes it.
            Summary: "Increased connection pool from 5 to 25, fixed exhaustion errors."
Turn 25:    User: "The database is running out of connections again"
            LLM calls search_efforts("database connections")
            → Match: db-pool-fix
            LLM: "I found a related concluded effort: db-pool-fix —
                  'Increased connection pool from 5 to 25...'
                  Want to reopen it, or start a new effort?"
Turn 26:    User: "Reopen it, same issue"
            LLM calls reopen_effort("db-pool-fix")
```

### Example 3: Ambiguous match — user wants new effort

```
Turn 25:    User: "We have a different database issue — query timeouts"
            LLM calls search_efforts("database query timeouts")
            → Match: db-pool-fix (partial keyword overlap)
            LLM: "I found a related concluded effort: db-pool-fix —
                  'Increased connection pool from 5 to 25...'
                  Want to reopen it, or start a new effort?"
Turn 26:    User: "No, this is different. New effort."
            LLM calls open_effort("query-timeouts")
```

### Example 4: No match — normal open

```
Turn 30:    User: "Let's plan my vacation to Japan"
            LLM calls search_efforts("vacation Japan") — or skips search (clearly unrelated)
            → No match
            LLM calls open_effort("japan-vacation")
```

---

## New Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "reopen_effort",
    "description": "Reopen a concluded effort to continue working on it. The original conversation history is preserved — new messages append to the existing log. Use when the user wants to return to a past topic. If the user names a specific effort, call directly. If ambiguous, use search_efforts first and ask the user.",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "The concluded effort ID to reopen."
        }
      },
      "required": ["id"]
    }
  }
}
```

---

## Implementation Changes

### `tools.py`

- Add `reopen_effort(session_dir, effort_id)` function:
  - Validate effort exists and status is `concluded`
  - Flip status to `open`, set `active: true`, deactivate others
  - Remove from expanded set if expanded
  - Append separator line to effort's JSONL
  - Return JSON with status, effort_id, prior_summary
- Add tool definition to `TOOL_DEFINITIONS`
- Update `execute_tool` dispatcher
- Update `close_effort` description (remove "permanently"/"irreversible")

### `orchestrator.py`

- Add `reopen_effort` to tool banner builder (`_build_tool_banners`):
  ```
  --- Reopened effort: auth-bug ---
  ```

### `prompts/system.md`

- Add `reopen_effort` section with the three-case guidance
- Update `close_effort` section to mention reopening is possible

### `state.py`

- No changes needed (manifest read/write already supports status changes)

### `decay.py`

- No changes needed (decay only applies to expanded efforts, not open ones)

---

## Testing Strategy

| What | How | LLM needed? |
|------|-----|-------------|
| Reopen concluded effort | Unit test | No |
| Reopen sets active, deactivates others | Unit test | No |
| Reopen preserves raw log | Unit test | No |
| Reopen non-concluded fails | Unit test | No |
| Reopen nonexistent fails | Unit test | No |
| Reopen removes from expanded set | Unit test | No |
| Separator line appended on reopen | Unit test | No |
| Re-conclude updates summary | Unit test (mock LLM) | No |
| Re-conclude covers full log | Unit test (mock LLM) | No |
| LLM reopens when user is explicit | e2e | Yes |
| LLM asks when match is ambiguous | e2e | Yes |
| LLM opens new when user declines reopen | e2e | Yes |
| Full cycle: open → conclude → reopen → work → re-conclude | Proof run | No (mocked) |

---

## Configuration

No new configuration values. Reopening uses existing tools and search mechanisms.

---

## Scope

### In Scope

- `reopen_effort` tool (status flip, raw log preservation, separator)
- System prompt guidance for explicit vs ambiguous reopen
- Integration with `search_efforts` (Slice 4) for ambiguous detection
- Updated `close_effort` description
- Re-conclusion with updated summary
- Tool banners for reopen

### Out of Scope (Later Slices)

| Feature | Why Deferred |
|---------|-------------|
| Merge two efforts | Different feature — combining separate efforts is more complex |
| Partial reopen (only some messages) | Unnecessary complexity — reopen means continue |
| Reopen history tracking (how many times reopened) | Nice-to-have, not needed for proof |
| Cross-session reopening | Slice 4 defers cross-session persistence |

---

## Dependency

```
Slice 4: Bounded Working Context (search_efforts tool)
    ↓
Slice 5: Effort Reopening (uses search_efforts for ambiguous detection)
```

Slice 5 depends on Slice 4's `search_efforts` for the ambiguous-match flow. The `reopen_effort` tool itself has no dependency beyond the existing manifest/state infrastructure.

---

## Success Criteria

- [ ] `reopen_effort` flips concluded effort to open
- [ ] Original raw log preserved — new messages append
- [ ] Separator line marks where reopening occurred
- [ ] Re-conclusion produces updated summary covering all messages
- [ ] LLM calls `reopen_effort` directly for explicit requests
- [ ] LLM uses `search_efforts` + asks user for ambiguous matches
- [ ] LLM opens new effort when user declines reopen
- [ ] Expanded effort correctly transitions to open on reopen
- [ ] All existing tests still pass (backward compatible)

---

## Related Documents

- [Slice 1 spec](01-core-compaction-proof.md) — Core compaction
- [Slice 2 spec](02-expansion-multi-effort.md) — Expansion & multi-effort
- [Slice 3 spec](03-salience-decay.md) — Salience decay
- [Slice 4 spec](04-bounded-working-context.md) — Bounded working context & search
- [Slices README](README.md) — Roadmap overview
