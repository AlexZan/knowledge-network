# Decision 018: Falsification Confidence Propagation

**Date**: 2026-03-03
**Status**: Accepted — architecture principle, implementation deferred to Rust port

---

## Context

The current confidence model is purely additive: more `supports` edges → higher confidence. This works well for everyday facts but breaks for scientific claims, where the epistemological rules are asymmetric.

The problem:

```
Theory T
├── supports × 100  (failed disproofs, confirming experiments)
└── contradicts × 1 (one empirical refutation)

Current confidence: very high (100:1 ratio)
Scientific verdict: DEAD
```

A single valid falsification is not just another vote. In Popperian falsificationism, one confirmed counterexample is sufficient to refute a universal claim — regardless of how many observations support it. The 10,000th white swan doesn't protect the "all swans are white" theory from the first black swan.

But hardcoding this asymmetry creates the opposite problem: a single unverified disproof would immediately collapse high-confidence theories. That's also wrong — one paper claiming to disprove something doesn't make it disproven.

## Insight

**The disproof is a first-class node, subject to the same topology-based confidence as any other claim.**

There are no "hard kills" in the system. The confidence in a refutation must itself propagate through the graph before that refutation affects the original claim. This is how science actually works:

1. Experiment E is published, claiming to falsify Theory T
2. E enters the graph as a new node with a `falsifies` edge to T
3. E starts with low confidence — one paper, no citations, no replications
4. T's confidence barely changes
5. E accumulates citations, independent replications, survives its own challenge attempts
6. E's confidence grows through topology
7. As E's confidence rises, its `falsifies` edge carries increasing weight against T
8. T's confidence falls proportionally
9. Eventually, if E reaches high confidence, T is effectively refuted by the graph

```
Early:
Theory T (conf: 0.85) ←── falsifies ── Experiment E (conf: 0.04)
     └── supports × 100                  └── (one lab, uncited)

Later:
Theory T (conf: 0.21) ←── falsifies ── Experiment E (conf: 0.78)
     └── supports × 100                  ├── supports × 50 (citations)
                                          ├── supports × 8 (replications)
                                          └── survived × 3 challenges
```

## Decision

### 1. Disproofs are nodes, not edge labels

A falsification claim — an experiment, a logical counterexample, an observed anomaly — is a `Claim` node in the graph. It is not just an edge property. This allows the disproof to:

- Accumulate its own support network
- Be contradicted by counter-arguments
- Have its own provenance and source
- Participate in further graph walks

### 2. `falsifies` is a distinct edge type from `contradicts`

`contradicts` — soft tension; two claims in conflict, winner unclear
`falsifies` — directed refutation; the source node is a claimed disproof of the target

The distinction is semantic, not mechanical. The confidence propagation rules are the same for both — but `falsifies` edges are expected to carry higher weight once the source node reaches high confidence, because a confirmed falsification is more decisive than a generic contradiction.

### 3. No hard kills — confidence in refutation must propagate first

Nothing in the system produces an instant, confidence-independent refutation. A `falsifies` edge from a low-confidence node has little effect. A `falsifies` edge from a high-confidence node (well-cited, replicated, survived challenges) has large effect. The threshold is topology-determined, not hardcoded.

### 4. The disproof can itself be disproved

If the falsification experiment E is itself flawed, counter-experiments can create `contradicts` or `falsifies` edges pointing at E. E's confidence falls. If E's confidence falls far enough, T's confidence recovers. This mirrors the scientific process exactly — methodological critiques, failed replications, and theoretical objections are all first-class graph citizens.

## Why This Is Consistent With Existing Principles

**Topology is authority** (Thesis 5): Confidence emerges from network structure. A disproof earns its authority the same way any claim does — through the accumulation of support, independent convergence, and survival under challenge.

**Perspectives, not consensus**: The graph doesn't adjudicate truth. It accumulates evidence. A disputed theory and its disputed falsification can both exist in the graph with partial confidence, faithfully representing the state of scientific knowledge.

**Everything is a node**: Disproofs, experiments, replications, methodological critiques — all first-class nodes with edges, provenance, and topology-based confidence.

## Relationship to Decision 017 (Typed Conflicts)

Decision 017 identified that `contradicts` is overloaded — logical, semantic, scope, temporal, and narrative tensions are all collapsed into one edge type. This decision adds `falsifies` as a distinct type for directed empirical refutation. These decisions are complementary:

- Decision 017 addresses *what kind of tension* exists between two claims
- Decision 018 addresses *how refutation confidence propagates* through the graph

Together they suggest the conflict edge vocabulary needs to grow beyond a single `contradicts` type.

## Implementation Notes

This principle is already partially expressed in the current system — every node has topology-based confidence, and `contradicts` edges reduce it. The gap is:

1. No `falsifies` edge type (currently everything is `contradicts`)
2. Confidence propagation doesn't yet weight edges by the source node's confidence
3. No explicit support for disproof nodes accumulating their own evidence networks

Full implementation is deferred to the Rust port, where the `GraphStore` abstraction can encode edge-type semantics and confidence propagation rules cleanly.

## Related

- [Decision 013: Unified KG Architecture](013-unified-kg-architecture.md) — confidence from topology
- [Decision 017: Typed Conflicts](017-typed-conflicts.md) — conflict edge vocabulary
- [BIG-PICTURE.md](../BIG-PICTURE.md) — Phase 2 (Rust port) where this lands
- `src/oi/conflicts.py` — current untyped confidence resolution (Python reference implementation)
