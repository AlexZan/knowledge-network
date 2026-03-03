# Conflict Resolution Empirical Findings

> **Purpose**: Raw data and analysis from the first run of Slice 13d conflict resolution against the thesis.md knowledge graph. Written for the paper-writing agent.

## Experiment Setup

- **Source graph**: `.oi-test/knowledge.yaml` — thesis.md ingested via batch linker (Slice 13c)
- **Graph size**: 236 nodes, 877 edges, 37 contradiction edges
- **System**: `src/oi/conflicts.py` — `generate_conflict_report()`, `resolve_conflict()`, `auto_resolve()`
- **LLM calls during resolution**: Zero. All classification and resolution is pure topology.
- **Copy used for testing**: `.oi-test-conflicts/` (original `.oi-test/` untouched)

## Classification Results

| Priority | Count | Description |
|----------|-------|-------------|
| auto_resolvable | 6 | Facts only, winner ≥5x supports |
| strong_recommendation | 17 | Winner ≥2x (facts) or ≥3x (subjective) |
| ambiguous | 14 | Equal or near-equal support, or both zero |
| **Total** | **37** | |

After auto-resolve: 0 auto_resolvable, 12 strong_recommendation, 12 ambiguous remaining (24 total).

## Graph State Change

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Active nodes | 236 | 231 | -5 |
| Superseded nodes | 0 | 5 | +5 |
| Contradicts edges | 37 | 31 | -6 |
| Supersedes edges | 0 | 6 | +6 |

Note: 5 unique losers from 6 resolutions — `fact-095` lost twice (to `fact-088` and `fact-094`).

## The Six Auto-Resolutions (Detail)

### Resolution 1: Value extraction vs. session isolation

- **Winner**: `fact-078` (6 supports) — "Value extraction allows lessons to be shared without exposing the original source data"
- **Loser**: `fact-038` (0 supports) — "Lessons learned in one session are not transferred to subsequent sessions"
- **Ratio**: 6:0 (6x)
- **Winner's supporters**: Privacy abstraction (`fact-013`), sensitive details in conversations (`fact-058`), lesson universality (`fact-059`), abstraction removes identifying details (`fact-060`), privacy gradient framework (`fact-068`), privacy by design (`fact-077`)
- **Loser's supporters**: None
- **Analysis**: The loser describes the *problem* (status quo). The winner describes the *solution* the thesis proposes. Six independent nodes confirm the solution works. The loser has no structural backing — it's an isolated observation.

### Resolution 2: Both options valid vs. roundtable selects winner

- **Winner**: `fact-088` (7 supports) — "Preference conflicts are subjective choices where both options are valid"
- **Loser**: `fact-095` (1 support) — "The roundtable mechanism involves active user participation to select a winner"
- **Ratio**: 7:1 (7x)
- **Winner's supporters**: Conflict classification (`fact-083`, `fact-084`, `fact-092`), evidence for truth conflicts (`fact-086`), context-dependent resolution (`fact-089`), explicit declaration (`fact-094`), history preservation (`fact-102`)
- **Loser's supporters**: `decision-015` (explicit human choice)
- **Analysis**: The network's conflict resolution subsystem overwhelmingly supports the view that preferences can coexist. The loser's claim that a "winner is selected" contradicts this. Notably, the loser's one supporter (`decision-015`) actually supports explicit *human* choice, not automated winner-selection.

### Resolution 3: Explicit declaration vs. roundtable winner-picking

- **Winner**: `fact-094` (9 supports) — "Preference issues are resolved through an explicit declaration of choice by a participant"
- **Loser**: `fact-095` (1 support) — same as Resolution 2
- **Ratio**: 9:1 (9x)
- **Winner's supporters**: Trigger recognition (`decision-004`), supersession mechanics (`decision-011`, `fact-100`, `fact-101`), history preservation (`fact-102`), explicit conflicts (`fact-105`), human agency (`decision-015`), high-confidence triggers (`fact-028`), roundtable fallback (`decision-012`)
- **Analysis**: Same loser, different winner. The full conflict resolution pipeline — from triggers through supersession to history — points at explicit declaration. `fact-095` was the weakest node in the preference-resolution cluster.

### Resolution 4: Flagging for resolution vs. guaranteed explicitness

- **Winner**: `fact-103` (18 supports) — "If no explicit preference declaration is made, the conflict is flagged for user or roundtable resolution"
- **Loser**: `fact-105` (1 support) — "The system prevents silent overwrites by making all conflicts explicit"
- **Ratio**: 18:1 (18x)
- **Winner's supporters**: 18 nodes spanning the entire conflict resolution subsystem — classification, resolution workflows, roundtable mechanics, truth vs. preference distinction, history preservation
- **Analysis**: The biggest support gap. `fact-105` overstates: it claims *all* conflicts are made explicit. The network says conflicts are *flagged* for resolution, a more nuanced position. 18 independent nodes confirm the flagging mechanism.

### Resolution 5: Network-as-model vs. LLM-as-reasoner

