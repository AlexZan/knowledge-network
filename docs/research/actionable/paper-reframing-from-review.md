# Paper Reframing: Findings from Auto-Resolution Review

**Date**: 2026-03-15
**Context**: Sample review of 15/113 V3 auto-resolutions, 7 reviewed in detail

## Key insight

"Zero false positives in auto-resolution" is the wrong headline metric. It conflates two things:

1. **Did the LLM correctly identify contradictions?** — Construction quality, driven by model performance and prompt instructions. Topology has no role.
2. **Did the topology pick the right winner?** — Almost tautological. The side with more support wins by definition.

The claim is also factually wrong: sample #7 (fact-057 vs fact-1139) is a confirmed false positive — a scope mismatch between a broad theory claim and a narrow GRW mathematical detail that the linker falsely flagged as contradictory, then the topology auto-resolved because of lopsided support.

## What the topology actually demonstrates

- **Conservative abstention** — knowing when NOT to act (5x threshold, subjective conflicts never auto-resolved, 55% of remaining conflicts were construction artifacts correctly left for human review)
- **Structural properties** — not gameable, not authoritarian, self-correcting, auditable end-to-end
- **Emergent patterns** — battleground nodes, depth of contradiction, cross-source signatures, argumentative trajectory
- **Accessible truth** — the graph gives the best truth accessible from the evidence it contains, not absolute truth. A 27:2 ratio for established QM over an unpublished theory is correct given the current graph — feed in validating experiments and the ratio shifts

## Sample review verdicts (7/15 reviewed)

| # | Ratio | Verdict | Notes |
|---|-------|---------|-------|
| 1 | 27:2 | Correct | Standard QM beat author's refinement — topology reflects evidence state |
| 2 | 14.5:0 | Correct outcome, suspect mechanism | Winner supported by near-duplicate node (inflation) |
| 3 | 283:0 | Correct | Valid contradiction caught within author's own theory |
| 4 | — | Correct | Both ideas worth exploring but winner has more support |
| 5 | — | Correct | Good conflict caught |
| 6 | — | Correct | Both valid ideas, winner has more support, loser worth preserving |
| 7 | 33.4:0 | **False positive** | Scope mismatch — not a real contradiction. LLM construction error auto-resolved |

## Paper changes needed

- Drop "zero false positives" as headline claim throughout (abstract, 3.7, 10)
- Reframe around abstention quality and structural properties
- Consider adding "accessible truth" framing to Section 7.2
- Clarify that resolution quality is bounded by construction quality (already in Section 8 but not reflected in the headline claims)
