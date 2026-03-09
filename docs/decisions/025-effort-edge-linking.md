# Decision 025: Effort-Edge Linking via Metadata

**Date**: 2026-03-08
**Status**: Implemented

## Context

Decision 023 introduced edge reclassification with review provenance. During manual conflict review, some conflicts are too complex to resolve immediately — the reviewer needs to re-read source material, rebuild mental context, or investigate further. These get deferred via `mark_reviewed(review_status="deferred")`.

Separately, the effort system (Decision 011) provides tracked work items for focused investigation. When a conflict is deferred, we want to create an effort to track the investigation — but there was no structured link between the effort and the edge(s) it investigates.

### Options Considered

1. **Formal graph edges** (`investigates` edge type from effort node to fact nodes) — queryable but adds edge bloat and a new edge type for a metadata concern.
2. **Metadata on the edge** (`effort: effort-name` field) — lightweight, no new edge types, grep-discoverable.
3. **Metadata on the effort node** (`related_edges` field) — couples effort schema to edge internals.
4. **Description only** — effort description mentions fact IDs in prose. Not machine-readable.

## Decision

Use lightweight metadata on the edge: add an optional `effort` field to edges via `mark_reviewed()`. The effort's description references the fact IDs (already the case). This creates a bidirectional reference without graph bloat:

- **Edge → Effort**: `edge.effort = "resolve-observer-objectivity-conflict"`
- **Effort → Edge**: effort description contains fact IDs and conflict context

### Implementation

Added `effort: str = ""` parameter to `mark_reviewed()`. When provided, the field is written directly onto the edge metadata. No schema changes, no new edge types.

## Consequences

- Deferred conflicts are traceable to their investigation effort
- No new edge types or graph complexity
- Machine-readable via simple field lookup or grep
- Scales naturally — multiple edges can reference the same effort
- Effort description remains the richer context (what to investigate, why)
