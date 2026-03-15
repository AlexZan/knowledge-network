# Auto-Resolution Sample Review: Findings

**Date**: 2026-03-14
**Scope**: Stratified sample of 15/113 V3 auto-resolved conflicts
**Data file**: `docs/research/auto-resolution-sample-review.md`

## Findings

### 1. Duplicate node inflation

fact-222 ("Consciousness is the recursive accumulation and projection of collapse history, actively shaping how deterministic systems resolve") has 1 raw supporter — fact-250 ("Consciousness is the recursive projection and shaping of collapse history..."). These are the same claim paraphrased. The linker classified them as `supports` instead of recognizing them as near-duplicates.

fact-250 has a high PageRank score, so its weighted contribution inflates fact-222's support to 14.5x — well above the 5x auto-resolution threshold. The resolution outcome was correct (domain expert confirmed), but the mechanism relied on a tautological supporter rather than genuine independent convergence.

### 2. False positive in auto-resolution: scope mismatch bypasses threshold

fact-057 ("Consciousness aligns with entropy injection and participates in collapse; observation is not a neutral measurement but a participatory collapse guided by the observer's unique collapse history") superseded fact-1139 ("A GRW collapse leaves the wavefunction with non-zero amplitude at all locations, resulting in 'tails'") at 33.4:0.0.

These are not actually contradictory. fact-057 is a broad claim about consciousness participating in collapse. fact-1139 is a narrow mathematical property of the GRW model (wavefunction tails). The linker created a false `contradicts` edge — a scope mismatch between a philosophical claim and a technical detail. The topology then auto-resolved it because the author's well-supported claim had overwhelming support vs an isolated SEP node with 0 supporters.

The 5x threshold protects against false positives when support is *close*, but cannot help when a well-supported node is falsely linked to an isolated one from a different source. This is the first confirmed false positive in auto-resolution from the sample.

### 3. No resolution audit trail

`auto_resolve()` does not log the weighted support values at resolution time. There is no way to reconstruct what ratios the algorithm saw when it made each decision. Post-hoc verification required restoring superseded nodes to approximate the pre-resolution graph state, which is imprecise.

### 3. No pre-resolution snapshot

No backup of `knowledge.yaml` is saved before `auto_resolve()` runs. The only way to analyze pre-resolution state is to approximate it by un-superseding nodes, which doesn't restore removed `contradicts` edges and changes PageRank distributions.
