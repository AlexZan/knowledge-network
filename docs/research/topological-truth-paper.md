# Topological Truth: Conflict Resolution Through Knowledge Graph Structure

Alexander Zanfir, Independent Researcher

March 2026

---

## Abstract

When conclusions are recorded as nodes in a knowledge graph with typed edges between them, the graph develops structural properties that can resolve contradictions — when the structural evidence is sufficient — without external judgment. I present a conflict resolution system that classifies and resolves contradictions using only the topology of supporting edges — no large language model, no human judge, no voting mechanism. LLMs construct the graph; the resolution phase is pure topology. Applied to a 236-node knowledge graph (877 edges, 37 contradiction pairs), the system automatically resolved 6 conflicts where topological support was overwhelming (≥5x ratio), correctly classified 17 as strong recommendations requiring review, and left 14 genuinely ambiguous — correctly identifying that its own evidence was insufficient to act. Zero LLM calls were involved in any conflict classification or resolution. One resolution is self-referential: the system was asked to adjudicate between "confidence from topology" and "confidence from voting" as competing approaches, and the topology chose topology — the system demonstrated its own thesis through its own operation. I argue that independent structural convergence in a knowledge graph is a mechanical analog of scientific replication, and present four properties that distinguish this approach from voting, LLM judgment, or explicit scoring: it is not gameable, not authoritarian, self-correcting, and auditable end-to-end. The system's honest limitation — 14 conflicts stayed ambiguous because the evidence was insufficient — is itself a form of epistemic integrity that most truth-finding systems lack.

---

## 1. Introduction

### 1.1 The Problem

Machine truth-finding is usually framed as a classification task. Given competing claims, select a winner by: polling human judges, asking a language model, counting votes, or computing a score. Each approach embeds an authority — someone or something that *decides*. The decision may be correct, but the mechanism is opaque, gameable, or both.

Voting systems are susceptible to coordination attacks. LLM-based judgment inherits the biases of training data and produces non-reproducible verdicts. Human scoring is expensive and doesn't scale. Explicit confidence scores are arbitrary — who decides that a claim merits 0.8 rather than 0.7? All of these approaches treat truth-finding as a judgment problem: apply an evaluator to competing claims and accept the verdict.

This paper proposes a different framing. Instead of *judging* claims, we examine the *structural support* each claim has accumulated in a knowledge graph. A claim supported by 28 independent nodes from across the graph is not popular — it is convergent. A claim with 1 supporter is not necessarily wrong — it is underspecified. The topology itself becomes the authority.

### 1.2 Prior Work: Conclusion-Triggered Compaction

This work builds on Cognitive Context Management (CCM) [1], which demonstrated that compacting AI memory at conclusion boundaries — rather than at capacity limits — achieves O(1) bounded working memory with 93–98% token savings. CCM's core mechanism extracts conclusions from resolved reasoning threads and persists them as summary nodes with links to their source material.

This paper asks the next question: when those compacted conclusions accumulate as nodes in a knowledge graph with typed edges between them, can the graph's own topology serve as an authority for resolving contradictions? The answer, demonstrated empirically, is yes — for conflicts where the structural evidence is sufficient, and honestly no for conflicts where it is not.

### 1.3 Contributions

1. A topology-based conflict resolution algorithm that classifies contradictions by support ratio and resolves them through supersession, with zero LLM involvement in any classification or resolution
2. Empirical results from a 236-node knowledge graph: 6 auto-resolutions, 17 strong recommendations, 14 honest ambiguities
3. A self-referential result in which the system adjudicated between its own thesis (topology-as-confidence) and an alternative (voting-as-confidence), and the topology chose topology
4. A second self-referential result: the system ingested this paper, found precision errors in its claims, and the paper was corrected based on the system's own conflict report (Section 9)
5. An argument that independent structural convergence is a mechanical analog of scientific replication — the closest algorithmic approximation of how empirical truth is established

