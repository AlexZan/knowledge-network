# Three-Way Interaction Analysis: Theory vs Collapse vs QM Foundations

**Date**: 2026-03-05 (initial), 2026-03-06 (post-resolution update)
**KG**: `/data/physics-theory-kg/`
**Sources**: 7 author conversations + SEP Collapse Theories + SEP Philosophical Issues in QT

## Post-Resolution Update (2026-03-06)

After auto-resolving 110 conflicts (see [conflict-resolution-findings.md](conflict-resolution-findings.md)):

| Metric | Pre-resolution | Post-resolution |
|--------|---------------|-----------------|
| Active nodes | 894 | 845 |
| Superseded nodes | 0 | 49 |
| Theory nodes | 730 | 667 |
| SEP-collapse nodes | 66 | 63 |
| SEP-QT nodes | 98 | 95 |
| Concept nodes | — | 20 |
| Cross-author contradicts edges | 31 | 1 |
| Three-way agreement nodes | 3 | 3 (unchanged) |
| Three-way disagreement nodes | 4 | 0 (all resolved) |

**Key changes**: The 4 previously-identified "battleground" nodes (fact-016, -017, -019, -028) all survived — they remain active. Their cross-author `contradicts` edges were resolved by superseding the weaker side of each pair, not by removing the core theory nodes. The topology correctly identified the author's claims as better-supported within the graph.

Only 1 cross-author contradicts edge remains (between a collapse theory meta-claim and a theory node about QBism). 37 intra-theory contradicts edges remain — these are internal tensions within the author's own reasoning across conversations.

## Why This Matters for the Paper

The two-way analysis (theory vs collapse) showed where the theory agrees and disagrees with one competing framework. The three-way analysis reveals something deeper: **different sources challenge the theory at different levels of depth**, and the system can distinguish between them mechanically.

## Edge Distribution by Source Interaction

### Pre-resolution (894 nodes)

| Category | supports | contradicts | related_to | exemplifies | Total |
|----------|:--------:|:-----------:|:----------:|:-----------:|:-----:|
| intra-theory | 1105 | 132 | 2742 | 41 | 4020 |
| intra-SEP-QT | 28 | 0 | 189 | 0 | 217 |
| intra-SEP-collapse | 30 | 0 | 69 | 0 | 99 |
| theory ↔ QT | 11 | 7 | 368 | 0 | 386 |
| theory ↔ collapse | 24 | 24 | 245 | 0 | 293 |
| collapse ↔ QT | 0 | 0 | 5 | 0 | 5 |

### Post-resolution (845 active nodes)

| Category | supports | contradicts | related_to | exemplifies | Total |
|----------|:--------:|:-----------:|:----------:|:-----------:|:-----:|
| intra-theory | 1017 | 37 | 2542 | — | 3596 |
| intra-SEP-QT | 27 | 0 | 186 | — | 213 |
| intra-SEP-collapse | 30 | 0 | 69 | — | 99 |
| theory ↔ QT | 9 | 0 | 358 | — | 367 |
| theory ↔ collapse | 24 | 1 | 243 | — | 268 |
| collapse ↔ QT | 0 | 0 | 4 | — | 4 |
| concept ↔ theory | — | — | — | 38 | 38 |

**Resolution impact on contradicts edges**: 132 → 37 intra-theory, 7 → 0 theory↔QT, 24 → 1 theory↔collapse. Total: 163 → 38.

### Key Observations

1. **The two SEP articles barely connect to each other** (5 edges, all `related_to`). They cover different aspects of the same field without directly contradicting each other. The system correctly treats them as independent perspectives.

2. **The QT article has broader topical overlap** (386 edges vs 293) but **fewer contradictions** (7 vs 24). It describes the landscape of interpretations rather than advocating a specific mechanism.

