# Slice 4: Bounded Working Context

**Goal**: Prove that working memory stays bounded regardless of conversation length — old summaries and ambient messages evict naturally, retrievable on demand via search. Truly infinite conversation without forced compaction.

**Purpose**: Generate proof data for the CCM whitepaper — "working context is self-managing at every tier, not just for expanded efforts."

---

## Core Hypothesis

> Working memory should behave like a cache: bounded in size, with old items evicting naturally. Nothing is deleted — evicted items move to a cheaper storage tier (manifest on disk) and are retrievable via search. The LLM context window stays bounded no matter how long the conversation runs.

---

## What Slices 1-3 Proved

| Slice | What | Status |
|-------|------|--------|
| 1 | Open effort = raw context, concluded = summary only (~80% savings) | Done |
| 2 | Expansion restores full context on demand, multi-effort switching | Done |
| 3 | Expanded efforts auto-collapse after 3 turns without reference | Done |

## What Slice 3 Left Unbounded

Slice 3 solved decay for **expanded efforts** (temporarily loaded raw logs). But two things still grow without limit:

| Problem | Current behavior | At scale |
|---------|-----------------|----------|
| **Concluded effort summaries** | ALL summaries loaded into system prompt | 500 efforts = thousands of tokens of summaries |
| **Ambient messages** | ALL of `raw.jsonl` loaded into context | 200 exchanges = massive ambient section |

After a long conversation, `_build_messages` produces a context that keeps growing even though most of it is irrelevant to the current topic. Eventually it would exceed the model's context window.

---

## Three-Tier Memory Architecture

```
┌─────────────────────────────────────────────┐
│  WORKING MEMORY (in LLM context window)     │
│  - System prompt                            │
│  - Recent ambient messages (last N)         │
│  - Recently-referenced summaries            │
│  - Expanded effort raw logs                 │
│  - Open effort raw logs (active last)       │
│  Bounded: evicts old items automatically    │
├─────────────────────────────────────────────┤
│  MANIFEST (on disk, searchable)             │
│  - All effort entries (id, status, summary) │
│  - manifest.yaml — permanent record         │
│  Never evicted, always searchable           │
├─────────────────────────────────────────────┤
│  RAW LOGS (on disk, expandable)             │
│  - efforts/*.jsonl — full conversations     │
│  - raw.jsonl — full ambient history         │
│  Never evicted, expandable on demand        │
└─────────────────────────────────────────────┘
```

**Key principle**: Eviction moves items DOWN a tier, never deletes them. Working memory is a sliding window over permanent storage.

---

## What Changes

### 1. Summary Eviction

Currently `_build_messages` loads all concluded effort summaries into the system prompt. Change: only include summaries that have been referenced within the last `SUMMARY_EVICTION_THRESHOLD` turns.

**Mechanism**: Extend the existing decay/reference tracking (Slice 3) to cover summaries, not just expanded efforts. Each concluded effort in the manifest gets a `last_referenced_turn` (already tracked in `expanded.json` for expanded efforts — extend to all concluded efforts).

**Eviction rule**: If a concluded effort's summary hasn't been referenced in `SUMMARY_EVICTION_THRESHOLD` turns, exclude it from working memory. It stays in the manifest, searchable.

