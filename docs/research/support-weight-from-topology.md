# Support Weight from Topology: Replacing LLM Judgment with Graph Structure

**Date:** 2026-03-14
**Status:** Brainstorm — not yet implemented
**Context:** Auto-resolution review found duplicate nodes inflating PageRank support (see `auto-resolution-review-findings.md`). Brainstormed how to fix, arrived at topology-based support weighting.

## The Problem

Two near-identical nodes (paraphrases of the same claim) get linked as `supports` by the LLM linker. Because one of them has high PageRank (well-connected), it inflates the other's support score — a tautological supporter driving auto-resolution.

**Real case from v3 KG:** fact-222 ("Consciousness is the recursive accumulation and projection of collapse history") was supported by fact-250 ("Consciousness is the recursive projection and shaping of collapse history"). Same claim, different words. The linker classified it as `supports` because it had no "duplicate" category. fact-250's high PageRank inflated fact-222's weighted support to 14.5x, triggering auto-resolution.

## The Reasoning Path

### Attempt 1: Binary duplicate detection

Initial proposal: cosine similarity > 0.95 → classify as duplicate, don't count as support.

**Problem:** Duplicate is binary, but the real world isn't. "F=ma" and "F=ma, which I derived from Newton's second law" isn't a duplicate — it has one extra detail. But that detail adds zero evidential value. A binary duplicate/not-duplicate split would miss this case.

### Attempt 2: LLM-scored support strength

Add a `strength` field to linker output: `{"edge_type": "supports", "strength": 0.8, "reasoning": "..."}`. LLM assesses how much unique value B adds to A on a 0.0-1.0 scale.

**Problem:** This puts a continuous judgment in the LLM's hands. LLMs are good at categorical classification (supports/contradicts/none) but unreliable at numeric scoring. They cluster at round numbers and aren't consistent across runs. And it violates the project thesis — confidence should emerge from topology, not LLM judgment.

### Attempt 3: New edge type "restates"

Add `restates` as a linker classification. Paraphrases get `restates` edges with zero confidence weight. Real support gets `supports` edges with full weight.

**Problem:** Still binary. A claim that adds a tiny amount of new information doesn't fit neatly into either `restates` or `supports`. The boundary between them is fuzzy.

### Attempt 4: Topology-based support weight (current proposal)

**Key insight:** The LLM classifies the TYPE of relationship (supports/contradicts/related_to/none). The STRENGTH of that relationship is computed from graph topology. No LLM judgment in the confidence calculation.

## The Proposal

### Separation of concerns

- **LLM decides WHAT**: Is this relationship supports, contradicts, related_to, or none? (Categorical — LLMs are good at this)
- **Topology decides HOW MUCH**: How much should this `supports` edge contribute to confidence? (Continuous — computed from structure)

### Two topological signals

**1. Embedding dissimilarity (content novelty)**

How different is the content of the two nodes?

- Cosine ~0.95+ → paraphrase → near-zero weight
- Cosine ~0.70 → related but different framing → moderate weight
- Cosine ~0.50 → different evidence for same conclusion → high weight

High cosine similarity = saying the same thing = redundant = low weight.
Low cosine similarity = different content = novel information = high weight.

**2. Source independence (provenance distance)**

How far apart are the nodes in provenance?

- Same conversation → low weight
- Different conversation, same author → moderate weight
- Different author / source type → high weight

Same source = likely restating. Different source = likely independent evidence.

### Combined weight examples

**Claim A: "Wavefunction collapse is irreversible"**

| Claim B | Cosine | Source | Weight | Why |
|---------|--------|--------|--------|-----|
| "Collapse cannot be reversed" | 0.96 | same conv | ~0.0 | Paraphrase from same context |
| "In my framework, phase info is destroyed" | 0.72 | same author, diff conv | ~0.4 | New mechanism, but same author repeating |
| "Zurek's decoherence shows irreversibility" | 0.55 | different author (SEP) | ~0.9 | Independent theory, different source |
| "PTB 2019 experiment confirmed no reversal" | 0.45 | different source type | ~1.0 | Independent empirical evidence |

### Two independent quality signals in PageRank

With this approach, confidence gets two topological inputs per edge:

1. **Edge weight** (embedding dissimilarity + source independence): Is this support redundant or novel?
2. **Supporter's own PageRank score**: Is the supporter itself well-supported?

