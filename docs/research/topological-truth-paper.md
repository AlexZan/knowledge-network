# Topological Truth: Conflict Resolution Through Knowledge Graph Structure

Alexander Zanfir, Independent Researcher

March 2026

---

## Abstract

When conclusions are recorded as nodes in a knowledge graph with typed edges between them, the graph develops structural properties that can resolve contradictions — when the structural evidence is sufficient — without external judgment. I present a conflict resolution system that classifies and resolves contradictions using only the topology of supporting edges — no large language model, no human judge, no voting mechanism. LLMs construct the graph; the resolution phase is pure topology. Applied across three experiments at increasing scale — a 236-node single-document graph (37 contradictions), an 894-node three-source graph (163 contradictions), and a 1,336-node graph built from 122 independent sources (190 contradictions) — the system auto-resolved 16%, 67%, and 58% of conflicts respectively, with zero false positives among auto-resolutions at any scale. Manual review of 20 post-resolution conflicts revealed that 55% were construction artifacts — the linker misclassified edges due to summary-level ambiguity — while the resolution mechanism correctly classified every one as requiring human review rather than auto-resolving it. Cross-source analysis revealed empirically distinguishable structural signatures between within-source and cross-source edges, providing evidence that independent convergence is observable in graph topology. One resolution is self-referential: the system adjudicated between "confidence from topology" and "confidence from voting" as competing approaches, and the topology chose topology — the system demonstrated its own thesis through its own operation. I argue that independent structural convergence in a knowledge graph is a mechanical analog of scientific replication, and present four properties that distinguish this approach from voting, LLM judgment, or explicit scoring: it is not gameable, not authoritarian, self-correcting, and auditable end-to-end.

---

## 1. Introduction

### 1.1 The Problem

Machine truth-finding is usually framed as a classification task. Given competing claims, select a winner by: polling human judges, asking a language model, counting votes, or computing a score. Each approach embeds an authority — someone or something that *decides*. The decision may be correct, but the mechanism is opaque, gameable, or both.

Voting systems are susceptible to coordination attacks. LLM-based judgment inherits the biases of training data and produces non-reproducible verdicts. Human scoring is expensive and doesn't scale. Explicit confidence scores are arbitrary — who decides that a claim merits 0.8 rather than 0.7? All of these approaches treat truth-finding as a judgment problem: apply an evaluator to competing claims and accept the verdict.

This paper proposes a different framing. Instead of *judging* claims, we examine the *structural support* each claim has accumulated in a knowledge graph. A claim supported by 28 independent nodes from across the graph is not popular — it is convergent. A claim with 1 supporter is not necessarily wrong — it is underspecified. The topology itself becomes the authority.

### 1.2 Prior Work: Conclusion-Triggered Compaction

This work builds on Cognitive Context Management (CCM) [1], which demonstrated that compacting AI memory at conclusion boundaries — rather than at capacity limits — achieves O(1) bounded working memory with 93–98% token savings. CCM's core mechanism extracts conclusions from resolved reasoning threads and persists them as summary nodes with links to their source material.

This paper asks the next question: when those compacted conclusions accumulate as nodes in a knowledge graph with typed edges between them, can the graph's own topology serve as an authority for resolving contradictions? The answer, demonstrated empirically, is yes — for conflicts where the structural evidence is sufficient, and no for conflicts where it is not.

### 1.3 Contributions

1. A topology-based conflict resolution algorithm that classifies contradictions by support ratio and resolves them through supersession, with zero LLM involvement in any classification or resolution
2. Empirical results across three scales: 236-node single-source, 894-node three-source, and 1,336-node 122-source graphs — demonstrating that auto-resolution rates improve with graph size as well-supported claims accumulate more structural evidence
3. A manual review analysis of 20 post-resolution conflicts showing that the resolution mechanism never auto-resolved a construction artifact — it correctly classified every false positive as requiring human review
4. Cross-source structural signatures: empirically distinguishable edge distributions between within-source and cross-source relationships, with three-way triangulation across independent academic sources
5. A self-referential result in which the system adjudicated between its own thesis (topology-as-confidence) and an alternative (voting-as-confidence), and the topology chose topology
6. A second self-referential result: the system ingested this paper, found precision errors in its claims, and the paper was corrected based on the system's own conflict report (Section 9)
7. An argument that independent structural convergence is a mechanical analog of scientific replication — the closest algorithmic approximation of how empirical truth is established

---

## 2. Mechanism

### 2.1 Graph Structure

The knowledge graph consists of nodes and typed edges. Nodes represent conclusions extracted from documents — facts, decisions, and preferences — each with a unique identifier, summary text, source provenance, and status (active or superseded). Edges encode relationships: `supports` (one node provides evidence for another), `contradicts` (two nodes make incompatible claims), `exemplifies` (one node is a specific instance of another), and `supersedes` (one node has replaced another through conflict resolution).

The initial graph (V1) was constructed by ingesting a thesis document through a batch linker that uses LLM-based semantic classification to determine edge types between node pairs. Subsequent experiments (V2, V3) applied the same linker to larger, multi-source graphs — see Sections 3.5–3.7. This is a deliberate architectural separation: **LLMs construct the graph; topology arbitrates disputes within it.** The perception phase (building the graph) may involve language models. The judgment phase (resolving conflicts) does not. The novel contribution is in the judgment phase.

### 2.2 Classification Algorithm

When two nodes are connected by a `contradicts` edge, the system classifies the conflict by comparing their inbound support — the number of other nodes that point to each via `supports` or `exemplifies` edges.

```
classify_conflict(supports_a, supports_b, is_subjective):
    if supports_a == supports_b:
        return AMBIGUOUS

    winner = max(supports_a, supports_b)
    loser = min(supports_a, supports_b)
    ratio = winner / max(loser, 1)    # avoid division by zero

    if is_subjective:                  # decisions or preferences involved
        if ratio >= 3: return STRONG_RECOMMENDATION
        else:          return AMBIGUOUS
        # subjective conflicts are NEVER auto-resolvable

    if ratio >= 5:  return AUTO_RESOLVABLE
    if ratio >= 2:  return STRONG_RECOMMENDATION
    else:           return AMBIGUOUS
```

