# Typed Conflicts: Beyond Binary Contradiction

## Status: Brainstorm — needs dev agent exploration

## Discovery

While writing the topological truth paper, we ingested the paper into its own knowledge graph. The system found 48 contradictions, but analysis revealed that most were not logical contradictions — they were different *kinds* of tension being flattened into a single `contradicts` edge type.

The current system treats all conflicts identically: count supporters, pick a winner. But only one of the five observed conflict types actually has a "winner."

## Observed Conflict Types

| Type | Example from paper ingestion | Has a winner? | Correct resolution |
|------|------------------------------|---------------|-------------------|
| **Logical** | "all conflicts explicit" vs "conflicts flagged for resolution" | Yes | Topology → supersession (current behavior) |
| **Semantic** | "classification (no LLM)" vs "classification (LLM)" — same word, different referents | No | Disambiguation — clarify terms, not supersede |
| **Scope** | "all contradicts edges between pair removed" vs "edges declined 37→31" — per-pair vs aggregate | No | Hierarchy — one contains the other |
| **Temporal** | current architecture vs vision — both true in different timeframes | No | Timeline — both valid, different contexts |
| **Narrative** | paper reporting a contradiction vs paper asserting one | No | Provenance — distinguish voice |

**Key insight**: Only logical contradictions have winners. The other four need different resolution mechanisms entirely. Superseding a node is the wrong operation for a semantic collision — you clarify it, not kill it.

**Second insight**: These are not "false positives." They are real tensions in the text. We were wrong to call them linker bugs (though the linker DOES need to distinguish them). The system correctly identified semantic tension; it just lacks the vocabulary to classify what kind.

## Open Questions for Dev Agent

1. **Where does typing happen?** At the linker pass (LLM classifies conflict subtype during ingestion), at conflict resolution time (algorithm detects patterns), or both (coarse at ingestion, refined at resolution)?

2. **Schema change?** Subtype the edge (`contradicts:logical`, `contradicts:semantic`) or add a property field (`contradicts` with `subtype: semantic`)? Property field is more extensible.

3. **Resolution per type.** Logical → supersession (current). Semantic → disambiguation node linking both? Scope → `generalizes` edge? Temporal → timeframe metadata? Each type probably needs its own resolution mechanic.

4. **The 80/20 question.** Logical + semantic might capture most real value. Temporal and narrative might be edge cases. Scope might be addressable by better linker context. What's the minimum viable type set?

5. **Does this change the conflict resolution algorithm?** Currently `_classify_conflict()` only looks at support counts. If it also knew the conflict subtype, it could route to different resolution strategies. But that adds complexity to the simplest part of the system.

6. **Interaction with issue #4 and #6.** Issue #4 (abstraction-level false positives) is likely scope-type conflicts. Issue #6 (narrative voice) is narrative-type conflicts. Typed conflicts might subsume both issues — they're not bugs, they're missing type information.

## Related

- `fact-311` in KG: semantic collisions as a class of false positives
- GitHub issue #4: linker false positives (abstraction level) — likely scope-type
- GitHub issue #6: narrative voice confusion — likely narrative-type
- `src/oi/conflicts.py`: current untyped conflict resolution
- `docs/research/topological-truth-paper.md` Section 9: self-ingestion findings
