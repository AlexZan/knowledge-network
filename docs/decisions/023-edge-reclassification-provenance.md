# Decision 023: Edge Reclassification with Review Provenance

**Date**: 2026-03-07
**Status**: Implemented

## Context

During manual conflict review of the rebuilt physics KG (post Decision 022), we discovered that many `contradicts` edges are false positives — the linker LLM flagged nodes as contradictory when they are actually complementary perspectives, different scopes, or compatible frameworks.

The existing system has two options for handling these:
1. `resolve_conflict()` — picks a winner, supersedes the loser. Destructive: removes a valid node.
2. `remove_edge()` — deletes the contradicts edge entirely. Loses the relationship information.

Neither option is correct for "these aren't contradictory, they're related." We need to **reclassify** the edge (e.g., `contradicts` → `related_to`) while preserving an auditable record of *why* the human reviewer made that judgment.

Additionally, the review process generates valuable reasoning that should be captured as first-class provenance — not just a summary field, but a link to the raw discussion that led to the decision. This is the knowledge network practicing what it preaches: conclusions backed by traceable evidence.

## Decision

### Edge Reclassification

Add `reclassify_edge()` to `knowledge.py`:
- Changes an edge's `type` (e.g., `contradicts` → `related_to`)
- Records a `reasoning` summary (the judgment)
- Records a `provenance_uri` pointing to the raw review discussion
- Records a `reviewed_at` timestamp
- Cleans up `has_contradiction` flags when contradicts edges are removed

### Review Provenance Files

Store raw review excerpts in `{session_dir}/reviews/`:
- One file per reclassification decision
- Contains the **verbatim relevant chat text** — only the portion discussing that specific conflict, not the full conversation log
- Named by conflict identifier (e.g., `S1-fact059-fact031.md`)
- Referenced by `review://{filename}` URI scheme in the edge's `provenance_uri`

### Audit Trail

```
edge.reasoning  →  "what was decided" (summary)
edge.provenance_uri  →  "review://S1-fact059-fact031.md" (links to raw evidence)
edge.reviewed_at  →  timestamp of the review
```

The raw review file contains the exact conversation that led to the decision, providing full traceability from edge → reasoning → raw discussion.

## Consequences

- False-positive contradicts edges can be corrected without destroying nodes or losing relationships
- Every reclassification is auditable: summary + raw provenance + timestamp
- Review files are portable — they travel with the KG data directory
- The `review://` URI scheme distinguishes human-reviewed edges from LLM-generated ones
- Edge schema gains optional fields (`provenance_uri`, `reviewed_at`) — backwards compatible
