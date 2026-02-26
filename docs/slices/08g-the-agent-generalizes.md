# Slice 8g: The Agent Generalizes

## Context

Slices 8a-8f built a knowledge graph with auto-extraction, linking, confidence, querying, and traceability. Nodes are facts, preferences, and decisions — all tied to specific efforts or sessions. The system remembers *what happened*, but doesn't yet notice *patterns across efforts*.

Scenario 3 ([08-knowledge-graph-scenarios.md](08-knowledge-graph-scenarios.md#scenario-3-the-pattern-emerges)) shows the target UX: after the third effort involving stale auth state, the system says "I'm noticing a pattern" and distills a generalized principle.

## What This Slice Adds

1. **`principle` node type** — a generalized insight derived from multiple facts
2. **`exemplifies` edge type** — links facts to the principle they support
3. **Pattern detection** — LLM call after knowledge extraction checks if new facts converge with existing ones
4. **Abstraction levels** — principles carry a level (contextual → general → universal) indicating how far they've been stripped of project-specific details
5. **Privacy gradient** — higher abstraction levels are naturally shareable; lower levels contain project specifics

## Design

### Node: `principle`

Same schema as existing nodes, with two additional fields:

```yaml
- id: principle-001
  type: principle
  summary: "Validate mutable auth state at each consumption point. Validate immutable properties once at entry and cache."
  abstraction_level: 2          # NEW: 1=contextual, 2=general, 3=universal
  instance_count: 3             # NEW: number of exemplifying facts
  source: null                  # principles don't come from one effort
  created_in_session: "2026-02-24T10-30-00"
  status: active
```

### Edge: `exemplifies`

New edge type connecting facts to principles:

```yaml
- source: fact-007              # the specific fact
  target: principle-001         # the general principle
  type: exemplifies
  reasoning: "Token cache bug is an instance of stale auth state at consumption point"
  created: "2026-02-24T10:30:00"
```

Direction: fact → principle (the fact exemplifies the principle). This means principles accumulate inbound `exemplifies` edges, which feeds confidence computation naturally.

### Abstraction Levels

| Level | Name | Privacy | Example |
|-------|------|---------|---------|
| 1 | Contextual | Project-specific | "Batch processors must validate credentials per record, not just at batch submission" |
| 2 | General | Shareable | "Validate mutable auth state at each consumption point" |
| 3 | Universal | Domain-independent | "Validate state where trust is consumed, not where the request originates" |

Level 0 (raw) is the effort log itself — already handled by expand_knowledge/expand_effort. Facts extracted from efforts are implicitly level 1.

Principles start at level 2. The LLM is prompted to strip project-specific details when generating the principle summary. Level 3 (universal) could be a future refinement when the same principle appears across truly different domains.

### Pattern Detection Pipeline

**When**: After `extract_knowledge()` produces new facts during `close_effort`.

**Flow**:

```
close_effort
  → summarize effort
  → extract_knowledge (produces 0-5 facts)
  → add_knowledge + run_linking (per fact)
  → detect_patterns (NEW)          ← takes new facts + their linked neighbors
      → find convergence candidates
      → LLM: "do these facts point to a general principle?"
      → if yes: create principle node + exemplifies edges
```

**`detect_patterns(new_node_ids, graph, model)`**:

1. For each new fact, collect its `supports` neighbors (from auto-linking)
2. Group facts that share neighbors — facts linked to the same nodes are potential pattern members
3. Filter: need ≥ 3 facts from ≥ 2 independent sources to trigger pattern detection
4. LLM call with the candidate cluster: "These N facts from independent efforts seem related. Is there a generalizable principle? If so, state it without project-specific details."
5. If LLM returns a principle: check if an existing principle already covers it (keyword + LLM comparison)
   - If existing principle found: add `exemplifies` edge from new fact to existing principle, update `instance_count`
   - If no match: create new `principle` node + `exemplifies` edges from all cluster members

**Threshold**: 3 facts from 2+ sources. This prevents premature generalization from a single effort.

### Confidence for Principles

Existing confidence computation works naturally:

- New principle: `low` (just created, few edges)
- After more facts link: `medium` (inbound supports/exemplifies count grows)
- Well-supported principle: `high` (≥3 independent sources, ≥2 support edges)
- Contradicted principle: `contested` (when a fact contradicts it — triggers Scenario 4 flow)

One change needed: `compute_confidence` should count `exemplifies` edges the same as `supports` edges for confidence calculation.

### Query Integration

`query_knowledge` already returns nodes by keyword match. Principles are nodes, so they're queryable automatically. Two enhancements:

1. When a principle matches a query, include its exemplifying facts in the response (follow `exemplifies` edges backward)
2. When a fact matches a query and it exemplifies a principle, mention the principle

### System Prompt Integration

Currently `_build_knowledge_prompt()` in orchestrator.py shows active knowledge nodes. Principles should appear the same way, but with their abstraction level indicated:

```
Knowledge:
  - [fact-007] Token cache must be initialized on connection reuse (medium confidence)
  - [principle-001] Validate mutable auth state at each consumption point (high confidence, 3 instances)
```

The `instance_count` gives the LLM context about how well-established the principle is.

### Presentation (Effort Close)

When pattern detection fires, the close_effort banner includes:

```
Learned:
  - Batch processors must validate credentials per record

I'm noticing a pattern: this is the third time I've seen auth state
go stale between validation and use. [3 efforts, 2 independent sources]

Generalized: "Validate mutable auth state at each consumption point."
```

This is a banner enhancement — the orchestrator formats the pattern detection result into natural language for the LLM to present.

## Phases

### Phase 1: Schema extensions

- `knowledge.py`: Add `"principle"` to valid node types, add `"exemplifies"` to valid edge types
- `knowledge.py`: `add_knowledge` accepts `abstraction_level` and `instance_count` fields
- `confidence.py`: Count `exemplifies` edges same as `supports` for confidence
- `query_knowledge`: When returning a principle, include exemplifying facts
- Tests: ~8

### Phase 2: Pattern detection pipeline

- New file `src/oi/patterns.py`: `detect_patterns(new_node_ids, knowledge, model)` → returns new principle nodes + edges
- `llm.py`: Add `detect_principle(facts, model)` LLM call — takes fact summaries, returns principle summary or null
- `llm.py`: Add `match_principle(new_principle_summary, existing_principles, model)` — dedup check
- `tools.py`: Wire `detect_patterns` into `close_effort` after `extract_knowledge` + `add_knowledge`
- Tests: ~10

### Phase 3: Orchestrator integration

- `orchestrator.py`: Update `_build_knowledge_prompt()` to show principle nodes with instance count
- `orchestrator.py`: Add pattern-detected banner in `_build_tool_banners()` for close_effort
- `tools.py`: Update close_effort return value to include pattern detection results
- Tests: ~6

## File Changes

| File | Phase | Change |
|------|-------|--------|
| `src/oi/knowledge.py` | 1 | Add `principle` type, `exemplifies` edge type, schema fields |
| `src/oi/confidence.py` | 1 | Count `exemplifies` like `supports` |
| `src/oi/patterns.py` | 2 | NEW — `detect_patterns()`, `find_convergence_candidates()` |
| `src/oi/llm.py` | 2 | Add `detect_principle()`, `match_principle()` |
| `src/oi/tools.py` | 2 | Wire pattern detection into close_effort |
| `src/oi/orchestrator.py` | 3 | Principle display in system prompt, pattern banner |
| `tests/test_knowledge.py` | 1 | Schema extension tests |
| `tests/test_confidence.py` | 1 | Exemplifies edge counting |
| `tests/test_patterns.py` | 2 | Pattern detection pipeline tests |
| `tests/test_tools.py` | 2 | close_effort pattern detection integration |
| `tests/test_orchestrator.py` | 3 | Principle display + banner tests |

**Estimated new tests: ~24**

## Key Function Signatures

```python
# patterns.py
def detect_patterns(
    new_node_ids: list[str],
    knowledge: dict,
    model: str,
) -> dict:
    """Returns {"principles": [...], "edges": [...]} or empty."""

def find_convergence_candidates(
    new_node_ids: list[str],
    knowledge: dict,
    min_facts: int = 3,
    min_sources: int = 2,
) -> list[list[dict]]:
    """Returns clusters of facts that may converge on a principle."""

# llm.py
def detect_principle(
    fact_summaries: list[str],
    model: str,
) -> str | None:
    """LLM: do these facts point to a general principle? Returns summary or None."""

def match_principle(
    new_summary: str,
    existing_principles: list[dict],
    model: str,
) -> str | None:
    """LLM: does this principle match an existing one? Returns matched ID or None."""

# knowledge.py (updated)
def add_knowledge(
    session_dir, node_type, summary, source=None, model=None,
    session_id=None, supersedes=None,
    abstraction_level=None,    # NEW
    instance_count=None,       # NEW
) -> dict:
```

## What's NOT in 8g

- **Level 3 (universal) abstraction**: Requires cross-domain pattern detection. Deferred until there's enough data diversity.
- **Scenario 4 (contradiction resolution)**: Already handled by 8c+8d supersedes flow. Principles participate in the same contradiction detection — no new work needed beyond what the linker already does.
- **User-initiated generalization**: The user saying "generalize these" — could be a future tool, but 8g focuses on automatic detection.
- **Principle refinement over time**: Updating principle summaries as more evidence arrives. Deferred — instance_count updates are sufficient for now.

## Verification

```bash
# Phase 1: schema + confidence
pytest tests/test_knowledge.py tests/test_confidence.py -v

# Phase 2: pattern detection
pytest tests/test_patterns.py tests/test_tools.py -v

# Phase 3: orchestrator
pytest tests/test_orchestrator.py -v

# Full suite: no regressions
pytest tests/ -v --ignore=tests/experiments --ignore=tests/test_e2e_real_llm.py

# E2E
pytest tests/test_e2e_real_llm.py -v -s
```

## Scenario 3 Walkthrough (Verification)

After implementing 8g, this UX should work:

1. User concludes effort #1 (token cache bug) → fact extracted: "Token cache must be initialized on connection reuse"
2. User concludes effort #2 (JWT rotation) → fact extracted: "Expired tokens must be cleared on rotation" → linked to fact #1 via `supports`
3. User concludes effort #3 (batch credential expiry) → fact extracted: "Batch processors must validate credentials per record" → linked to facts #1, #2
   - **Pattern detection fires**: 3 facts, 2+ sources, all related to stale auth state
   - **Principle created**: "Validate mutable auth state at each consumption point"
   - **3 `exemplifies` edges** created (each fact → principle)
   - **Banner shows**: "I'm noticing a pattern..." with the generalized principle
4. Future query about auth → principle surfaces with high confidence (3 instances, independent sources)
