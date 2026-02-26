# Slice 8h: Reactive Knowledge — `because_of` Edges and Staleness Detection

## Origin

Architectural trace during unified KG design validation ([Decision 013](../decisions/013-unified-kg-architecture.md), Trace 6). A three-level dependency chain had no mechanism to detect stale justifications when a bottom node was superseded.

## Problem

Knowledge nodes can depend on other nodes for their validity, but the system has no way to express or detect this.

Example:
```
preference-001: "I prefer TypeScript"
  because_of → fact-003: "TypeScript has better IDE support"
    because_of → fact-001: "I use VS Code"
```

User says: "I switched to Neovim" → `fact-001` gets superseded. But `fact-003` and `preference-001` still show full confidence with no indication that their justification is stale. The system confidently states a preference whose foundation has changed.

## Scope

### In Scope

1. **`because_of` edge type** — a new relationship type expressing "this node's validity depends on that node"
2. **LLM can create `because_of` edges** — via `add_knowledge(edge_type="because_of", related_to=[...])`
3. **Staleness detection at query time** — `query_knowledge` checks if any `because_of` targets (1 hop) are superseded or contested
4. **Staleness flag in results** — query results include `stale_dependencies: [...]` when detected, listing the superseded/contested targets
5. **Confidence penalty** — nodes with stale dependencies have effective confidence lowered (never higher than "medium")
6. **System prompt guidance** — LLM told to surface stale dependencies conversationally

### Out of Scope (Deferred)

- **Multi-hop staleness** — only 1-hop `because_of` targets checked. Deep chain propagation deferred.
- **Eager propagation** — no event-driven walk of inbound edges on supersession. Lazy query-time only.
- **Auto-resolution** — the system flags staleness, the user resolves it. No automatic invalidation.

## Design

### `because_of` edge semantics

`because_of` means: "this node was created/justified based on that node being true." It's directional: `source` depends on `target`.

```
source: preference-001 ("I prefer TypeScript")
target: fact-003 ("TypeScript has better IDE support")
type: because_of
```

If the target is superseded, contested, or itself has stale dependencies, the source's justification is stale.

### Staleness check (in `query_knowledge`)

After computing confidence for a matched node, before adding it to results:

```python
# Check because_of targets for staleness
stale_deps = []
for edge in knowledge["edges"]:
    if edge["source"] == node["id"] and edge["type"] == "because_of":
        target = nodes_by_id.get(edge["target"])
        if target:
            if target.get("status") == "superseded":
                stale_deps.append({"node_id": target["id"], "reason": "superseded"})
            elif target.get("has_contradiction"):
                stale_deps.append({"node_id": target["id"], "reason": "contested"})
```

If `stale_deps` is non-empty:
- Add `"stale_dependencies": stale_deps` to the result entry
- Cap confidence level at `"medium"` (never report `"high"` for a node with stale deps)

### Confidence interaction

Staleness is not the same as contradiction. A node with stale dependencies isn't *wrong* — its justification is *uncertain*. The confidence penalty reflects this:

| Node state | Max confidence |
|-----------|---------------|
| No stale deps | Normal (low/medium/high/contested) |
| Has stale deps | Capped at medium |
| Has stale deps + own contradictions | Contested (contradiction takes priority) |

### System prompt addition

After the existing `add_knowledge` section in `src/oi/prompts/system.md`:

```markdown
**`because_of` edges:**
When a user states a preference or decision WITH a reason, create both nodes and
link them with `because_of`. Example: "I prefer X because Y" → preference node +
fact node + `edge_type="because_of"`.

When query_knowledge returns `stale_dependencies`, mention it naturally:
"You said you prefer TypeScript because of VS Code's IDE support, but you've
since switched to Neovim — does that preference still hold?"
```

## Changes

| File | Change |
|------|--------|
| `src/oi/tools.py` | Add `"because_of"` to `edge_type` enum in TOOL_DEFINITIONS |
| `src/oi/knowledge.py` | `query_knowledge`: staleness check + confidence cap after confidence computation |
| `src/oi/prompts/system.md` | `because_of` guidance for LLM |

No new files. No changes to `add_knowledge` — it already accepts arbitrary `edge_type` strings and stores them. The enum addition just makes it visible to the LLM.

## Tests

### `tests/test_knowledge.py` — new class `TestBecauseOfEdges`

1. **`test_because_of_edge_created`** — `add_knowledge(related_to=[X], edge_type="because_of")` stores a `because_of` edge
2. **`test_because_of_no_effect_on_confidence`** — `because_of` edges don't count as `supports` in confidence computation (they're dependency links, not evidence)

### `tests/test_knowledge.py` — new class `TestStalenessDetection`

3. **`test_stale_when_target_superseded`** — query a node whose `because_of` target is superseded → `stale_dependencies` in result
4. **`test_no_stale_when_target_active`** — query a node whose `because_of` target is active → no `stale_dependencies`
5. **`test_stale_when_target_contested`** — query a node whose `because_of` target has `has_contradiction=True` → `stale_dependencies`
6. **`test_confidence_capped_at_medium`** — node with stale deps + enough support for "high" → capped at "medium"
7. **`test_contested_overrides_stale_cap`** — node with stale deps + own contradiction → "contested" (not "medium")
8. **`test_multiple_stale_deps`** — node with two `because_of` targets, both superseded → both listed

### `tests/test_tools.py` — new tests

9. **`test_because_of_in_edge_type_enum`** — verify `because_of` is in tool definition enum

## Verification

```bash
# Slice tests
pytest tests/test_knowledge.py::TestBecauseOfEdges tests/test_knowledge.py::TestStalenessDetection tests/test_tools.py -v -k because_of

# Full regression
pytest tests/ -v --ignore=tests/experiments --ignore=tests/test_e2e_real_llm.py

# E2E
pytest tests/test_e2e_real_llm.py -v -s
```

## Success Criteria

- [ ] `because_of` edge type available to LLM
- [ ] `query_knowledge` detects and reports stale dependencies (1-hop)
- [ ] Confidence capped at medium for nodes with stale deps
- [ ] System prompt guides LLM to surface staleness conversationally
- [ ] All existing tests still pass (no regressions)