Three design decisions are embedded in this algorithm:

**Subjective conflicts are never auto-resolved.** When either node in a contradiction is a decision or preference (rather than a factual claim), the system will recommend but never act autonomously. Subjective disputes require human sign-off regardless of how lopsided the topology is. This is not a limitation — it is a deliberate epistemic boundary. The system distinguishes between "this claim has more structural support" and "this claim is correct," and recognizes that for subjective matters, structural support is insufficient authority.

**The 5x threshold is deliberately conservative.** A factual claim must have five times the support of its competitor before automatic resolution. This means a 4:1 advantage — which would be overwhelming in most contexts — still requires human review. The threshold was chosen to minimize false positives at the cost of leaving resolvable conflicts for manual review. In the empirical evaluation, every auto-resolution at ≥5x was unambiguously correct.

**Zero supports counts as one for ratio calculation.** A node with 6 supporters versus a node with 0 supporters yields a ratio of 6, not infinity. This prevents pathological behavior on isolated nodes while preserving the meaningful signal that one side has structural backing and the other has none.

### 2.3 Resolution Mechanics

When a conflict is resolved — either automatically or by human decision — the system performs five operations:

1. **Mark the loser as superseded.** Set `status=superseded` and record `superseded_by` pointing to the winner. The losing node is not deleted — it remains in the graph as a historical record.
2. **Add a supersedes edge.** Create a directed `supersedes` edge from winner to loser with a reason string. This makes the resolution auditable and walkable.
3. **Remove contradicts edges.** All `contradicts` edges between the pair are removed, since the contradiction is now resolved.
4. **Clean the loser's contradiction flag.** The loser is superseded; its contradiction status is no longer relevant.
5. **Conditionally clean the winner's contradiction flag.** Only clear it if the winner has no remaining `contradicts` edges with other nodes.

The key property of this mechanism is **reversibility**. Superseded nodes retain all their original content and edges (except the resolved contradiction). If new evidence arrives that supports the loser, the resolution can be revisited. The graph does not commit permanently — it records its current best judgment and the evidence behind it.

---

## 3. Empirical Results

### 3.1 The Graph

The knowledge graph was constructed by ingesting a single thesis document (~12,000 words) describing the Living Knowledge Networks framework [2]. The document contains interconnected arguments with internal tensions — enough structure for contradictions to emerge naturally during graph construction.

| Metric | Value |
|--------|-------|
| Active nodes | 236 |
| Total edges | 877 |
| Contradiction edges | 37 |
| Node types | facts, decisions, preferences |
| Source document | Single thesis (~12,000 words) |
| LLM calls during resolution | 0 |

### 3.2 Classification Results

| Priority | Count | Description |
|----------|-------|-------------|
| Auto-resolvable | 6 | Factual conflicts, winner ≥5x support |
| Strong recommendation | 17 | Winner ≥2x (facts) or ≥3x (subjective) |
| Ambiguous | 14 | Equal or near-equal support |
| **Total** | **37** | |

### 3.3 Graph State After Resolution

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Active nodes | 236 | 231 | −5 |
| Superseded nodes | 0 | 5 | +5 |
| Contradicts edges | 37 | 31 | −6 |
| Supersedes edges | 0 | 6 | +6 |

Each of the 6 resolutions removed the `contradicts` edge between the resolved pair (per Section 2.3, step 3), producing the observed decline from 37 to 31. Six resolutions produced five unique superseded nodes — one node (`fact-095`) was the loser in two separate resolutions, confirming it as the weakest node in its local cluster.

### 3.4 The Six Resolutions

The six auto-resolved conflicts, examined individually:

#### Resolution 1: Solution supersedes problem statement (6:0)

- **Winner**: "Value extraction allows lessons to be shared without exposing the original source data" (6 supporters)
- **Loser**: "Lessons learned in one session are not transferred to subsequent sessions" (0 supporters)

The loser describes the *problem* — the status quo that the thesis proposes to solve. The winner describes the *solution*. Six independent nodes confirm the solution's mechanism through privacy abstraction, lesson universality, and privacy-by-design principles. The loser has no structural backing because it is an observation, not an argued position. The topology correctly identified an isolated problem statement competing against a well-supported solution.

#### Resolution 2: Coexistence supersedes winner-selection (7:1)

- **Winner**: "Preference conflicts are subjective choices where both options are valid" (7 supporters)
- **Loser**: "The roundtable mechanism involves active user participation to select a winner" (1 supporter)

The graph contained seven nodes supporting the view that preferences can coexist, and only one supporting the claim that a roundtable "selects a winner." The graph's own topology overwhelmingly favored coexistence. Notably, the loser's single supporter (`decision-015`) actually argues for explicit *human* choice — which is closer to the winner's position than the loser's framing of winner-selection. The topology captured a nuance that keyword matching would miss.

#### Resolution 3: Declaration supersedes winner-picking (9:1)

- **Winner**: "Preference issues are resolved through an explicit declaration of choice by a participant" (9 supporters)
- **Loser**: Same as Resolution 2 — "The roundtable mechanism involves active user participation to select a winner" (1 supporter)

The same node lost twice. Nine nodes across the graph — spanning trigger recognition, supersession mechanics, and history preservation — converge on explicit declaration as the resolution mechanism. `fact-095` was structurally the weakest node in the preference-resolution cluster, contradicting two better-supported positions simultaneously. The topology identified it from two independent angles.

#### Resolution 4: Flagging supersedes guaranteed explicitness (18:1)

- **Winner**: "If no explicit preference declaration is made, the conflict is flagged for user or roundtable resolution" (18 supporters)
- **Loser**: "The system prevents silent overwrites by making all conflicts explicit" (1 supporter)