---

## 2. Mechanism

### 2.1 Graph Structure

The knowledge graph consists of nodes and typed edges. Nodes represent conclusions extracted from documents — facts, decisions, and preferences — each with a unique identifier, summary text, source provenance, and status (active or superseded). Edges encode relationships: `supports` (one node provides evidence for another), `contradicts` (two nodes make incompatible claims), `exemplifies` (one node is a specific instance of another), and `supersedes` (one node has replaced another through conflict resolution).

The graph used in this study was constructed by ingesting a thesis document through a batch linker that uses LLM-based semantic classification to determine edge types between node pairs. This is a deliberate architectural separation: **LLMs construct the graph; topology arbitrates disputes within it.** The perception phase (building the graph) may involve language models. The judgment phase (resolving conflicts) does not. The novel contribution is in the judgment phase.

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

The knowledge graph was constructed by ingesting a thesis document describing the Living Knowledge Networks framework [2]. The document covers five interconnected theses about conclusion-triggered compaction, dynamic knowledge networks, abstraction hierarchies, conflict resolution, and emergent confidence. It also references a voting-experience mechanism proposed as a potential alternative confidence model.

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

Each of the 6 resolutions removed the `contradicts` edge between the resolved pair (per Section 2.3, step 3), producing the observed decline from 37 to 31. Six resolutions produced five unique superseded nodes — one node (`fact-095`) lost two separate conflicts, confirming it as the weakest node in its local cluster.

### 3.4 The Six Resolutions

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

The most significant resolution, analyzed in detail in Section 6.

---

## 4. What the System Refused to Resolve

Fourteen of 37 contradictions were classified as ambiguous. The system produced no recommendation and took no action. These fall into three categories:

**Genuinely underdetermined conflicts.** Both sides have zero or equal support. Neither claim has accumulated independent backing, so the topology has nothing to compare. These are not failures — they are nodes that have not yet participated in enough of the graph's structure to be evaluable. They may resolve as the graph grows, or they may remain permanently ambiguous.

**Near-equal support with insufficient gap.** Both sides have supporters, but the ratio falls below the classification threshold. A 3:2 advantage is a signal, not a verdict. The system reports it but does not act.

**Novel claims without structural context.** Some contradictions involve nodes that are topologically isolated — connected to the graph through only the contradiction edge itself, with no support from elsewhere. The system correctly identifies these as unevaluable: without independent support, there is nothing for the topology to measure.

The 14 ambiguous conflicts are not a weakness of the system. They are its most important feature. A truth-finding mechanism that always produces a verdict is not finding truth — it is manufacturing certainty. The willingness to say "the evidence is insufficient" is the property that separates measurement from opinion. Scientific peer review operates on the same principle: insufficient evidence means no conclusion, not a weaker conclusion.

After the 6 auto-resolutions, the remaining distribution shifted: 12 strong recommendations and 12 ambiguous (24 total). The strong recommendations await human review — the system has an opinion but recognizes it lacks the authority to act unilaterally below its confidence threshold.

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

### 7.3 The Limitation Is the Feature

Fourteen of 37 conflicts remained ambiguous. The system did not force a resolution. For novel claims without sufficient structural context, it reported "insufficient evidence" and waited.

This is not a failure rate of 38%. It is an integrity rate of 38%. The system knows when it doesn't know. Most truth-finding systems — LLM judgment, majority voting, explicit scoring — will always produce an answer. They cannot express "I don't have enough information," because their mechanisms are designed to produce outputs, not to abstain. The ability to abstain when evidence is insufficient is what makes the remaining verdicts credible.

---

## 8. Limitations

**Single-source graph.** The 236-node graph was constructed from a single thesis document. While the document contains diverse argumentative threads that produce genuinely independent nodes, the independence guarantee would be stronger across multiple documents from different authors. The mechanism is source-agnostic — topology does not distinguish between nodes from one document or a thousand — but the empirical demonstration has not yet been performed at multi-source scale.