3. **Zero intra-SEP contradictions.** Both SEP articles are internally consistent (they're encyclopedic references), and the system correctly finds no internal tensions.

## Three-Way Agreement (3 nodes)

Three theory nodes are supported by **both** SEP articles — validated from two independent mainstream perspectives:

| Node | Body | Collapse supports | QT supports |
|------|------|:-----------------:|:-----------:|
| fact-013 | Photon detector causes interference pattern to disappear | 2 | 2 |
| fact-016 | Detector as entropic system with collapse seed | 4 | 1 |
| fact-059 | Standard QM doesn't specify collapse mechanism | 3 | 1 |

**fact-016 is the most remarkable**: the author's core claim about entropy-driven collapse receives support from *both* SEP sources while also being contradicted by both (see below). It's the central battleground.

## Three-Way Disagreement (4 nodes → 0 after resolution)

Before conflict resolution, four theory nodes were contradicted by **both** SEP articles:

| Node | Body | Why collapse objects | Why QT objects |
|------|------|---------------------|----------------|
| fact-016 | Detector as entropic collapse seed | GRW collapse is spontaneous, detector-independent | Everett rejects collapse entirely; Bohm denies collapse |
| fact-017 | Photon conditions collapse, doesn't detect | GRW: collapse is random, not conditioned | Bohm: no collapse to condition; pilot wave guides |
| fact-019 | Screen as first collapse-inducing system | GRW: collapse not triggered by measurement | Everett: no collapse; Bohm: screen reveals position |
| fact-028 | Collapse-Conservation principle | GRW: no entropy condition needed | von Neumann: distinction is conventional, not physical |

**Post-resolution**: All 4 theory nodes survived (remain active). The weaker side of each cross-author `contradicts` pair was superseded — the SEP nodes that contradicted these theory claims had less topological support within the graph (which is dominated by the author's 667 theory nodes). This is expected: the graph reflects what *this* knowledge base supports, not what the broader physics community agrees on.

**fact-016 was simultaneously in three-way agreement AND three-way disagreement** (pre-resolution). Both sources supported parts of the claim (detection causes physical changes) while contradicting other parts (the specific mechanism). After resolution, the support edges remain but the contradiction edges are resolved — the nuanced "partially agrees" signal is now captured as support-only plus the supersedes audit trail.

## The Depth Gradient: Family Disputes vs Foundational Challenges

The most important finding for the paper:

### Collapse article contradictions (24): "How does collapse work?"

All 24 contradictions share the assumption that **collapse is real**. They disagree about the *trigger mechanism* — spontaneous (GRW) vs conditional (author's theory). These are **family disputes** within the collapse interpretation camp.

### QT article contradictions (7): "Does collapse even happen?"

The 7 contradictions come from two fundamentally different objections:

1. **Everett/Many-Worlds** (3 contradictions): Collapse never happens. All branches persist. The theory's entire framework — entropy-triggered collapse, screens as collapse-inducing systems — is rejected at the ontological level.

2. **de Broglie-Bohm/Pilot Wave** (3 contradictions): Collapse never happens. Particles have definite trajectories guided by the wave function. Detectors don't cause collapse; they reveal pre-existing positions.

3. **Von Neumann's conventionalism** (1 contradiction): The Process 1/Process 2 distinction (collapse vs unitary evolution) is not a fundamental physical difference but depends on somewhat arbitrary observer/observed divisions. The author's Collapse-Conservation principle treats this distinction as fundamental physics.

**The QT contradictions are fewer but more structurally threatening.** The collapse article challenges the author's mechanism; the QT article challenges the author's foundational premise.

## QT-Unique Insights

### Tensions the collapse article couldn't surface

- **fact-025** ("electron remains coherent until collapse at screen") is supported by the collapse article (GRW also posits collapse) but contradicted by the QT article (Everett says collapse never happens). The two-way analysis missed this — only the three-way comparison reveals it.

### Validations the collapse article couldn't provide

- **fact-018** ("without entropic system, electron retains full wavefunction") is contradicted by collapse (GRW: collapse is universal) but supported by QT (von Neumann's Process 2: unitary evolution in absence of measurement). The standard QM formalism actually supports the author's conditional framing even though GRW rejects it.

- **fact-120** ("collapse occurs when environment is large enough") is supported by QT's decoherence framework (environmental entanglement) but has no collapse article edge at all. Decoherence is a different lens that validates the author's size-dependent threshold idea without invoking GRW mechanics.

## Contact Surface Comparison

| Metric | Collapse | QT |
|--------|:--------:|:--:|
| Theory nodes with any cross-edge | 34 (4.8%) | 42 (5.7%) |
| Cross-author contradictions | 24 | 7 |
| Cross-author supports | 24 | 11 |
| Cross-author related_to | 245 | 368 |

The QT article has broader topical contact (42 vs 34 nodes, 368 vs 245 related_to) but a more targeted contradiction pattern (7 vs 24). It's a survey article, so it connects widely but only contradicts where it describes alternatives to collapse.

## Implications for the White Paper

### 1. Multi-Source Triangulation Works

The system demonstrates genuine triangulation — not just "more sources = more edges" but qualitatively different insights from different perspectives. The collapse article reveals mechanism disagreements; the QT article reveals foundational challenges. Neither alone tells the full story.

### 2. Depth of Contradiction Is Detectable

The knowledge graph captures a gradient of disagreement:
- **Surface**: related_to (topical overlap, no commitment)
- **Mechanism**: contradicts from collapse article (disagrees about *how*)
- **Foundational**: contradicts from QT article (disagrees about *whether*)

A future pipeline improvement could classify contradiction depth automatically.

### 3. The "Battleground Node" Pattern

fact-016 (entropic collapse seed) is simultaneously supported and contradicted by both SEP articles. This pattern — a node that receives both support and contradiction from multiple independent sources — indicates a genuinely contested claim at the frontier of the field. The system surfaces this mechanically.

### 4. Cross-Source Independence

The two SEP articles barely connect to each other (5 edges). They provide genuinely independent perspectives on the theory. This validates the experimental design — the cross-author sources aren't just echoing each other.