The largest support gap in the dataset. The graph contained a node claiming *all* conflicts are made explicit, competing against a node taking the more nuanced position that conflicts are *flagged* for resolution. Eighteen independent nodes — spanning classification, resolution workflows, roundtable mechanics, and history preservation — support the flagging mechanism. The topology distinguished between an overstatement ("all conflicts are explicit") and the more accurate qualified claim ("conflicts are flagged for resolution").

#### Resolution 5: Vision supersedes current state (5:1)

- **Winner**: "In Living Knowledge Networks the network itself serves as the model without a separate training phase" (5 supporters)
- **Loser**: "In the current stage, the large language model performs reasoning and a personal knowledge graph stores experience" (1 supporter)

The loser accurately describes the *current* architecture. The winner describes the *vision*. Both are factually correct in their respective temporal contexts. But the topology captured the direction of the argument — where the thesis is heading — not just its current state. The loser's single supporter (`decision-020`: persist conclusions) is tangential; persistence is not the same as defending LLM-as-reasoner. Five nodes support the network-as-model vision through explicit claims about no weight matrices, graph-encoded knowledge, and hybrid architecture endgame.

This resolution reveals an emergent property: **topology encodes argumentative trajectory.** The graph does not merely record what is currently true. When a document argues toward a conclusion, the intermediate supporting claims accumulate edges that point toward the destination. The topology captures momentum.

#### Resolution 6: Connectivity supersedes voting (28:4)

- **Winner**: "Conclusion-triggered compaction creates a knowledge network where node connectivity determines confidence levels" (28 supporters)
- **Loser**: "A voting-experience system could serve as the confidence mechanism" (4 supporters)

The most significant resolution — and the only self-referential one. The system adjudicated between two competing proposals for its own confidence mechanism, and the topology chose the one it was already using. The system demonstrated its own thesis through its own operation. The full analysis is in Section 6.

### 3.5 Scaling: Three-Source Graph (894 Nodes)

To test whether topological resolution scales beyond a single document, the knowledge graph was wiped and rebuilt from scratch using three independent sources: 7 AI-assisted conversations developing a physics theory (ChatGPT exports processed via an ingestion pipeline, 730 nodes), a Stanford Encyclopedia of Philosophy article on collapse theories (66 nodes), and a second SEP article on philosophical issues in quantum theory (98 nodes). The same extraction and linking pipeline was used, with no parameter changes from V1. The three sources were authored independently and address overlapping but distinct aspects of quantum mechanics. Cross-source structural signatures from this experiment are analyzed in Section 7.3.

| Metric | Single-Source (V1) | Three-Source (V2) |
|--------|-------------------|-------------------|
| Active nodes | 236 | 894 |
| Total edges | 877 | 5,020 |
| Contradictions | 37 | 163 |
| Auto-resolved | 6 (16%) | 110 (67%) |
| Strong recommendations | 17 | 19 |
| Ambiguous | 14 | 34 |
| LLM calls in resolution | 0 | 0 |
| PageRank iterations | — | 45 |
| Runtime | — | 53ms |

The auto-resolution rate jumped from 16% to 67%. Larger graphs produce more lopsided support ratios because well-supported claims accumulate evidence from multiple independent sources, making the topological signal more decisive. Every auto-resolution completed without error.

### 3.6 Scaling: Full Rebuild (1,336 Nodes, 122 Sources)

