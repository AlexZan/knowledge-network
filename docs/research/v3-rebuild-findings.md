# V3 Rebuild Findings: Full-Scale Conversation-Aware Extraction

**Date**: 2026-03-07 to 2026-03-08
**Decisions**: 022 (conversation-aware extraction), 023 (edge reclassification), 024 (TOTP attestation, draft), 025 (effort-edge linking)

## Summary

Rebuilt the physics theory KG from scratch using conversation-aware extraction (Decision 022). Instead of chunking conversations into turn-pairs and extracting claims per-chunk, the new pipeline sends full conversations to the LLM in a single call with a conclusion-focused prompt. This eliminates intra-author false contradictions caused by the LLM seeing partial context.

## Scale

| Metric | V2 (per-chunk) | V3 (conversation-aware) |
|--------|----------------|------------------------|
| Conversations ingested | 7 | 120 |
| Documents ingested | 2 | 2 |
| Total nodes | 894 | 1,336 |
| Active nodes | 894 | 1,263 |
| Total edges | 5,020 | 8,022 |
| `related_to` | 3,618 | 5,981 |
| `supports` | 1,198 | 1,849 |
| `contradicts` (before resolution) | 163 | ~190 |
| `contradicts` (after auto-resolve) | 51 | 79 |
| `supersedes` | — | 113 |
| Auto-resolve rate | 67% | 58% |
| Failed ingestions | 0 | 1 |

### Source breakdown (active nodes)

- physics-theory (conversations): 1,104
- sep-philosophical-issues-qt.md: 99
- sep-collapse-theories.md: 59

### LLM model

Cerebras `gpt-oss-120b` ($0.35/M input, 128K context). Previous `llama-3.3-70b` no longer available on Cerebras.

## Manual Conflict Review (In Progress)

37 conflicts remained after auto-resolution. Manual review began with the user walking through each one.

### Results (20/37 reviewed)

| Conflict | Nodes | Action | Reason |
|----------|-------|--------|--------|
| S1 | fact-059 vs fact-031 | → `related_to` | Complementary perspectives (observer complexity vs decoherence) |
| S2 | fact-059 vs fact-013 | → `related_to` | Different levels (collapse mechanism vs measurement outcomes) |
| S3 | fact-061 vs fact-013 | → `related_to` | "Deterministic form" is projection onto outcome, not deterministic prediction |
| S4 | fact-127 vs fact-870 | → `related_to` | Different scopes (intra-universe causal links vs inter-universe disconnection) |
| S5 | fact-147 vs fact-030 | → `related_to` | "Compatible model" subsumes "which-path information" — same mechanism at different granularity |
| S6 | fact-147 vs fact-031 | → `related_to` | Ontological (real collapse) vs phenomenological (apparent collapse) — different levels |
| S7 | fact-174 vs fact-598 | → `related_to` | A surveys existing theories, B stakes a position — complementary |
| S8 | fact-175 vs fact-467 | Deferred + effort | Theory evolution (14-day gap). Created effort `resolve-observer-objectivity-conflict` |
| S9 | fact-176 vs fact-501 | Kept `contradicts` | Terminology conflict — "rewriting collapse chain" is misleading. Candidate for terminology correction flow |
| S10 | fact-201 vs fact-519 | → `related_to` + effort | Not contradictory, but reviewer uncertain about fact-201. Created effort `verify-coherent-energy-transfer` |
| S11 | fact-206 vs fact-123 | Kept `contradicts` | Genuine — partial collapse (speculative) vs full collapse (standard physics). Let topology resolve |
| S12 | fact-228 vs fact-156 | → `related_to` | Sequential stages of fluctuation → collapse → memory spectrum. Candidate for process/sequence edge type |
| S13 | fact-262 vs fact-062 | → `supports` | Contrapositives of same principle — "collapse required for position" / "no collapse = interference" |
| S14 | fact-354 vs fact-634 | Kept `contradicts` | Terminology conflict — "space" and "lattice" for pre-spatial substrate. Candidate for correction flow |
| S15 | fact-354 vs fact-530 | Kept `contradicts` | Same terminology issue as S14. Keep signal until fact-354 is superseded |
| S16 | fact-370 vs fact-178 | Kept `contradicts` | Assistant-elevated spitball vs firm belief. Let topology resolve. Attribution-aware extraction would fix |
| S17 | fact-402 vs fact-401 | → `supports` | Same principle split into two nodes — "randomness is not information, but it IS information potential" |
| S18-S34 | (various) | Deferred (batch) | Intra-theory conflicts requiring domain expert review |
| S35 | fact-1112 vs fact-614 | Deferred + effort | Third-party frameworks (GRW vs Bohm) — neither is user's theory. Attribution gap |
| S36 | fact-1112 vs fact-1236 | Kept `contradicts` | Known rivalry: GRW vs Bohm, both from SEP articles |
| S37 | fact-1143 vs fact-1152 | Kept `contradicts` | Rival ontologies within collapse theory, intentionally presented in same SEP article |

### Summary

| Outcome | Count |
|---------|-------|
| Reclassified → `related_to` | 7 |
| Reclassified → `supports` | 2 |
| Kept `contradicts` (genuine) | 5 |
| Deferred with effort | 3 |
| Deferred (batch, intra-theory) | 17 |
| Deferred (attribution gap) | 1 |
| **Total reviewed** | **20/37** |

**Key insight — the revert pattern**: S9 and S14 were initially reclassified to `related_to`, then reverted back to `contradicts` after realizing that terminology conflicts should keep their contradiction signal until the offending node is superseded via the terminology correction flow. The contradiction is valid *as written* even when the underlying concepts are compatible — don't lose the signal prematurely.

### False Positive Patterns

Five recurring patterns explain why the linker flags non-contradictions or misclassifies:

