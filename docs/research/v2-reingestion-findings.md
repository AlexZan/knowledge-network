# V2 Re-ingestion Experiment: Full Pipeline with Cross-Author Source

**Date**: 2026-03-05
**KG**: `/mnt/storage/physics-theory-kg/`
**Pipeline features active**: Decisions 019 (contradicts gate), 020 (salience, edge weights, concept nodes), 021 (LLM audit trail)

## Experiment Design

Wiped the physics theory KG and re-ingested all sources from scratch with the full current pipeline. Goal: measure the impact of all pipeline improvements (Decisions 019, 020, 021) on graph quality, and test cross-author source interaction.

### Sources Ingested

| # | Source | Type | Nodes |
|---|--------|------|:-----:|
| 1 | 67ee77df (conv 1) | ChatGPT conversation | 10 |
| 2 | 67f39b61 (conv 2) | ChatGPT conversation | 74 |
| 3 | 67f0f25e (conv 3) | ChatGPT conversation | 140 |
| 4 | 680bcd45 (conv 4) | ChatGPT conversation | 75 |
| 5 | 6810c74f (conv 5) | ChatGPT conversation | 276 |
| 6 | 6813ea48 (conv 6) | ChatGPT conversation | 74 |
| 7 | 68165f32 (conv 7) | ChatGPT conversation | 61 |
| 8 | sep-collapse-theories.md | SEP article (Ghirardi/Bassi) | 66 |

**Total cost**: ~$2-3 on Cerebras (gpt-oss-120b), 8 ingestion runs.

---

## V1 vs V2 Comparison

| Metric | V1 (5 docs, pre-D019/020) | V2 7-conv only | V2 + cross-author |
|--------|:-------------------------:|:--------------:|:-----------------:|
| Active nodes | 712 | 710 | 776 |
| Total edges | 3895 | 3979 | 4371 |
| supports | 1398 | 1105 | 1159 |
| related_to | 2338 | 2742 | 3056 |
| contradicts | 159 | 132 | 156 |
| High confidence | 26 | 15 | 17 |
| Contested | 19 | 25 | 27 |

### Key Observations

1. **supports decreased, related_to increased**: Decision 019's contradicts gate and improved linker prompts are reclassifying weak agreements as `related_to` instead of `supports`. The support edges that remain are higher quality.

2. **contradicts decreased (159→132 for same content)**: The contradicts gate is filtering out false positive contradictions. Adding the SEP article brought it back up to 156 — the increase (24 new contradictions) is entirely cross-author disagreements.

3. **High confidence decreased (26→17)**: Decision 020's reasoning-weighted PageRank makes unreasoned support edges worth 0.5x, so nodes need more/better support to reach high confidence. This is working as designed — high confidence should be harder to achieve.

4. **Contested increased (19→27)**: Two factors: (a) reasoning weights shifting some nodes from medium to contested, (b) new cross-author contradictions. Needs deeper analysis (see below).

---

## Contested Node Deep Dive (27 nodes)

### Classification

| Category | Count | % | Description |
|----------|:-----:|:--:|-------------|
| Theory evolution | 12 | 44% | Author's theory refined across conversations |
| Within-theory tension | 7 | 26% | Internal tension at different abstraction levels |
| Theory vs mainstream | 5 | 19% | Genuine theory-vs-GRW/standard-physics conflicts |
| False positive | 3 | 11% | Linker error or scope mismatch |

### False Positive Rate

| Version | Contested | False Positives | Rate |
|---------|:---------:|:---------------:|:----:|
| V1 (5 docs) | 19 | 0 | 0% |
| V2 (8 sources) | 27 | 3 | 11% |

The false positive rate increased with cross-author content. All 3 false positives involve scope/framing mismatches:

1. **fact-127**: "Interference lost in subset" contradicted by "interference present in total data" — compatible claims at different scopes (subset vs total).
2. **fact-293**: Mathematical definition of readiness function contradicted by philosophical claim about probability — different levels (formalism vs ontology).
3. **fact-360**: "Lensing anomalies expected where collapse-density gradient exists" marked as contradicted by standard model lensing — but fact-360 is explicitly proposing an alternative, not claiming agreement.

**Implication**: The contradicts-gate prompt needs better scope/framing awareness for cross-author comparisons. The linker correctly identifies tension but sometimes points the `contradicts` edge at the wrong target (the prediction rather than the standard model it challenges).

### Most Contested Node

**fact-017**: "Photon conditions collapse rather than detecting the electron"
- 54.35 weighted supports vs 68.31 weighted contradicts
- 12 contradicting edges from 4 sources
- The core theory claim, contested by SEP's GRW spontaneous collapse model, standard detector models, and some of the author's own evolving claims
- **Assessment**: Correctly contested — this is the central point of disagreement between the theory and GRW/CSL

### Theory Evolution Examples (12 nodes)

The graph correctly tracks how ideas evolved across conversations:

- **Injected vs emergent randomness**: Early claim (conv 2) that parent universe sends random entropy contradicted by later claim (conv 5) that randomness emerges from insufficient causal constraints
- **Anchor lifecycle**: "Anchors deactivate immediately" (conv 5 early) contradicted by "anchors are permanent" (conv 5 late)
- **Speed of light**: "Haven't modeled speed limit yet" contradicted by 4 nodes from conv 4 that define speed of light as causal saturation constant
- **Nature of first fluctuation**: "Not a concrete thing, just a role" (conv 4) vs "creates a concrete binary anchor" (conv 5)

