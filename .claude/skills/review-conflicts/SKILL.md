---
name: review-conflicts
description: Review KG conflicts one-by-one with the user. Loads the review format, fetches provenance metadata, and walks through each conflict awaiting approval before executing reclassifications.
disable-model-invocation: true
argument-hint: "[session_dir] [conflict-review.md path]"
---

# Conflict Review Workflow

Review knowledge graph conflicts interactively with the user. For each conflict, present the full context and wait for explicit approval before executing any reclassification.

## Arguments

- `$ARGUMENTS` — optional: `[session_dir] [conflict-review-file]`
- Defaults: session_dir = `/data/physics-theory-kg`, conflict review file = `docs/research/conflict-review.md`

## Setup

1. Read the conflict review markdown file to get the list of conflicts
2. Check which conflicts have already been resolved (have review files in `{session_dir}/reviews/`)
3. Start from the first unresolved conflict

## Display Format

For EACH conflict, present it using this exact template:

---

### S{N} — {STRONG RECOMMENDATION | AMBIGUOUS}

| | Side A | Side B |
|---|---|---|
| **Node** | {id} | {id} |
| **Authored** | {YYYY-MM-DD} | {YYYY-MM-DD} |
| **Delta** | | {N days/weeks, which is newer} |
| **Source type** | {chat / document / external} | {chat / document / external} |
| **Source** | {conversation title or doc name} | {conversation title or doc name} |
| **Claim** | "{summary}" | "{summary}" |

**Linker reasoning**: {why the linker flagged this as contradicts}

**Analysis**: {your assessment — are they truly contradictory, complementary, different scopes, evolutionary stages, etc.}

**Proposed action**: `{old_type}` → `{new_type}` ({keep_both|keep_a|keep_b|defer})
**Reasoning**: {justification for the proposed action}

---

Then **WAIT** for explicit user approval before executing.

## Fetching Metadata

For each conflict, load both nodes from the KG YAML to get:
- `authored_at` — when the source conversation/document was created
- `provenance_uri` — which conversation or document it came from
- `reasoning` — why the extraction LLM created this node

Use this Python snippet to fetch node metadata:
```python
import yaml
from pathlib import Path
g = yaml.safe_load(Path('{session_dir}/knowledge.yaml').read_text())
nodes = {n['id']: n for n in g['nodes']}
# Then access nodes['fact-XXX']['authored_at'], etc.
```

## Executing Reclassifications

After user approves, use `reclassify_edge()`:
```python
from oi.knowledge import reclassify_edge
result = reclassify_edge(
    session_dir=Path('{session_dir}'),
    source_id='{side_a_id}',
    target_id='{side_b_id}',
    old_type='contradicts',
    new_type='{new_type}',
    reasoning='{reasoning}',
    review_text='{review_text}',
    review_filename='S{N}-{side_a_id}-{side_b_id}.md',
)
```

For `mark_reviewed()` (defer/uncertain):
```python
from oi.knowledge import mark_reviewed
result = mark_reviewed(
    session_dir=Path('{session_dir}'),
    source_id='{side_a_id}',
    target_id='{side_b_id}',
    edge_type='contradicts',
    review_status='deferred',  # or 'uncertain', 'approved'
    notes='{notes}',
    review_text='{review_text}',
    review_filename='S{N}-{side_a_id}-{side_b_id}.md',
)
```

## Rules

1. **Never skip the display step** — always show the full table before proposing an action
2. **Never execute without approval** — wait for the user to say yes/approve/go ahead
3. **Show timestamps** — always include `authored_at` and delta between the two sides
4. **Track progress** — after each approval, confirm execution and move to the next unresolved conflict
5. **Batch load metadata** — load all node metadata once at the start to avoid repeated YAML reads
7. **Always read source logs** — for every conflict, read the source conversation/document logs for both sides via `provenance_uri` before presenting analysis. Don't rely only on node summaries — dig into the original context for better recommendations
6. **Gap analysis after every resolution** — after each conflict is resolved/reclassified, ask: "Can we identify a gap from this that would not be solved by one of our planned improvements?" Check against the Planned section in `docs/slices/README.md`. If a new gap is found, propose adding it to Planned.
8. **Don't reclassify terminology conflicts** — when a `contradicts` edge is valid because of wrong terminology (not wrong logic), keep it as `contradicts` and mark reviewed. The conflict signal is valuable until the terminology correction flow (planned #4) supersedes the offending node. Only reclassify when the claims as written are genuinely non-contradictory.
