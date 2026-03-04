# Decision 021: Contradicts Gate — Mandatory Pre-Check in Linker Prompt

**Status**: Implemented
**Date**: 2026-03-04

---

## Problem

The linker misclassifies scope/framing tensions as `contradicts` edges. Four nodes in the physics KG are contested due to this:

| Node | Tension | Why it's not a contradiction |
|------|---------|------------------------------|
| `fact-189` | "Only 1s registered" vs "fluctuations are not data" | Same concept at different abstraction levels |
| `fact-289` | "Null catalysts" vs "1-bit cause" | Same mechanism, different terminology |
| `fact-298` | Permanent anchors vs immediately-deactivated anchors | Model evolved within conversation |
| `decision-004` | Reset memory_weight to 1.0 vs gradual decay | Implementation diverged from concept |

The prompt already says "different abstraction levels → related_to" (step 2) and "only use contradicts when both claims cannot simultaneously be true" (step 4). But the LLM skips past step 2 and reaches for `contradicts` when it sees surface-level tension.

These are not contradictions — they're the same idea described differently. They should be `related_to`. The false `contradicts` edges suppress confidence and trigger conflict resolution for nodes that have nothing to resolve.

**Prior art**: Decision 019 added `related_to` as an edge type and reduced contradictions by 40%. These 4 are the residual.

---

## Decision

Restructure the linker prompt's contradicts step to add a **mandatory gate**. Before the LLM can output `contradicts`, it must explicitly consider whether both claims could be simultaneously true in different contexts.

### Before (current step 4)

> "Does Node A directly and logically refute Node B as a factual claim — not just describe a different scenario or aspect? Only use contradicts when both claims cannot simultaneously be true. If YES → contradicts"

### After (new steps 4a + 4b)

> "4a. Could both claims be true if they describe the same concept at different detail levels, use different terminology, or apply in different contexts? If YES → related_to"
>
> "4b. Does accepting Node A force you to reject Node B — they cannot both be true in ANY context? If YES → contradicts"

The gate makes `related_to` the explicit escape hatch that the LLM must consider before reaching `contradicts`.

---

## Scope

- Prompt change only in `src/oi/linker.py` (`_build_link_prompt_single` and `batch_link_nodes`)
- No schema changes
- No resolver changes
- No new edge types or subtypes

---

## Validation Plan

**Success criteria**: Re-run the physics KG ingestion (same 5 docs) and check contested node count. Currently 19 contested, 4 are within-theory tensions. Success = those 4 reclassified as `related_to`, contested count drops to ~15.

**Failure criteria**: If the 4 persist after the gate, the single-pass prompt approach has hit its ceiling. Next step would be a validation pass (second LLM call reviewing only `contradicts` edges).

---

## Results

**2026-03-04: 4/4 reclassified successfully.**

Targeted test: ran the 4 contested within-theory tension pairs through the updated linker prompt using `cerebras/gpt-oss-120b`. All 4 now classify as `related_to` instead of `contradicts`.

| Pair | Old | New | LLM Reasoning |
|------|-----|-----|---------------|
| fact-118 → decision-004 | contradicts | related_to | "Conceptual role vs specific implementation choice" |
| fact-199 → fact-189 | contradicts | related_to | "Different abstraction levels — one defines nature, other describes recording" |
| fact-152 → fact-298 | contradicts | related_to | "Different system versions, compatible" |
| fact-182 → fact-289 | contradicts | related_to | "Same concept, different details, can coexist" |

The mandatory 4a gate ("could both be true in different contexts?") forced the LLM to consider compatibility before reaching for `contradicts`. The existing step 2 ("different abstraction levels → related_to") was insufficient on its own — the explicit pre-check before `contradicts` made the difference.

**Next step**: Full re-ingestion of the physics KG to validate at scale (contested count should drop from 19 to ~15). The targeted test proves the gate works on the known false positives; full re-ingestion confirms it doesn't over-suppress real contradictions.

---

## Related

- [Decision 019: Semantic vs Logical Edges](019-semantic-vs-logical-edges.md) — introduced `related_to`
- [Decision 017: Typed Conflicts](017-typed-conflicts.md) — brainstorm that motivated this. Conclusion: typed contradictions aren't needed; the problem is classification accuracy, not missing types
- GitHub Issue #4: linker false positives across abstraction levels
- `docs/research/ingestion-pipeline-experiments.md`: contested node analysis
