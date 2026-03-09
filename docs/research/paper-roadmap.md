# Paper Roadmap

> Research publication sequence for Living Knowledge Networks. Each paper proves one thing, cites the last, and stands alone.

## Paper 1: Cognitive Context Management (Published)

**Title**: Cognitive Context Management: Brain-Inspired Architecture for Bounded AI Memory

**Core claim**: Compacting AI memory at conclusion boundaries — rather than capacity limits — achieves O(1) bounded working memory with 93-98% token savings.

**Status**: Published, February 2026

**Citation**: Zanfir, A. (2026). Cognitive Context Management: Brain-Inspired Architecture for Bounded AI Memory. Zenodo. https://doi.org/10.5281/zenodo.18752096

**What it proved**: Conclusion-triggered compaction works. The compacted conclusions become persistent nodes. This is the memory management foundation — the mechanism that produces the nodes the later papers operate on.

---

## Paper 2: Topological Truth (Current)

**Title**: Topological Truth: Conflict Resolution Through Knowledge Graph Structure

**Core claim**: Topology alone — support edge ratios — is sufficient authority to resolve factual contradictions in a knowledge graph. No LLM, no human judge, no voting.

**Status**: Draft complete, March 2026

**Location**: `docs/research/topological-truth-paper.md`

**What it proves**: The hardest claim in the framework — that graph structure can *arbitrate disputes* without external judgment. If topology can resolve conflicts, the easier claims (ranking confidence, identifying well-supported nodes) follow as corollaries. The self-referential result (topology chose topology over voting) and the 14 honest abstentions are the headline findings.

**Empirical data**: Three runs — (1) 236-node single-doc graph: 37 contradictions, 6 auto-resolved. (2) 894-node 3-source graph: 163 contradictions, 110 auto-resolved (67%). (3) 1,336-node full-scale graph (120 conversations + 2 docs, conversation-aware extraction): 190 contradictions, 111 auto-resolved, 37 manual — of which 7/8 reviewed so far were false positives reclassified to `related_to`. Zero LLM calls in resolution. See `docs/research/conflict-resolution-findings.md` and `docs/research/v3-rebuild-findings.md`.

**Relationship to Paper 1**: CCM produces compacted conclusions. This paper asks: when those conclusions contradict each other, can the graph resolve it? Answer: yes, when structural evidence is sufficient; honestly no when it isn't.

---

## Paper 3: The Full System (Future)

**Title**: TBD — something like "Living Knowledge Networks: Emergent Truth from Graph Topology"

**Core claim**: A knowledge graph with typed edges, built from compacted conclusions, is a quantifiable source of truth. Confidence emerges from network topology. The graph is the model.

**Status**: Not started. Waiting for empirical results at multi-source scale.

**What it needs to prove**:
- Emergent confidence scoring from topology (not just conflict resolution, but continuous confidence)
- Ingestion at scale across multiple independent documents/sources
- The independence guarantee: convergence from separate sources is structurally distinguishable from convergence within one source
- The abstraction hierarchy / privacy gradient in practice
- Self-correction over time as new evidence arrives

**Why it's a separate paper**: The "quantifiable source of truth" claim requires demonstrating the *whole system* — ingestion, linking, confidence, conflict resolution, self-correction. Papers 1 and 2 each prove one mechanism. Paper 3 presents the unified framework and cites 1 and 2 as established foundations. Trying to prove everything in one paper dilutes each result.

**Relationship to Papers 1-2**: Paper 1 proved compaction works. Paper 2 proved topology can arbitrate. Paper 3 shows the full loop: conclusions compact into nodes, nodes accumulate edges, edges form topology, topology determines truth, truth updates as the graph grows.

---

## The Vision Beyond Papers

The three papers cover the single-graph case. Beyond that:

- **Distributed/federated knowledge networks**: Local graphs link into larger networks across machines. The same convergence mechanism operates, but with stronger independence guarantees (separate users, separate experiences, separate documents). The privacy gradient (Thesis 3) enables this — raw private nodes stay local, generalizations propagate.
- **Graph-structured training data**: A mature knowledge graph is already-organized structured data with provenance, confidence, and relationships. Fundamentally different from text corpora for model training.
- **The graph as dynamic neural network**: Training and inference merge — every conversation both uses and extends the model. The endgame described in the thesis document.

These are not papers yet. They are the direction the empirical work is heading. Each will become a paper when it has data.

---

## Development Efforts (knowledge-network KG)

Open efforts tracked in the knowledge-network KG (`mcp_search_efforts`) that may be relevant to paper work:

- `attribution-referenced-knowledge` — brainstorm how to handle third-party knowledge extracted from user chat history (e.g., Bohmian mechanics from a pasted lecture transcript getting `source: physics-theory`). Related to planned #6 (attribution-aware extraction).

Check `mcp_search_efforts` on the knowledge-network MCP server for current status.

---

## Guiding Principle

Each paper claims what it proved. Each paper acknowledges what it hasn't. Each paper points to where it leads. The restraint is what gives each paper its credibility. The 14 ambiguous conflicts that stayed ambiguous — that's the same intellectual honesty applied to the publication sequence itself.
