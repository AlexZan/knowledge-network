# Cross-Author Analysis: Physics Theory vs SEP "Collapse Theories"

**Date**: 2026-03-05
**KG Version**: v2 (776 nodes, 4371 edges)
**Sources**: 7 ChatGPT conversations (author's physics theory) + 1 SEP article (Ghirardi/Bassi on GRW/CSL collapse theories)

## Experiment Design

Ingested the Stanford Encyclopedia of Philosophy article on collapse theories as a cross-author source into a knowledge graph already containing the author's physics theory (7 conversations). The goal: test whether the system can identify genuine points of agreement and disagreement between independent frameworks, and reveal what's unique about the author's theory.

## Cross-Author Edge Summary

| Edge Type | Count | Direction |
|-----------|:-----:|-----------|
| related_to | 245 | SEP -> theory |
| supports | 24 | SEP -> theory |
| contradicts | 24 | SEP -> theory |
| **Total** | **293** | All unidirectional |

The SEP article (66 nodes) connected to only **34 of 710 theory nodes** (4.8%). The remaining 95.2% of theory nodes had zero cross-author edges.

## Contact Surface

The 34 connected theory nodes cluster entirely around the **double-slit experiment** and **collapse mechanism** — the narrow overlap between the two frameworks.

Most-connected theory nodes (by cross-author edge count):

| Node | Edges | Body |
|------|:-----:|------|
| fact-016 | 34 | Photon detector as entropic system with collapse seed |
| fact-013 | 31 | Photon detector causes interference pattern to disappear |
| fact-019 | 28 | Screen acts as first collapse-inducing system |
| fact-022 | 25 | Collapse injects patterned entropy from detector |
| fact-028 | 24 | Collapse only when determinism meets irreducible patterned entropy |

## What the SEP Validates

**24 support edges** cluster around shared premises:

1. **Observer-independence of collapse** — Both frameworks agree consciousness plays no special role. The SEP's GRW/CSL description (collapse is physical, not mental) directly supports the theory's entropy-driven, observer-free collapse.

2. **The measurement problem is real** — Both agree standard QM's two incompatible evolution rules (Schrodinger + collapse postulate) are a genuine problem requiring resolution.

3. **Detection devices trigger collapse through physical interaction** — The SEP's amplification mechanism aligns with the theory's detector-as-entropic-system model.

4. **Collapse introduces energy** — The SEP acknowledges GRW/CSL inject energy via stochastic noise, validating the theory's entropy-injection claim.

### Purely validated nodes (supported, never contradicted):
- fact-059: Standard QM doesn't specify collapse mechanism
- fact-124: Detection alone suffices for collapse (no human needed)
- fact-066: Standard QM assumptions about superposition and collapse
- fact-014: Measurement collapses the wavefunction

## What the SEP Challenges

**22 of 24 contradictions** trace to a single fundamental disagreement:

**Conditional vs. unconditional collapse**
- **Author's theory**: Collapse requires specific conditions — entropic system present, determinism meeting patterned entropy, model-target alignment
- **GRW/CSL**: Collapse happens spontaneously, universally, unconditionally to all matter

Three SEP nodes drive this:
- fact-631 (GRW random localizations) → 8 contradicts
- fact-650 (universal spontaneous collapse) → 8 contradicts
- fact-638 (collapse not triggered by measurement) → 6 contradicts

Remaining 2 contradictions:
- **Randomness origin**: GRW injects stochastic noise vs. theory's emergent randomness from insufficient causal constraints
- **False positive** (1): QBism framing mismatch — linker missed that the theory was criticizing observer-dependent collapse, not advocating it

## What's Genuinely Unique (No SEP Counterpart)

95% of the theory has no contact with GRW/CSL. These concepts exist in territory collapse theories don't enter:

### 1. Parent/Child Universe Cosmology
Black holes as randomness engines seeding child universes. The theory extends collapse physics into a full cosmological ontology. GRW/CSL make no cosmological claims.

### 2. Anchors and Fluctuations
Novel ontological primitives — binary relational pointers (anchors) that store memory of prior collapse influences, and causeless execution commands (ticks) from the parent universe. No GRW/CSL analog.

### 3. Dark Matter/Energy Replacement
Rotation curve fits via "collapse curvature" without dark matter halos. Void expansion from collapse-density gradients with derived equations (H_eff). GRW/CSL make no astrophysical predictions.

### 4. Emergence of Spacetime
Spatial distance as emergent from degree of causal closure between recursive structures. Entirely absent from standard collapse theory.

### 5. Named Formal Principles
- Structural Bias Principle
- Collapse-Conservation
- Recursive Randomness
- Null Catalyst

Four named principles with no analog in GRW/CSL.

### 6. Inflation Redefined
Cosmic inflation as a runaway burst of collapses outpacing causal bandwidth, ending when anchors exceed resolution. Novel mechanism.

### 7. Simulation Framework
Concrete grid simulations with gamma fields, bias kernels, collapse thresholds, and SPARC rotation curve fitting. The theory is computationally testable in ways GRW/CSL are not.

### 8. Research Process (Meta-Layer)
34 decision nodes and 52 preference nodes capture the theory's development methodology. The SEP article, as an encyclopedic reference, contains only facts.

## Key Insight

The theory is not a GRW/CSL variant. It shares a thin contact surface around the measurement problem (same diagnosis), then proposes a fundamentally different mechanism (conditional entropy-triggered collapse vs. unconditional spontaneous collapse) and extends into cosmology, emergence, and simulation — territory standard collapse theories don't enter.

The knowledge graph correctly:
- Identified the precise mechanistic fork (conditional vs unconditional)
- Validated shared premises without forcing false agreement
- Left 95% of original territory unconnected (no false relationships)
- Distinguished between the SEP *reporting* GRW theory (voice: reported) and the theory *proposing* alternatives (voice: authored)

## False Positive Assessment

| Source | Contradicts | False Positives | Rate |
|--------|:-----------:|:---------------:|:----:|
| Cross-author | 24 | 1 | 4% |
| Full KG | 156 | 3 | ~2% |
| Prior v1 | 159 | 0 | 0% |

The false positive rate increased slightly with cross-author content, suggesting the contradicts-gate prompt could benefit from better scope/framing awareness when comparing secondary sources against primary claims.

## Comparison: V1 vs V2

| Metric | V1 (5 docs, 643 nodes) | V2 (8 sources, 776 nodes) |
|--------|:----------------------:|:-------------------------:|
| Active nodes | 712 | 776 |
| Total edges | 3895 | 4371 |
| supports | 1398 | 1159 |
| related_to | 2338 | 3056 |
| contradicts | 159 | 156 |
| High confidence | 26 | 17 |
| Contested | 19 | 27 |
| False positives | 0 (0%) | 3 (11% of contested) |

The contested count increase (19 → 27) reflects both new cross-author tensions and Decision 020's reasoning-weighted PageRank making unreasoned support edges worth 0.5x, shifting some nodes from medium to contested.

## Next Steps

1. Ingest a standard QM textbook/article as a third perspective — test three-way interaction
2. Run conflict resolution on the v2 graph
3. Investigate the 3 false positives for contradicts-gate prompt improvements