Both are purely topological. The LLM's only role is edge-type classification.

## Edge Case: Dissimilarity ≠ Value

**Concern raised:** What about "x=y, and I realized this while eating overcooked chicken on the couch"?

Cosine similarity with "x=y" would be low (~0.3) because of all the irrelevant content. Our dissimilarity formula would give it HIGH weight — but it's obviously worthless as support.

**Resolution:** This case is handled at two layers:

1. **The linker wouldn't classify this as `supports`**. The chicken dinner content is irrelevant — the LLM would say `none` or `related_to`. The weight formula only applies to edges the LLM has already classified as `supports`. The LLM is good at this categorical judgment.

2. **Extraction should produce clean nodes.** "I ate overcooked chicken" has no knowledge value and shouldn't survive extraction. If the LLM bundles it with the real claim ("x=y, which I realized while eating chicken"), that's an extraction quality issue — the source_quote preserves the full context, but the node summary should be just "x=y".

So: the LLM guards the gate (only real support relationships get edges), and topology determines the weight. Irrelevant content never gets a `supports` edge in the first place.

## Edge Case: Small additions with no evidential value

**Concern raised:** "F=ma" vs "F=ma, which I derived from Newton's second law" — technically different, but the addition doesn't strengthen the claim.

**Resolution:** Handled correctly by topology:

- Cosine similarity would be high (~0.88) — most content is identical
- Same author, likely same conversation
- Computed weight: ~0.1

Near-zero contribution. Not exactly zero (the content IS slightly different), but barely moves the needle in PageRank. This is the right answer — it's not a perfect duplicate, but it's close enough that topology correctly diminishes it.

Additionally, clean extraction should produce one node, not two. "Which I derived from Newton's second law" is provenance context (how they arrived at F=ma), not a separate claim. It belongs in the source_quote or as a relationship edge from "Newton's second law" to "F=ma". Two layers of protection.

## Relationship to Existing Infrastructure

- **Edge weights exist** in `confidence.py` (Decision 020, slice 14a). Currently binary: 1.0 with reasoning, 0.5 without. Would be replaced with the computed topology weight.
- **Embeddings exist** via Ollama (nomic-embed-text). Cosine similarity is already used in `find_clusters()`.
- **Provenance URIs exist** on every node. Source independence is directly computable from provenance.
- **PageRank iteration** in `compute_all_confidences()` already uses edge weights. No algorithm changes needed — just better weights.

## Relationship to Hierarchy vs Network Discussion

This brainstorm also explored whether knowledge should be organized hierarchically (parent-child) or as a network. Key insight: **hierarchy only works when a concept is exclusively owned by one parent.** In practice, almost all knowledge cross-links — "photon frequency" relates to energy, wavelength, spectra, photoelectric effect. Forcing it under a "photon" parent hides those connections.

**Conclusion:** The only structural primitive needed is edges in a network. Different edge types provide different dimensions (semantic, logical, provenance). Hierarchy is a filtered VIEW over the network, not a storage structure. Compaction (principle nodes + exemplifies edges) provides zoom levels without imposing hierarchy.

This connects to Thesis 1 (conclusion-triggered compaction) applied recursively to the graph: dense neighborhoods compact into principle nodes, which can be expanded on demand. Different neighborhoods at different resolutions simultaneously — impossible with a tree, natural with a network.

## Implementation Notes (When Ready)

1. Requires embeddings to exist for all nodes before weight computation
2. Weight formula TBD — likely: `f(1 - cosine_similarity) * source_independence_factor`
3. Source independence scoring TBD — could be categorical (same conv / diff conv / diff author / diff source type) or continuous
4. Need to decide: compute weights at linking time (store on edge) or at confidence computation time (compute on the fly)?
   - At linking time: faster confidence computation, but weights are frozen
   - At confidence time: always fresh, but recomputes every time
5. Backward compatible: existing edges without weights default to current behavior (1.0/0.5 based on reasoning field)

## Open Questions

- What's the right function mapping cosine similarity to weight? Linear? Sigmoid? Step function with a few tiers?
- Should the two signals (embedding dissimilarity + source independence) be multiplied, added, or combined some other way?
- At what cosine threshold does a `supports` edge become effectively zero? 0.90? 0.95?
- Should `contradicts` edges also have topology-based weights, or is contradiction always binary?
- How does this interact with `because_of` edges (causal dependencies)?