**When does a summary count as "referenced"?**
- User or assistant mentions the effort ID
- User or assistant mentions 2+ keywords from the summary (same logic as Slice 3 decay)
- LLM calls `expand_effort`, `search_efforts`, or `effort_status` for that effort
- The effort was just concluded this session (grace period: don't evict immediately)

### 2. Ambient Message Window

Currently `_build_messages` loads ALL of `raw.jsonl`. Change: only load the last `AMBIENT_WINDOW` exchanges (user+assistant pairs).

**Mechanism**: Simple tail — read the last N lines from `raw.jsonl`. Older ambient messages are still on disk, still searchable, but not in working memory.

**AMBIENT_WINDOW**: Start with 10 exchanges (20 messages). This gives enough conversational continuity without unbounded growth.

### 3. `search_efforts` Tool

New LLM-callable tool. When the user asks about a topic whose summary has been evicted from working memory, the LLM calls this tool to search the manifest.

```
search_efforts(query: str) -> JSON
```

**Search logic**: Match query against all concluded effort summaries + effort IDs using keyword overlap (same `extract_keywords` + `is_referenced` logic from decay.py). Return matching summaries ranked by relevance.

**Returns**: List of matching efforts with id, summary, status. The LLM can then:
- Answer from the summary directly
- Call `expand_effort` if the user needs raw details

**When to call**: The system prompt tells the LLM: "If the user asks about a past topic and you don't see it in the concluded efforts list, use search_efforts to find it."

### 4. Updated System Prompt

Add a section explaining eviction and search:

```
## Memory

Concluded effort summaries shown above are only the recently-referenced ones.
Older summaries are still stored — use search_efforts(query) to find past efforts
not shown in working memory. You can then expand_effort(id) for full details.
```

---

## Updated Working Context Structure

Before (Slice 3):
```
Working Context = system_prompt
               + ALL concluded summaries (non-expanded)    ← unbounded
               + ALL ambient messages                      ← unbounded
               + expanded effort raw
               + open effort raw (active last)
```

After (Slice 4):
```
Working Context = system_prompt
               + recently-referenced summaries only        ← bounded
               + last N ambient exchanges                  ← bounded
               + expanded effort raw                       ← bounded (by Slice 3 decay)
               + open effort raw (active last)             ← bounded (by user behavior)
```

Every tier is now bounded. Nothing is lost — just moved to a cheaper tier.

---

## Flow Examples

### Example 1: Natural eviction

```
Turn 1-20:  User works on auth-bug, concludes it.
Turn 21-40: User works on perf-fix, concludes it.
Turn 41-60: User works on sailing-trip, concludes it.
Turn 61-80: User works on db-migration, concludes it.
            auth-bug summary hasn't been referenced since turn 20.
            auth-bug evicts from working memory (still in manifest).
Turn 81:    User: "What was the fix for the auth thing?"
            LLM sees no auth-related summary in working memory.
            LLM calls search_efforts("auth fix")
            → Returns: {id: "auth-bug", summary: "Fixed 401 errors..."}
            LLM answers from summary, or expands for full details.
```

### Example 2: Long ambient conversation

```
Turn 1-50:  50 ambient exchanges (no efforts).
            raw.jsonl has 100 messages.
            Working memory only shows last 10 exchanges (20 messages).
            Turns 1-40 are on disk, not in context.
            Context stays bounded at ~same size regardless of how long the chat runs.
```

### Example 3: Re-reference prevents eviction

```
Turn 1:     Conclude auth-bug.
Turn 2-30:  Work on other things. auth-bug summary in working memory.
Turn 31:    User: "Similar to the auth-bug pattern..."
            → Reference detected. auth-bug stays in working memory.
Turn 32-60: No auth references.
            → auth-bug eventually evicts again.
```

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SUMMARY_EVICTION_THRESHOLD` | 20 | Turns without reference before summary leaves working memory |
| `AMBIENT_WINDOW` | 10 | Number of recent ambient exchanges to keep in working memory |

**Why 20 for summaries?** Summaries are cheap (30-50 tokens each). They should linger longer than expanded raw logs (which decay at 3 turns). A threshold of 20 means summaries stay relevant for roughly 20 exchanges before evicting.

**Why 10 for ambient?** 10 recent exchanges provide enough conversational continuity. Older ambient chat is rarely relevant — if it is, the user will reference a specific topic and trigger a search.

---

## New Tool Definition

```json
{
  "type": "function",
  "function": {
    "name": "search_efforts",
    "description": "Search past efforts by topic. Use when the user asks about something not shown in the concluded efforts list. Returns matching effort summaries from the full manifest.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "What to search for (topic, keywords, effort name)"
        }
      },
      "required": ["query"]
    }
  }
}
```

---

## Implementation Changes

### `state.py`
- Add `_load_summary_references` / `_save_summary_references` — tracks `last_referenced_turn` for all concluded efforts (not just expanded ones)
- Or extend existing `expanded.json` → rename to `memory_state.json` with sections for expanded state AND summary references

### `orchestrator.py` — `_build_messages`
- Filter concluded summaries: only include those referenced within `SUMMARY_EVICTION_THRESHOLD` turns
- Cap ambient messages: only load last `AMBIENT_WINDOW * 2` lines from `raw.jsonl`
- Add memory section to system prompt explaining eviction + search

### `decay.py`
- Extend `check_decay` to also track summary references (same keyword matching, applied to all concluded efforts not just expanded ones)
- Or create a separate `check_summary_eviction` function

### `tools.py`
- Add `search_efforts(session_dir, query)` tool handler
- Add tool definition to `TOOL_DEFINITIONS`
- Update `execute_tool` dispatcher

### `prompts/system.md`
- Add memory section explaining that not all summaries are shown and how to search

---

## Testing Strategy

| What | How | LLM needed? |
|------|-----|-------------|
| Summary eviction after threshold | Unit test | No |
| Reference resets eviction counter | Unit test | No |
| Evicted summaries stay in manifest | Unit test | No |
| Ambient window caps messages | Unit test | No |
| `search_efforts` returns matching summaries | Unit test | No |
| `search_efforts` finds evicted effort | Unit test | No |
| `search_efforts` ranks by relevance | Unit test | No |
| Working memory token count stays bounded | Proof run | No (mocked) |
| LLM calls search_efforts for evicted topic | e2e | Yes |
| LLM expands after search | e2e | Yes |
| Full cycle: conclude → evict → search → recall | Proof run | No (mocked) |

---

## Proof Run (Scripted)

| Step | Action | Summaries in WM | Ambient in WM | Total WM tokens |
|------|--------|----------------|---------------|-----------------|
| Setup | 5 concluded efforts, 30 ambient exchanges | 5 | 10 (last) | ~800 |
| Turn 1 | Reference effort-1 and effort-2 | 5 | 10 | ~850 |
| Turn 21 | No references to effort-3,4,5 for 20 turns | 2 (1,2 only) | 10 | ~700 |
| Turn 22 | User asks about effort-4 topic | search finds it | 10 | ~750 |
| Turn 23 | User asks for details | expand effort-4 raw | 10 | ~1200 |
| Turn 26 | Decay collapses effort-4 | 3 (1,2,4) | 10 | ~750 |

**Key metrics**:
- Working memory stays bounded even as total concluded efforts grow
- Evicted efforts are retrievable via search
- search → expand path works seamlessly
- Token count has a ceiling, not unbounded growth

---

## Scope

### In Scope

- Summary eviction from working memory after `SUMMARY_EVICTION_THRESHOLD` turns
- Ambient message windowing (last `AMBIENT_WINDOW` exchanges)
- `search_efforts` tool for retrieving evicted summaries
- Reference tracking for all concluded effort summaries
- Updated system prompt explaining memory tiers
- Proof run: bounded growth + search recall

### Out of Scope (Later Slices)

| Feature | Slice | Why Deferred |
|---------|-------|--------------|
| Cross-session persistence | 5+ | Single session is sufficient for proof |
| Semantic/embedding search | 5+ | Keyword matching is good enough |
| Token budget (hard cap) | 5+ | Eviction thresholds provide soft cap |
| Summary-of-summaries | 5+ | Individual summaries are cheap enough |
| Ambient message search | 5+ | Ambient is low-value; window is sufficient |

---

## Success Criteria

- [ ] Concluded effort summaries evict from working memory after threshold
- [ ] Evicted summaries remain in manifest (not deleted)
- [ ] Reference resets eviction counter for summaries
- [ ] Ambient messages capped to last N exchanges
- [ ] Older ambient messages remain in raw.jsonl
- [ ] `search_efforts` finds evicted efforts by keyword
- [ ] LLM correctly calls search_efforts when topic not in working memory
- [ ] Working memory token count has a bounded ceiling
- [ ] Proof run demonstrates bounded growth with search recall
- [ ] All existing tests still pass (backward compatible)

---

## Related Documents

- [Slice 1 spec](01-core-compaction-proof.md) — Core compaction
- [Slice 2 spec](02-expansion-multi-effort.md) — Expansion & multi-effort
- [Slice 3 spec](03-salience-decay.md) — Salience decay (foundation for eviction)
- [Slices README](README.md) — Roadmap overview