These are genuine contradictions — the theory evolved, and the graph is the historical record of that evolution.

### Only 2 of 19 Original Contested Nodes Survived

The SEP article and Decision 020's reasoning weights reshuffled the contested set almost entirely. This demonstrates that adding new evidence sources genuinely changes the confidence landscape — the graph is dynamic, not static.

---

## Cross-Author Interaction Analysis

See also: [cross-author-analysis.md](cross-author-analysis.md) for the full writeup.

### Edge Summary: SEP → Theory

| Type | Count |
|------|:-----:|
| related_to | 245 |
| supports | 24 |
| contradicts | 24 |

All 293 cross-author edges flow SEP → theory (none in reverse). The linker found dense topical connections with a balanced support/contradiction split.

### Contact Surface

Only **34 of 710 theory nodes (4.8%)** have any cross-author edges. All 34 cluster around the double-slit experiment and collapse mechanism. **95.2% of the theory exists in territory GRW/CSL don't address.**

### What the SEP Validates

1. **Observer-independence of collapse** — 5 support edges from SEP fact-654 alone
2. **The measurement problem is real** — consensus physics, expected
3. **Detection devices trigger collapse through physical interaction** — amplification mechanism aligns
4. **Collapse introduces energy** — both frameworks acknowledge this

### What the SEP Challenges

**22 of 24 contradictions** trace to one fundamental disagreement:

- **Author's theory**: Collapse is conditional — requires an entropic system, determinism meeting patterned entropy
- **GRW/CSL**: Collapse is unconditional — spontaneous, universal, happens to all matter

This is a clean theoretical fork: same diagnosis (measurement problem), different prescription (conditional vs unconditional trigger).

### Cross-Author Contradiction Quality

| Contradicts | False Positives | Rate |
|:-----------:|:---------------:|:----:|
| 24 | 1 | 4% |

The one false positive: fact-687 vs fact-107 (QBism framing mismatch — both sources actually agree that observer-dependent collapse is undesirable, but the linker missed that the theory was criticizing, not advocating, observer-dependence).

### What's Genuinely Unique (No SEP Counterpart)

The 95% of theory nodes with zero cross-author contact cluster into:

1. **Parent/child universe cosmology** — black holes as randomness engines, child universe seeding
2. **Anchors and fluctuations** — novel ontological primitives with no GRW/CSL analog
3. **Dark matter/energy replacement** — rotation curve fits, void expansion equations
4. **Emergence of spacetime** — distance as emergent from causal closure
5. **Named formal principles** — Structural Bias Principle, Collapse-Conservation, Recursive Randomness, Null Catalyst
6. **Inflation redefined** — collapse-bandwidth saturation mechanism
7. **Simulation framework** — concrete grid simulations with gamma fields, bias kernels
8. **Research process meta-layer** — 34 decisions + 52 preferences (no SEP analog)

---

## Pipeline Performance

### JSON Parse Errors

1 of 111 chunks (0.9%) failed with "Expecting ',' delimiter" during conv 6 ingestion. Same anomaly pattern as previous occurrences (see `anomalies.yaml`, entry `llm-json-truncation`). Fixed by adding missing-comma repair to `_parse_llm_json()`.

### LLM Audit Trail

Decision 021's `llm_log.jsonl` captured all LLM calls. File located at `{OI_SESSION_DIR}/llm_log.jsonl`.

### Document Skip (Resume/Checkpoint)

The `skip_existing` feature worked correctly for re-runs during the experiment, preventing duplicate ingestion after the cross-source-id bug was fixed (see [ingestion-resume-findings.md](ingestion-resume-findings.md)).

---

## Implications for the White Paper

1. **Multi-source validation works**: The system correctly identifies shared premises (supports) and genuine disagreements (contradicts) between independent frameworks, while leaving unrelated content unconnected.

2. **Cross-author testing reveals theory uniqueness**: 95% of the theory has no contact with standard collapse physics — it extends into cosmology, emergence, and novel ontology that GRW/CSL don't address.

3. **Contested nodes are mostly real**: 89% of contested nodes represent genuine tensions (theory evolution, within-theory, or theory-vs-mainstream). The 11% false positive rate with cross-author content suggests room for prompt improvement.

4. **Confidence calibration improved**: Decision 020's reasoning weights make high confidence harder to achieve (26→17), which is correct behavior — unreasoned agreement shouldn't carry full weight.

5. **The graph is dynamic**: Adding a single cross-author source (66 nodes) reshuffled the contested set almost entirely (only 2 of 19 survived). Evidence genuinely updates beliefs in this system.

---

## Next Steps

1. **Ingest standard QM foundations text** (SEP "Philosophical Issues in Quantum Theory") for three-way interaction
2. **Run conflict resolution** on the v2 graph (free, no LLM calls)
3. **Analyze three-way interactions** — where do all three sources agree? Where does each stand alone?
4. **Update the white paper** with multi-source empirical data