**Support count, not support depth.** The current algorithm counts inbound support edges without weighting by the supporters' own connectivity. A node supported by five highly-connected nodes should, in principle, be stronger than one supported by five isolated nodes. The classification algorithm uses raw counts; a recursive confidence-weighted variant would be more expressive. In this first evaluation, raw counts were sufficient for the auto-resolvable threshold, but more nuanced conflicts may require depth-aware scoring.

**Separation of perception and judgment.** The architecture deliberately separates graph construction (LLM-assisted) from conflict resolution (pure topology). This means the quality of topological judgment is bounded by the quality of the graph the LLM built. Errors in edge classification — a `supports` edge that should be `contradicts`, or a missed relationship — would propagate into the topology and affect resolution quality. The resolution algorithm is deterministic and auditable; the graph construction that feeds it is not. This is an intentional trade-off: LLMs are good at semantic classification but poor at consistent judgment under contradiction, so each phase uses the tool suited to it.

**Threshold sensitivity.** The 5x auto-resolution threshold and 2x/3x recommendation thresholds are parameters, not derived quantities. Different thresholds would change the classification of the 37 conflicts. The 5x threshold was chosen for conservatism — all 6 auto-resolutions were unambiguously correct — but the optimal threshold likely depends on graph size, density, and domain.

**Temporal naivety.** The algorithm does not consider when nodes or edges were created. A node supported by 28 edges from 2024 is treated identically to one supported by 28 edges from 2020. In domains where recency matters, this could be a limitation. The current design intentionally prioritizes accumulated evidence over recency — a deliberate choice documented in the project's architectural decisions — but it is a trade-off.

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

---

## 10. Conclusion

I presented a conflict resolution system that resolves contradictions in a knowledge graph using only topological structure. Applied to a 236-node graph with 37 contradictions, the system auto-resolved 6 where structural support was overwhelming, recommended action on 17, and honestly abstained on 14. No language model was involved in any resolution.

The mechanism is simple: count independent supporters, compute the ratio, act only when the evidence is decisive. The results are not simple. The system distinguished between problems and solutions, between current state and argued vision, between nuanced positions and overstated claims. In one case, it adjudicated between its own operating principle and a competing proposal, selecting the better-supported position through the very mechanism that position advocates.

Four properties — not gameable, not authoritarian, self-correcting, auditable — distinguish topological truth-finding from voting, LLM judgment, or explicit scoring. The ability to abstain when evidence is insufficient distinguishes it from all of them.

Independent structural convergence in a knowledge graph is a mechanical analog of scientific replication. It is not perfect — coherence is not correspondence, and a well-argued falsehood would pass. But it captures the essential epistemological mechanism and applies it without human judgment, model inference, or majority rule. The mechanism demonstrated here operates on a single graph. It is source-agnostic — the topology does not distinguish between nodes from one document or a thousand independent machines. This suggests that the same convergence-based truth-finding could operate across federated knowledge networks, where the independence guarantee is stronger by construction.

The 14 ambiguous conflicts are as important as the 6 resolved ones. A system that always produces a verdict is not finding truth — it is manufacturing certainty. The willingness to say "the evidence is insufficient" is what makes the remaining verdicts credible.

---

## References

[1] Zanfir, A. (2026). Cognitive Context Management: Brain-Inspired Architecture for Bounded AI Memory. Zenodo. https://doi.org/10.5281/zenodo.18752096

[2] Zanfir, A. (2025). Living Knowledge Networks: A Framework for Distributed Intelligence. Unpublished thesis document. https://github.com/knowledge-network

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

## Appendix B: Classification Algorithm Source

The classification and resolution logic is implemented in approximately 100 lines of Python with no external dependencies beyond Pydantic for data modeling. The full source is available at the project repository. The algorithm's simplicity is a feature: the complexity is in the graph, not the code that reads it.
