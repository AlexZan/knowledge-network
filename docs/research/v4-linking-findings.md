# V4 Linking Pipeline Findings

**Date:** 2026-03-15
**KG:** physics-theory (`/data/physics-theory-kg`)
**Previous version:** v3 (1,263 nodes, 8,022 edges, backed up at `/data/physics-theory-kg-v3/`)

## Pipeline Execution

| Step | Duration | Cost | Result |
|------|----------|------|--------|
| Auto-link same group | ~5s | Free | 28,507 `related_to` edges across 199 groups |
| Embeddings (nomic-embed-text, GPU) | 30s | Free | 2,361 vectors |
| Cross-group LLM linking (Cerebras gpt-oss-120b) | 39min | ~$10 | 13,648 edges (3,060 supports, 254 contradicts, 10,334 related_to) |

## V3 vs V4 Comparison

| Metric | V3 | V4 | Change |
|--------|----|----|--------|
| Active nodes | 1,263 | 2,361 | +87% |
| Sources | 122 | ~205 | +68% |
| Total edges | 8,022 | 42,155 | +425% |
| `supports` | ~2,800 | 3,060 | +9% |
| `contradicts` | 190 | 254 | +34% |
| `related_to` | ~5,000 | 38,841 | +677% |
| Edges/node | 6.4 | 17.9 | +180% |
| Contradictions/node | 0.150 | 0.108 | -28% |

## Key Findings

### 1. Contradiction rate reduced by 28%

V3: 0.150 contradictions per node. V4: 0.108. The `exclude_same_group` filter in `find_candidates()` prevents the LLM from seeing same-conversation pairs as cross-group candidates. In v3, these pairs were sent to the LLM, which sometimes misclassified scope/framing differences within a single conversation as contradictions. Filtering them out lets the LLM focus on genuine cross-source conflicts.

254 contradictions remain. Breakdown:
- 96 cross-source (physics-theory ↔ project-sources, physics-theory ↔ sep-qt-issues, etc.)
- 158 same-source but cross-conversation (different ChatGPT conversations within physics-theory)

The same-source contradictions are expected — the author's thinking evolved across conversations. Cross-source contradictions between the author's framework and SEP articles represent genuine theoretical disagreements.

### 2. Cross-source bridging works

1,966 unique provenance group pairs are connected by cross-group edges. The most connected pairs:
- SEP articles ↔ SEP articles: 236 edges (two QM reference articles cross-referencing)
- Author conversations ↔ author PDFs: 233+ edges (theory discussions linking to formal writeups)
- Author conversations ↔ SEP articles: 125+ edges (framework claims linked to established QM)

This is the graph structure that makes confidence meaningful — claims supported by both the author's conversations AND independent SEP articles have genuinely higher topological confidence than claims supported only by repeated author statements.

### 3. Support inflation confirmed — validates need for topology-based weight

The top 5 most-supported nodes:

| Node | Inbound supports | Unique groups | Summary |
|------|-----------------|---------------|---------|
| fact-043 | 443 | 131 | Deterministic system needs randomness injection for time/evolution |
| fact-042 | 337 | — | Collapse occurs only when deterministic system punctured by irreducible randomness |
| fact-045 | 254 | — | Collapse-Conservation Principle |
| fact-044 | 185 | — | Collapse as conservation mechanism |
| fact-090 | 168 | — | Seeded Collapse: prior events guide future collapses |

These are all core thesis statements repeated across many conversations and documents. fact-043 has 443 supporters from 131 different groups — but 314 of those supporters are from `physics-theory` (the author's own ChatGPT conversations). Only 4 are from `sep-qt-issues` (independent source).

Under the current binary edge weighting, all 443 supporters contribute equally to PageRank. A paraphrase of the thesis from conversation 47 counts the same as an independent validation from a Stanford Encyclopedia article. This is the exact inflation pattern identified in `auto-resolution-review-findings.md`.

**Planned fix:** Roadmap item #9 — topology-based support weight. Replace binary edge weight (1.0/0.5) with computed weight from embedding dissimilarity + source independence. Paraphrases (high cosine, same author) → near-zero weight. Independent evidence (low cosine, different source) → full weight. See `support-weight-from-topology.md`.

### 4. `related_to` dominates the edge distribution

92.1% of LLM-classified edges are `related_to` (10,334 out of 13,648). Only 7.3% are `supports` and 0.6% are `contradicts`. This is a healthy ratio for a single-author physics theory KG — most concepts are related but don't directly support or contradict each other.

The 28,507 auto-link `related_to` edges (same-group) plus 10,334 LLM-classified `related_to` edges create a dense connectivity fabric. The 3,060 `supports` edges on top of that provide the reasoning structure.

### 5. Edge distribution by source pair

| Source pair | Edges | Notes |
|-------------|-------|-------|
| physics-theory ↔ physics-theory | 18,646 | Author's conversations cross-linking |
| project-sources ↔ project-sources | 10,883 | Author's PDFs cross-linking |
| sep-qt-issues ↔ sep-qt-issues | 6,912 | Two SEP articles cross-linking |
| physics-theory ↔ project-sources | 4,895 | Conversations ↔ formal writeups |
| physics-theory ↔ sep-qt-issues | 791 | Author's framework ↔ established QM |
| project-sources ↔ sep-qt-issues | 28 | PDFs ↔ SEP (sparse) |

The physics-theory ↔ sep-qt-issues bridge (791 edges) is the most valuable for confidence — it connects the author's claims to independent academic sources. The project-sources ↔ sep-qt-issues bridge (28 edges) is surprisingly sparse, suggesting the author's formal PDFs use different terminology than the SEP articles, even when discussing the same concepts.

## Data Quality

- **Zero errors** in the linking run (2,361 nodes processed, 252 skipped as unlinkable types or no candidates)
- **No parse failures** in the LLM output
- **Same-group filtering worked correctly** — 199 groups identified, auto-link edges created only within groups
- **Auto-link edges have no reasoning field** — distinguishable from LLM-classified edges for downstream analysis

Note: The initial auto-link run produced a false alarm — a diagnostic script checked the wrong field (`provenance` instead of `provenance_uri`), making it appear that all 2,361 nodes were in one group. The actual grouping was correct (199 groups). The function uses `provenance_uri` which was populated on all nodes.

## Next Steps

1. **Implement topology-based support weight (#9)** — fix the inflation before clustering builds on it
2. **Clustering + concept synthesis** — group near-duplicate nodes, create principle nodes
3. **Conflict report** — review the 254 contradictions, classify auto-resolvable vs ambiguous
4. **Validate confidence** — after #9, check that confidence levels reflect independent evidence rather than repetition