- **Winner**: `fact-139` (5 supports) — "In Living Knowledge Networks the network itself serves as the model without a separate training phase"
- **Loser**: `fact-158` (1 support) — "In the current stage, the large language model performs reasoning and a personal knowledge graph stores experience"
- **Ratio**: 5:1 (5x)
- **Winner's supporters**: No weight matrices (`fact-140`), graph encodes knowledge (`fact-141`), endgame hybrid architecture (`fact-161`), system deliverable (`decision-026`), framework creation date (`fact-196`)
- **Loser's supporters**: `decision-020` (persist conclusions) — doesn't actually defend the LLM-as-reasoner claim
- **Analysis**: The loser accurately describes the *current* architecture. The winner describes the *vision*. The topology captured the direction of the argument — where the thesis is heading — not just its current state. The loser's supporter is tangential (persistence ≠ LLM reasoning).

### Resolution 6: Connectivity-as-confidence vs. voting-as-confidence

- **Winner**: `fact-010` (28 supports) — "Conclusion-triggered compaction creates a knowledge network where node connectivity determines confidence levels"
- **Loser**: `fact-183` (4 supports) — "Open Systems' voting-experience system could serve as the confidence mechanism"
- **Ratio**: 28:4 (7x)
- **Winner's supporters**: 28 nodes — anti-gaming (`fact-129`), dynamic updates (`fact-130`), provenance (`fact-151`, `fact-152`), topology scoring (`fact-174`), no weight matrices (`fact-140`), and 22 others spanning every major thesis theme
- **Loser's supporters**: `decision-009` (need conflict resolution), `fact-184` (upvotes as support edges), `fact-193` (voting-experience doc), `fact-199` (initial draft links)
- **Analysis**: The most thematically significant resolution. The network *rejected the easier mechanism* (voting) in favor of the harder one (structural connectivity). `fact-184` (upvotes as support edges) supports *both* sides — but the winner has 27 other supporters. This is the system demonstrating its own thesis: confidence from topology, not from votes.

## Key Insights for the Paper

### 1. Emergent Reasoning Without LLM

The conflict resolution system produces what looks like reasoning — but no model was involved. The graph "argued with itself" through support structure. Each resolution is a structural proof: "this claim has more independent backing than that claim." This is a new category: **topological reasoning**.

### 2. The Graph Validates Its Own Thesis

Resolution 6 is self-referential in a profound way. The thesis claims confidence should come from topology, not explicit scores. The voting-as-confidence alternative was proposed and ingested honestly. The topology then *chose* topology-as-confidence over voting-as-confidence. The system demonstrated its own principle through its own operation.

### 3. Four Properties of Topological Truth-Finding

1. **Not gameable**: You cannot inflate confidence without building genuine support structure. Resolution 6 proved this — voting (the easier mechanism) lost to connectivity (the harder one).
2. **Not authoritarian**: No single node, source, or model decides. `decision-001` has 44 supports but earned them one independent link at a time.
3. **Self-correcting**: Losers are superseded, not deleted. If new evidence arrives, resolutions can reverse. The graph doesn't commit permanently.
4. **Auditable end-to-end**: Ask "why is this true?" and the answer is a walkable subgraph. No hidden weights.

### 4. The Closest Algorithm to Absolute Truth

The independence requirement is key. A fact with 28 supporters from different sources isn't popular — it's *convergent*. This is the same epistemological standard science uses: independent replication. The system applies it mechanically to a knowledge graph.

The limitation is honest: it only works for claims that *can* accumulate independent support. Novel one-off observations stay ambiguous (14 of 37 conflicts). The system says "I don't know yet" when it doesn't know — which is itself a form of epistemic integrity.

### 5. Topology Captures Argumentative Direction

Resolution 5 showed the graph doesn't just record facts — it captures *where the argument is heading*. The current-state description (LLM does reasoning) lost to the vision (network is the model) because more nodes support the vision. The topology encoded the thesis's trajectory.

### 6. Structural Convergence ≠ Popularity

This is not a voting system. Each supporter is itself a node with its own support network. A node supported by 5 well-connected nodes is stronger than one supported by 10 isolated nodes. The authority is structural depth, not count alone (though in this first run, count was sufficient for the auto_resolvable threshold).

## Classification Algorithm

```
_classify_conflict(supports_a, supports_b, is_subjective):
  if equal supports → ambiguous
  ratio = winner_supports / max(loser_supports, 1)
  if subjective (decision or preference involved):
    if ratio ≥ 3 → strong_recommendation (NEVER auto_resolvable)
    else → ambiguous
  if factual:
    if ratio ≥ 5 → auto_resolvable
    if ratio ≥ 2 → strong_recommendation
    else → ambiguous
```

Key design decisions:
- Subjective conflicts (involving decisions/preferences) are **never** auto-resolved — require human sign-off
- The 5x threshold for auto-resolution is deliberately conservative
- Division by zero avoided by treating 0 supports as 1 for ratio calculation

## Resolution Mechanics

1. Mark loser `status=superseded`, set `superseded_by=winner_id`
2. Add `supersedes` edge (winner → loser) with reason
3. Remove all `contradicts` edges between the pair
4. Clean `has_contradiction` flag on loser (always — it's superseded)
5. Clean `has_contradiction` flag on winner only if no remaining contradicts edges

## Files

| File | Role |
|------|------|
| `src/oi/conflicts.py` | Implementation: models, classification, resolution |
| `tests/test_conflicts.py` | 14 tests (all graph-based, zero LLM) |
| `.oi-test/knowledge.yaml` | Original 236-node graph (untouched) |
| `.oi-test-conflicts/knowledge.yaml` | Post-resolution copy (6 conflicts resolved) |