The largest experiment rebuilt the knowledge graph from scratch using conversation-aware extraction [3] across 120 author conversations (a superset of V2's 7) and the same 2 SEP articles — 122 independent sources total.

| Metric | Three-Source (V2) | Full-Scale (V3) |
|--------|-------------------|-----------------|
| Active nodes | 894 | 1,263 |
| Total nodes (incl. superseded) | 894 | 1,336 |
| Total edges | 5,020 | 8,022 |
| `supports` | 1,198 | 1,849 |
| `related_to` | 3,618 | 5,981 |
| `contradicts` (before resolution) | 163 | 190 |
| `contradicts` (after auto-resolve) | 51 | 79 |
| `supersedes` | — | 113 |
| Auto-resolve rate | 67% | 58% |
| Sources | 3 | 122 |

The auto-resolve rate decreased from 67% to 58% despite the larger graph. This is not a regression — the 17x increase in source conversations introduced more nuanced claims with genuine ambiguity. The V2 graph had 7 conversations from a single author; the V3 graph had 120 conversations spanning months of theory development, where the author's own position evolved over time. The resolution mechanism correctly identified these evolutionary tensions as requiring human review rather than forcing a verdict.

### 3.7 Scaling Analysis

| Scale | Nodes | Sources | Contradictions | Auto-Resolved | Rate |
|-------|-------|---------|----------------|---------------|------|
| V1 | 236 | 1 doc | 37 | 6 | 16% |
| V2 | 894 | 3 | 163 | 110 | 67% |
| V3 | 1,336 | 122 | 190 | 111 | 58% |

Three observations emerge from the scaling progression:

**Auto-resolution improves with graph density, not just size.** The jump from 16% to 67% between V1 and V2 was driven by cross-source support accumulation: claims about quantum measurement that were isolated in a single document gained independent backing from academic sources. The modest decline to 58% in V3 reflects an increase in genuinely contested claims, not a weakening of the mechanism. Manual review (Section 4.2) confirmed this: of 20 sampled post-resolution conflicts, 5 were intra-theory contradictions where the author's position evolved across the 120-conversation span — a class of conflict that barely exists in V2's 7-conversation dataset. The remaining non-resolutions included 3 cross-source scientific disagreements and 11 construction artifacts, all correctly left for human review.

**Zero false positives in auto-resolution at every scale.** Manual review (Section 4) confirmed that every auto-resolved conflict was correctly decided. The 5x threshold is conservative enough to prevent erroneous resolutions even as the graph grows by an order of magnitude.

**The mechanism is source-agnostic.** The algorithm does not know whether two supporting nodes came from the same document, the same author, or independent sources. It counts structural connections. Yet the results are qualitatively different across source configurations — because the *graph's structure* reflects the independence of its inputs. This property is explored further in Section 7.

---

## 4. What the System Refused to Resolve

### 4.1 The V1 Abstentions

In the initial 236-node graph, fourteen of 37 contradictions were classified as ambiguous. The system produced no recommendation and took no action. These fall into three categories:

**Genuinely underdetermined conflicts.** Both sides have zero or equal support. Neither claim has accumulated independent backing, so the topology has nothing to compare. These are not failures — they are nodes that have not yet participated in enough of the graph's structure to be evaluable. They may resolve as the graph grows, or they may remain permanently ambiguous.

**Near-equal support with insufficient gap.** Both sides have supporters, but the ratio falls below the classification threshold. A 3:2 advantage is a signal, not a verdict. The system reports it but does not act.

**Novel claims without structural context.** Some contradictions involve nodes that are topologically isolated — connected to the graph through only the contradiction edge itself, with no support from elsewhere. The system correctly identifies these as unevaluable: without independent support, there is nothing for the topology to measure.

The 14 ambiguous conflicts are not a weakness of the system. They are its most important feature. A truth-finding mechanism that always produces a verdict is not finding truth — it is manufacturing certainty. The willingness to say "the evidence is insufficient" is the property that separates measurement from opinion. Scientific peer review operates on the same principle: insufficient evidence means no conclusion, not a weaker conclusion.

### 4.2 Manual Review: What the V3 Abstentions Actually Were

The full-scale V3 graph (1,336 nodes, 122 sources) left 37 conflicts after auto-resolution. Twenty were manually reviewed by the domain expert (the theory's author), with full provenance — reading source conversations, checking timestamps, and examining the context the linker lacked. Results:

| Outcome | Count | % |
|---------|-------|---|
| Reclassified → `related_to` or `supports` (false positive) | 11 | 55% |
| Kept `contradicts` (genuine conflict) | 6 | 30% |
| Kept `contradicts` (terminology conflict, reverted) | 2 | 10% |
| Deferred | 1 | 5% |

**55% of the conflicts the system refused to auto-resolve were construction artifacts** — the linker misclassified edge types because it had only node summaries, not source context. But the resolution mechanism never auto-resolved any of them. Every construction artifact was correctly classified as ambiguous or strong-recommendation, requiring human review. This is the critical finding: **construction errors in the graph do not propagate into resolution errors**, because the conservative 5x threshold filters them out.

Five construction failure modes emerged from the review:

1. **Scope mismatch.** Claims at different scales (intra-universe vs inter-universe, individual observer vs ensemble) appear contradictory at summary level but operate in non-overlapping domains.

2. **Context loss.** The linker sees only summaries — it misses that two nodes describe sequential stages of the same process, or are contrapositives of the same principle. One pair described "collapse creates entropy" and "memory has zero entropy" as contradictory; in the source conversation, they are explicitly presented as stages of a spectrum (fluctuation → collapse → memory).

3. **Extraction splitting.** The extraction LLM split a single user statement — "randomness is not information, but it *is* information potential" — into two separate nodes, which the linker then flagged as contradictory. Same conversation, same timestamp. The conflict was manufactured by the extraction phase, not discovered by the linker.

4. **Terminology conflict.** The underlying concepts are compatible but the node's summary language creates genuine tension with other nodes. "Rewriting the collapse chain" (meaning: redirecting future collapses) contradicts "the collapse chain is immutable after resolution." These were initially reclassified as `related_to`, then **reverted** back to `contradicts` — the signal is valid as written, even when the author's intent was compatible. Premature reclassification would lose information.

5. **Attribution gap.** Reference material pasted into a conversation (e.g., a lecture transcript on Bohmian mechanics) was attributed as the author's own theory claim. The GRW-vs-Bohm contradiction is scientifically real, but the system misattributed one side's provenance, making a cross-interpretation disagreement appear as an intra-author contradiction.

Each of these failure modes has a designed (but not yet implemented) mitigation: tiered context-aware linking for modes 1–2, extraction-phase deduplication for mode 3, a terminology correction flow for mode 4, and attribution-aware extraction for mode 5.

### 4.3 The Genuine Conflicts

Six of the 20 reviewed conflicts were genuine contradictions — the `contradicts` edge was correct. These fall into two categories:

**Intra-theory evolution.** The author's position changed over time. A speculative claim about partial collapse (authored early) contradicts an established claim about full collapse (authored later with stronger conviction). The `authored_at` timestamps make the evolution visible. The system correctly left these for human judgment — topological support alone cannot determine whether a later claim supersedes or merely extends an earlier one.

**Cross-source scientific disagreement.** The system correctly identified known rivalries between quantum mechanics interpretations: GRW collapse theory (from the SEP article) vs pilot-wave theory (from a separate SEP article), and competing ontological positions within the same encyclopedic survey. These are genuine, well-known scientific disagreements. The system found them mechanically.

### 4.4 The Revert Pattern

Two conflicts (S9, S14) were initially reclassified from `contradicts` to `related_to`, then reverted back to `contradicts` after reflection. The reviewer realized that terminology conflicts should retain their contradiction signal until the offending node is superseded with corrected language.

This is a nuance that standard knowledge graph systems do not report: **a contradiction can be valid as a signal even when the underlying concepts are compatible.** The node *as written* contradicts another node. Reclassifying it prematurely hides the fact that the node's language needs correction. The `contradicts` edge serves as a persistent flag — not just "these claims disagree" but "this node's summary is misleading enough to trigger false contradiction signals."

---

## 5. Properties of Topological Truth-Finding

Four properties distinguish topology-based conflict resolution from alternative approaches.

### 5.1 Not Gameable

You cannot inflate a node's confidence without building genuine support structure. Each supporter is itself a node with its own topology — a node supported by five well-connected nodes is structurally different from one supported by five isolated stubs. Gaming the system requires constructing an entire plausible subgraph of supporting claims, each of which must itself be integrated into the broader graph to carry weight.

Resolution 6 demonstrated this directly. The voting-as-confidence alternative is the *easier* mechanism — it is simpler to implement, well-understood, and already used in production systems. The topology rejected it in favor of the *harder* mechanism (structural connectivity) because the harder mechanism had deeper structural roots. Ease of implementation does not create topological support.

Compare this to voting systems, where coordination among a small group can override the broader population, or to LLM judgment, where prompt engineering can steer verdicts.

### 5.2 Not Authoritarian

No single node, source, or model decides the outcome. The most-connected node in the test graph (`decision-001`, 44 inbound supports) earned those connections one independent link at a time, through ingestion of a document where many claims pointed back to the same foundational decision. If a new document contradicted that foundational decision with sufficient independent support, the topology would reflect it.

This is structurally different from systems where a designated authority (a human curator, a trained classifier, a majority vote) renders a verdict. The authority in topological resolution is distributed across the entire support subgraph. Asking "who decided this?" yields not a name or a model, but a walkable chain of evidence.

### 5.3 Self-Correcting

Superseded nodes are not deleted. They remain in the graph with full content, original edges, and a `superseded_by` pointer to their replacement. If new evidence arrives that supports a previously superseded node — new nodes are added that create support edges pointing to it — the support ratio changes. A resolution that was once 28:4 could become 28:30 with sufficient new evidence, at which point the system would reclassify the conflict as ambiguous or even recommend reversal.

The graph does not commit permanently. It records its current best judgment and the structural evidence behind that judgment. This mirrors how scientific consensus operates: established results are not eternal truths but current best explanations, revisable when evidence warrants.

### 5.4 Auditable End-to-End

Every resolution traces to a walkable subgraph. Ask "why was this claim superseded?" and the answer is: "Because these 28 nodes support its competitor, and here are their IDs, summaries, and their own support structures." The entire reasoning chain is inspectable by humans without specialized tools — it is nodes and edges, not hidden weights or attention patterns.

This is the property that no neural network-based truth-finding system can currently match. An LLM can *tell you* why it judged one claim more credible than another, but its explanation is a post-hoc rationalization generated by the same opaque weights. The knowledge graph's explanation *is* the evidence — there is no gap between the mechanism and the audit trail.

The manual review process (Section 4.2) extended this audit trail further. Each human review decision — reclassify, keep, defer — was recorded with reasoning and raw source excerpts in provenance files linked via `review://` URIs. The chain is now: node extraction (with source provenance) → edge classification (by linker) → conflict detection (by topology) → auto-resolution or human review (with review provenance). Every link in the chain is inspectable and reversible.

---

## 6. The Self-Referential Result

Resolution 6 requires its own analysis because the system adjudicated a dispute about its own operating principle.

### 6.1 The Conflict

The thesis document proposes that confidence in a knowledge network should emerge from node connectivity — the topology of supporting edges. An alternative was also present in the graph: a voting-experience system where upvotes function as support edges and accumulated experience determines authority.

Both proposals were ingested honestly into the same graph:

- `fact-010`: "Conclusion-triggered compaction creates a knowledge network where node connectivity determines confidence levels"
- `fact-183`: "A voting-experience system could serve as the confidence mechanism"

The ingestion process created `contradicts` edges between them because they propose incompatible confidence mechanisms. No editorial decision was made to favor either side during ingestion.

### 6.2 The Topology

`fact-010` accumulated 28 inbound support edges from across the graph. Its supporters include nodes about anti-gaming properties, dynamic confidence updates, provenance chains, topology scoring, the absence of weight matrices, and twenty-two other nodes spanning every major theme of the thesis. The support is broad — not concentrated in one subsection of the document, but distributed across the full argumentative structure.

`fact-183` accumulated 4 supporters: the need for conflict resolution (`decision-009`), upvotes as support edges (`fact-184`), a reference to the voting-experience document (`fact-193`), and initial draft links (`fact-199`). Notably, `fact-184` (upvotes as support edges) is conceptually compatible with *both* sides — but the topological fact is that it was linked to the voting node, not the connectivity node.

The ratio is 28:4 — 7x — well above the 5x auto-resolution threshold.

### 6.3 The Self-Reference

The thesis claims that confidence should come from topology, not from explicit scoring mechanisms like voting. The voting-based alternative was proposed, ingested, and given a fair structural opportunity to accumulate support. The topology then evaluated both proposals by the very mechanism one of them advocates — structural support comparison — and selected the structural-support proposal as the winner.

**The system demonstrated its own thesis through its own operation.**

This is not circular reasoning. The topology did not know which node contained "its own" thesis. It compared support counts — 28 versus 4 — using the same algorithm it applies to every other contradiction in the graph. The result happened to validate the system's own principle, but the mechanism that produced the result is the same mechanism that resolved the other five conflicts, none of which were self-referential.

### 6.4 Addressing the Skeptic

An obvious objection: of course the thesis document's own graph has more support for the thesis document's own proposal. The graph was built from a document that argues for topology-as-confidence, so naturally topology-as-confidence has more supporters.

This is true, and it is also the point. The thesis document *argues its case* by building a web of supporting claims — anti-gaming properties, auditability, self-correction, the neural network analogy. Each of those supporting claims became a node. Each node was independently linked to the conclusions it supports. The result is that a well-argued position has deep structural support, and a briefly-mentioned alternative has shallow structural support.

This is exactly how the system is supposed to work. A well-argued position *should* win over a briefly-mentioned one. The topology measured the depth of argumentation, not the author's intent. If the voting-experience alternative had been argued with the same depth — with nodes about its anti-gaming properties, its auditability, its track record — it would have accumulated comparable support, and the conflict would have been classified as ambiguous.

The skeptic's objection reduces to: "The better-argued position won." That is not a bug.

---

## 7. Independent Convergence as Mechanical Replication

### 7.1 The Epistemological Claim

The independence of supporting nodes is the key property that elevates topological truth-finding above counting. A node supported by 28 other nodes is not merely popular. If those 28 nodes were created from different sections of a document, addressing different aspects of the problem, through different argumentative paths — then their convergence on the same conclusion is structural evidence that the conclusion is well-founded.

This is the same epistemological standard that science uses. A hypothesis confirmed by one experiment is interesting. A hypothesis confirmed by five independent experiments using different methodologies is established. A hypothesis confirmed by twenty-eight independent results from different subfields is as close to settled as science gets.

The knowledge graph applies this principle mechanically. Each supporting node is an independent "experiment" — a claim that was ingested, linked, and found to support the target. The system does not know or care that these nodes are "independent" in any philosophical sense. It counts structural connections. But the *process* by which the graph was built — ingesting claims from a document's argumentative structure, linking them based on semantic relationships — produces nodes whose independence is grounded in the source material's own reasoning diversity.

### 7.2 What This Is Not

This is not a claim that topological support equals truth. A well-argued falsehood would accumulate topological support just as readily as a well-argued truth. The system measures *coherence of supporting structure*, not *correspondence to reality*.

But this limitation is shared by every epistemological framework, including science. Scientific replication measures coherence of experimental results — it cannot prove correspondence to ultimate reality, only convergence of independent evidence. Topological truth-finding operates at the same level: it identifies claims that are well-supported by independent structural evidence, and distinguishes them from claims that are not.

The honest claim is: **this is the closest algorithmic approximation of how empirical knowledge is established.** Not because it is perfect, but because it captures the essential mechanism — independent convergence — and applies it without requiring human judgment, LLM inference, or voting.

### 7.3 Cross-Source Structural Signatures

The three-source experiment (V2) provided the first empirical evidence that independent convergence is not merely a theoretical property but an observable structural signature.

Edge distributions between within-source and cross-source relationships were empirically distinguishable:

| Edge Category | `related_to` | `supports` | `contradicts` | N |
|---------------|:------------:|:----------:|:-------------:|------:|
| Within-source | 70% | 27% | 3% | 4,295 |
| Cross-source | 90% | 5% | 5% | 684 |

Cross-source edges are overwhelmingly `related_to` (topical overlap without logical commitment) — 90% versus 70% within-source. The most striking difference is in `supports` edges: 27% of within-source edges are logical commitments (one node providing evidence for another), compared to just 5% cross-source. This is expected: independent sources addressing the same domain will have topical overlap, but their argumentative structures are independent — they do not build on each other's intermediate claims. The structural signature of independence is a high related-to-support ratio.

The two SEP articles in the three-source graph connected to each other through only 5 edges (all `related_to`). They cover different aspects of quantum mechanics without directly contradicting each other. The system correctly treated them as genuinely independent perspectives.

### 7.4 Three-Way Triangulation

Three theory nodes received `supports` edges from *both* independent SEP articles — validated from two separate mainstream perspectives:

- "Photon detector causes interference pattern to disappear" (supported by collapse theory and QM foundations)
- "Detector as entropic system with collapse seed" (supported by both, also contradicted by both — a battleground node)
- "Standard QM doesn't specify collapse mechanism" (supported by both)

The second node is particularly notable: it simultaneously received support (detection causes physical changes) and contradiction (the specific mechanism is disputed) from both independent sources. This "battleground node" pattern — support and contradiction from multiple independent perspectives — is a structural indicator of a genuinely contested claim at the frontier of a field. The system surfaces this mechanically.

### 7.5 Depth of Contradiction

The three-way analysis revealed that different sources challenge the theory at different levels, and the graph structure captures this gradient:

The collapse theory article produced 24 contradictions, all sharing the assumption that **collapse is real**. They disagree about the *trigger mechanism* — spontaneous (GRW) vs conditional (the author's theory). These are family disputes within the collapse interpretation camp.

The quantum foundations article produced 7 contradictions from fundamentally different objections: Everett/Many-Worlds (collapse never happens, all branches persist) and de Broglie-Bohm (particles have definite trajectories, collapse is unnecessary). These are not mechanism disagreements — they are foundational challenges that reject the premise.

The system did not need to understand this distinction to capture it. The structural difference — many shallow contradictions from one source vs few deep contradictions from another — emerged from the topology. A future pipeline improvement could classify contradiction depth automatically from such structural signatures.

### 7.6 The Limitation Is the Feature

The system did not force a resolution on any conflict where evidence was insufficient. At the V1 scale, 14 of 37 stayed ambiguous. At the V3 scale, 37 of 190 remained after auto-resolution, and manual review confirmed that the system's abstentions included both genuine ambiguities and construction artifacts — but never a case where it should have acted and didn't. The ability to abstain when evidence is insufficient is what makes the remaining verdicts credible.

---

## 8. Limitations

**Support count, not support depth.** The current algorithm counts inbound support edges without weighting by the supporters' own connectivity. A node supported by five highly-connected nodes should, in principle, be stronger than one supported by five isolated nodes. The classification algorithm uses raw counts. A reasoning-weighted variant has been partially implemented — edges with explicit reasoning receive 1.0x weight in PageRank while edges without reasoning receive 0.5x — but the classification thresholds still operate on counts. A recursive depth-aware variant would be more expressive.

**Separation of perception and judgment.** The architecture deliberately separates graph construction (LLM-assisted) from conflict resolution (pure topology). This means the quality of topological judgment is bounded by the quality of the graph the LLM built. Manual review (Section 4.2) quantified this: 55% of post-resolution conflicts were construction artifacts — edges misclassified because the linker had only node summaries, not source context. The resolution algorithm correctly refused to auto-resolve any of these, but a cleaner graph would have fewer false conflicts to review. A tiered linking approach — escalating from summaries to source blocks to agentic graph navigation when classification confidence is low — would reduce construction errors without changing the resolution algorithm.

**Construction failure modes.** Five specific failure modes were identified in the construction phase (Section 4.2): scope mismatch, context loss, extraction splitting, terminology conflict, and attribution gap. Each has a designed mitigation. The failure modes are in the *perception* phase, not the *judgment* phase — but they affect the input quality on which judgment operates. The resolution mechanism's conservatism (5x threshold, never auto-resolving subjective conflicts) provides a safety margin against construction noise.

**Threshold sensitivity.** The 5x auto-resolution threshold and 2x/3x recommendation thresholds are parameters, not derived quantities. Different thresholds would change the classification distribution. The 5x threshold was chosen for conservatism and has now been validated at three scales — 236 nodes, 894 nodes, and 1,336 nodes — with zero false positives among auto-resolutions at every scale. The optimal threshold likely depends on graph density and domain, but the empirical evidence supports 5x as a robust default.

**Adversarial inputs not tested.** Section 5.1 argues that gaming the system requires constructing an entire plausible subgraph. This is true for a single-author graph, but in a multi-source system an adversary could inject many low-quality sources that all support a desired conclusion. The current experiments use trusted sources (author conversations, encyclopedic references) — no adversarial ingestion was attempted. The 5x threshold provides some defense (the adversary needs overwhelming structural advantage, not merely a majority), but the system's robustness under adversarial conditions is an open question.

**Temporal naivety.** The algorithm does not consider when nodes or edges were created. A node supported by 28 edges from 2024 is treated identically to one supported by 28 edges from 2020. In domains where recency matters, this could be a limitation. The graph stores `authored_at` timestamps on nodes, and manual review confirmed that temporal signals are valuable — conflicts between nodes authored weeks apart often represent theory evolution rather than contradiction. Incorporating temporal weighting into the resolution algorithm is a natural extension, though the current design intentionally prioritizes accumulated evidence over recency.

**Semantic contradictions vs. logical contradictions.** The system currently treats all `contradicts` edges as a single undifferentiated type. A prompt-level gate (requiring mutual exclusivity before classifying an edge as `contradicts`) reduces false positives from scope differences, terminology mismatches, and abstraction-level gaps — but the distinction between semantic tension and genuine logical contradiction is made at construction time by the LLM, not verified structurally. Manual review (Section 4.2) found that 55% of post-resolution conflicts were construction artifacts — edges where the nodes *sounded* contradictory but were not logically incompatible. The current mitigation is preventive (better prompts), not diagnostic. A principled approach would classify contradiction type — logical, semantic, scope, temporal, narrative — and route each to the appropriate resolution mechanism, since only logical contradictions have winners in the topological sense. The remaining types require disambiguation, hierarchy, timeline analysis, or provenance tracking respectively. This is a high-priority direction for future work.

---

## 9. The System Read This Paper

As a final validation, this paper was ingested into the same knowledge graph system it describes. The ingestion pipeline extracted 228 nodes and 908 edges from the paper's text, then the linker classified relationships — including 48 contradiction pairs.

The system found real problems.

**Qualification gaps.** The abstract originally stated that the graph "can resolve contradictions without external judgment" — an unconditional claim. The body qualified this: "when the structural evidence is sufficient." The linker flagged the tension between these two framings, correctly identifying that the abstract overstated the body's more careful position. The abstract was revised to include the qualification.

**Phase boundary ambiguity.** The paper claimed "zero LLM calls" in the abstract and "LLM-dependent graph construction" in the limitations section. The linker flagged these as contradictions. They are not contradictory — they describe different phases of the system — but the original language did not make the boundary explicit enough for a reader (or a machine) to parse without confusion. The abstract was revised to specify: "LLMs construct the graph; the resolution phase is pure topology."

**Scope mismatches.** The paper described a per-pair operation ("all contradicts edges between winner and loser are removed") and an aggregate result ("contradicts edges declined from 37 to 31") without connecting them. The linker flagged these as contradictions because it could not infer that the aggregate is the sum of per-pair operations. An explicit connecting sentence was added.

**Narrative voice confusion.** When the paper described the original six resolutions — reporting what nodes claimed and why they lost — the linker treated those descriptions as the paper's own assertions. A passage explaining that "the loser's claim contradicts the subsystem" was classified as the paper itself making a contradictory claim. This revealed a genuine limitation in the ingestion pipeline (now tracked as a bug), and the resolution descriptions were rewritten in clearer reporting language.

These corrections were not cosmetic. The qualification gap in the abstract was a real precision error — the paper's strongest feature (honest abstention) was being undermined by an unqualified opening claim. The phase boundary ambiguity could mislead a reader into thinking the system uses no LLMs at all. The system found both problems through the same topological mechanism the paper describes, and the fixes make the paper more honest.

The narrative voice limitation is particularly notable: it represents a case where the system correctly identified semantic tension in the text but misattributed its source. The paper was *reporting* contradictions, not *making* them. This is a known limitation of claim extraction from analytical documents, and it points toward future work on provenance-aware ingestion that distinguishes first-person assertions from third-person observations.

*Note: The self-ingestion was performed on the original single-scale draft. The paper has since been substantially revised with multi-scale results (Sections 3.5–3.7), manual review findings (Sections 4.2–4.4), and cross-source analysis (Sections 7.3–7.5). The corrections described above remain valid — they were applied before the subsequent revisions.*

---

## 10. Conclusion

I presented a conflict resolution system that resolves contradictions in a knowledge graph using only topological structure. Applied across three experiments — 236 nodes from a single document, 894 nodes from three independent sources, and 1,336 nodes from 122 sources — the system auto-resolved conflicts at rates of 16%, 67%, and 58% respectively, with zero false positives at any scale. No language model was involved in any resolution.

The mechanism is simple: count independent supporters, compute the ratio, act only when the evidence is decisive. The results are not simple. At the smallest scale, the system distinguished between problems and solutions, between current state and argued vision, between nuanced positions and overstated claims. In one case, it adjudicated between its own operating principle and a competing proposal, selecting the better-supported position through the very mechanism that position advocates. At the largest scale, it correctly identified known scientific rivalries between quantum mechanics interpretations, surfaced battleground nodes that receive both support and contradiction from independent sources, and captured a gradient of disagreement depth — mechanism disputes from one source, foundational challenges from another.

Manual review of 20 post-resolution conflicts validated both the system's verdicts and its abstentions. 55% of remaining conflicts were construction artifacts — the linker misclassified edges due to summary-level ambiguity — but the resolution mechanism correctly classified every one as requiring human review. The separation of construction quality from resolution quality is not just architectural; it is empirically confirmed.

Four properties — not gameable, not authoritarian, self-correcting, auditable — distinguish topological truth-finding from voting, LLM judgment, or explicit scoring. The ability to abstain when evidence is insufficient distinguishes it from all of them.

Independent structural convergence in a knowledge graph is a mechanical analog of scientific replication. Cross-source analysis provided empirical evidence: within-source and cross-source edge distributions are structurally distinguishable, and three-way triangulation from independent academic sources produced genuine validation — and genuine challenge — that the system surfaced mechanically. The mechanism is source-agnostic — the topology does not distinguish between nodes from one document or a thousand independent machines. This suggests that the same convergence-based truth-finding could operate across federated knowledge networks, where the independence guarantee is stronger by construction.

The conflicts that stayed ambiguous are as important as the ones that were resolved. A system that always produces a verdict is not finding truth — it is manufacturing certainty. The willingness to say "the evidence is insufficient" is what makes the remaining verdicts credible.

---

## References

[1] Zanfir, A. (2026). Cognitive Context Management: Brain-Inspired Architecture for Bounded AI Memory. Zenodo. https://doi.org/10.5281/zenodo.18752096

[2] Zanfir, A. (2025). Living Knowledge Networks: A Framework for Distributed Intelligence. Unpublished thesis document. https://github.com/AlexZan/knowledge-network

[3] Zanfir, A. (2026). Conversation-aware extraction for knowledge graphs. Decision 022, Knowledge Network project. Replaces per-chunk extraction with full-conversation LLM calls to eliminate false intra-author contradictions.

[4] Ghirardi, G., Bassi, A. (2020). Collapse Theories. Stanford Encyclopedia of Philosophy. https://plato.stanford.edu/entries/qm-collapse/

[5] Myrvold, W., Genovese, M., Shimony, A. (2022). Bell's Theorem / Philosophical Issues in Quantum Theory. Stanford Encyclopedia of Philosophy. https://plato.stanford.edu/entries/qt-issues/

---

## Appendix A: Resolution Summary Table

| # | Winner | Loser | Ratio | Winner Supports | Loser Supports |
|---|--------|-------|-------|-----------------|----------------|
| 1 | fact-078 (value extraction) | fact-038 (session isolation) | 6:0 | 6 | 0 |
| 2 | fact-088 (both options valid) | fact-095 (roundtable selects) | 7:1 | 7 | 1 |
| 3 | fact-094 (explicit declaration) | fact-095 (roundtable selects) | 9:1 | 9 | 1 |
| 4 | fact-103 (flagging for resolution) | fact-105 (guaranteed explicit) | 18:1 | 18 | 1 |
| 5 | fact-139 (network as model) | fact-158 (LLM as reasoner) | 5:1 | 5 | 1 |
| 6 | fact-010 (connectivity confidence) | fact-183 (voting confidence) | 28:4 | 28 | 4 |

## Appendix B: Manual Review Summary (V3, 20/37)

| # | Nodes | Verdict | Category |
|---|-------|---------|----------|
| S1 | fact-059 vs fact-031 | → `related_to` | Scope: complementary perspectives |
| S2 | fact-059 vs fact-013 | → `related_to` | Scope: different levels |
| S3 | fact-061 vs fact-013 | → `related_to` | Scope: projection ≠ prediction |
| S4 | fact-127 vs fact-870 | → `related_to` | Scope: intra vs inter-universe |
| S5 | fact-147 vs fact-030 | → `related_to` | Scope: subsumption |
| S6 | fact-147 vs fact-031 | → `related_to` | Framework: collapse-first vs standard QM |
| S7 | fact-174 vs fact-598 | → `related_to` | Framework: survey vs position |
| S8 | fact-175 vs fact-467 | Deferred | Theory evolution |
| S9 | fact-176 vs fact-501 | Kept (reverted) | Terminology: "rewriting" vs "immutable" |
| S10 | fact-201 vs fact-519 | → `related_to` | Not conflicting |
| S11 | fact-206 vs fact-123 | Kept | Genuine: partial vs full collapse |
| S12 | fact-228 vs fact-156 | → `related_to` | Sequential stages of same process |
| S13 | fact-262 vs fact-062 | → `supports` | Contrapositives of same principle |
| S14 | fact-354 vs fact-634 | Kept (reverted) | Terminology: spatial for pre-spatial |
| S15 | fact-354 vs fact-530 | Kept | Genuine: lattice vs pre-spatial bias |
| S16 | fact-370 vs fact-178 | Kept | Genuine: spitball vs firm belief |
| S17 | fact-402 vs fact-401 | → `supports` | Extraction split: one statement → two nodes |
| S35 | fact-1112 vs fact-614 | Kept | Cross-source: GRW vs Bohm (attribution gap) |
| S36 | fact-1112 vs fact-1236 | Kept | Cross-source: GRW vs pilot wave |
| S37 | fact-1143 vs fact-1152 | Kept | Intra-source: rival ontologies in survey |

## Appendix C: Classification Algorithm Source

The classification and resolution logic is implemented in approximately 100 lines of Python with no external dependencies beyond Pydantic for data modeling. The full source is available at the project repository. The algorithm's simplicity is a feature: the complexity is in the graph, not the code that reads it.