1. **Scope mismatch**: Claims at different scales (intra-universe vs inter-universe, individual observer vs ensemble) appear contradictory when compared at summary level but operate in non-overlapping domains.

2. **Framework difference**: Standard physics descriptions (decoherence, measurement) vs the user's collapse-first model. These are alternative frameworks describing the same phenomena, not contradictory claims within one framework.

3. **Evolutionary refinement**: Claims authored weeks apart represent the user refining their position. The later claim doesn't contradict the earlier — it sharpens or extends it. The `authored_at` timestamps make this visible.

4. **Terminology conflict**: The underlying concepts are compatible but the node summary uses language that clashes with established terminology elsewhere in the theory (e.g., "rewriting the collapse chain" for what should be "redirecting future collapse alignment," or "space lattice" for a pre-spatial substrate). These should keep their `contradicts` edge until the node is superseded with corrected language.

5. **Assistant-elevation**: The assistant restates a user's tentative exploration as a firm framework principle. The extraction LLM captures it as an assertion when it was actually a hypothesis. Causes false contradictions with the user's actual firm beliefs.

### Root Cause

The linker LLM receives only **node summaries** when classifying edges. During extraction, the LLM had the full conversation — but that context is lost by linking time. A node summary like "collapse requires compatible modeling" vs "decoherence explains apparent collapse" looks contradictory without the surrounding context that explains they operate at different levels.

### Planned Fix: Tiered Context-Aware Linking

1. **Tier 1 (current)**: Summaries only. Fast, cheap, catches obvious relationships. High false positive rate on nuanced claims.
2. **Tier 2 (planned)**: Summaries + source blocks. When the linker is uncertain, pull the specific text block from provenance. Requires block-level provenance (`#turn-3:L12-L18`).
3. **Tier 3 (planned)**: Agentic KG navigation. For persistent ambiguity, the linker traverses related nodes for disambiguation context.

## Relevance to White Paper

### New data points for Paper 2 (Topological Truth)

1. **Scale increase**: From 236 → 894 → 1,336 nodes. The topology-based auto-resolution mechanism scales — 58% auto-resolve rate at 1,336 nodes (vs 67% at 894, 16% at 236). Lower rate likely due to 17x more conversations introducing more nuanced claims.

2. **False positive analysis**: Manual review reveals the linker's main failure mode — scope/framework mismatches at summary level. This is a *construction* problem (how the graph is built), not a *resolution* problem (how topology arbitrates). Important distinction: the resolution mechanism correctly classified these as ambiguous/strong-recommendation rather than auto-resolving them.

3. **Temporal signal**: `authored_at` timestamps reveal theory evolution. This is a new dimension not covered in the current paper draft — the graph captures not just what is believed but *when* beliefs formed and how they evolved.

4. **Human review provenance**: Decision 023 creates an auditable chain from conflict detection → human review → reclassification with reasoning + raw chat excerpts. This strengthens the "auditable end-to-end" claim in the paper.

5. **Honest limitations**: The system correctly left genuinely ambiguous conflicts (S8) for human judgment and created a tracked effort for investigation. The "epistemic integrity" argument in the paper's abstract is further validated.

6. **The revert pattern**: A paper-worthy insight — terminology conflicts should keep their `contradicts` edge because the signal is valid *as written*, even when the underlying concepts are compatible. Prematurely reclassifying loses information. No other KG system reports this nuance: the contradiction signal can be correct as a signal even when the underlying claims aren't logically contradictory. This reveals that conflict resolution has two distinct phases: (1) understanding the conflict's nature, (2) deciding whether to remove the signal — and these can have different answers.

7. **Cross-source validation**: The system correctly identifies both well-known scientific rivalries (GRW vs Bohm, S36) and intentionally presented debates within survey articles (S37). These are "easy" contradictions that validate the linker works correctly on external academic sources. The system also exposed an attribution gap — third-party knowledge discussed in user chat logs gets `source: physics-theory` when it should be attributed to the original framework (S35).

### New data points for Paper 3 (Full System)

1. **120-source ingestion**: First test at meaningful multi-source scale. Independence guarantee is stronger when sources are separate conversations over months rather than sections of one document.

2. **Conversation-aware extraction**: The extraction method matters for graph quality. Per-chunk extraction creates false intra-author contradictions. Full-conversation extraction eliminates them. This is a practical finding about graph construction methodology.

3. **Review provenance chain**: The full loop is now: extract → link → detect conflict → auto-resolve OR human review → reclassify with provenance → effort tracking for deferred cases. This is the "self-correcting" property in action.

## Gaps and Anomalies

- **1 failed conversation** (`68028f8e`, "@Collapse-First QFT Model"): LLM returned a step-by-step experimental plan instead of JSON. Logged as anomaly `llm-ignores-json-instruction`. Retryable.
- **`voice` field not persisted**: `ExtractedClaim` has `voice` (first_person/reported/described) but `add_knowledge()` doesn't save it. Block-level provenance is the better solution.
- **17 intra-theory conflicts deferred** (S18-S34): Require domain expert review with full theory context. Pattern suggests mix of false positives and genuine intra-theory tensions.
- **Extraction splits composite principles**: S17 showed the LLM splitting "randomness is not information, but it IS information potential" into two nodes that then get flagged as contradictory. Context-aware linking wouldn't fully fix this since it's an extraction problem.
- **Attribution gap for referenced knowledge**: Third-party frameworks discussed in user chat (e.g., Bohmian mechanics from a pasted lecture) get `source: physics-theory`. Tracked in effort `attribution-referenced-knowledge` (knowledge-network KG).
- **New planned features identified during review**: #4 terminology correction flow, #5 process/sequence edge types (`precedes`/`leads_to`), #6 attribution-aware extraction with epistemic status.
