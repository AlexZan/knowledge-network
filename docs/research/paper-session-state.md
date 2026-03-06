# Paper Session State — Topological Truth (Paper 2)

> Updated 2026-03-06 after CachyOS migration and 3-source conflict resolution run.

## What We Were Doing

Assessing what to add to the Topological Truth white paper (Paper 2) based on findings accumulated since the first draft. The 3-source conflict resolution run is now complete.

## Paper Location

- **Source**: `docs/research/topological-truth-paper.md`
- **Markdown source for Paper 1 (CCM)**: `docs/ccm-whitepaper.md` (published, DOI: 10.5281/zenodo.18752096)
- **Paper roadmap**: `docs/research/paper-roadmap.md`

## Current Paper Draft State

The topological truth paper draft was written against the **236-node, single-document graph** (thesis.md). Since then, the physics theory KG has grown to 894 nodes across 3 independent sources, and a full conflict resolution run has been completed.

## New Empirical Data Available (since draft)

### 3-Source Conflict Resolution (2026-03-06)

**Graph**: 894 active nodes, 5020 edges, 163 contradictions
**Sources**: 730 theory nodes (7 conversations), 66 SEP-collapse nodes, 98 SEP-QT nodes

| Metric | First Run (thesis.md) | 3-Source Run |
|--------|----------------------|--------------|
| Nodes | 236 | 894 |
| Edges | 877 | 5,020 |
| Contradictions | 37 | 163 |
| Auto-resolved | 6 (16%) | 110 (67%) |
| Strong recommendations | 17 | 19 |
| Ambiguous | 14 | 34→25 (post-resolve) |
| Errors | 0 | 0 |
| PageRank iterations | — | 45 |
| Runtime | — | 53ms |

**Key finding**: Auto-resolve rate jumped from 16% to 67% at scale. Larger graphs produce more lopsided support ratios because well-supported claims accumulate evidence from multiple sources, making topology-based resolution more decisive.

**Data**: `docs/research/conflict-resolution-findings.md` (Second Run section)

### Cross-Author Analysis (2026-03-05)

- 293 cross-author edges (SEP-collapse → theory): 24 supports, 24 contradicts, 245 related_to
- 391 cross-author edges (SEP-QT → theory): 11 supports, 7 contradicts, 373 related_to
- 95% of theory nodes have zero cross-author contact — theory extends far beyond established literature
- Core disagreement: conditional (entropy-triggered) vs unconditional (spontaneous) collapse — 22/24 contradictions trace to this single fork
- False positive rate: 3/27 contested nodes (11%)

**Data**: `docs/research/cross-author-analysis.md`, `docs/research/v2-reingestion-findings.md`

### Prior Multi-Source Data (still relevant)

- 5 documents ingested: 643 nodes, 3,587 edges, 155 contradictions
- Zero false positives in 13 cross-source contradiction edges
- Cross-source structural signature: 77%/18%/5% (related_to/supports/contradicts) vs 56%/39%/6% within-document
- 24 nodes reached `high` confidence from 3+ independent sources
- 19 contested nodes, 0 false positives — 9/19 (47%) represent theory evolution

**Data**: `docs/research/ingestion-pipeline-experiments.md` (Experiments 2-3)

## Assessment: What to Add (Updated Plan)

### Priority 1 — 3-Source Conflict Resolution Data (headline result)

The paper's Section 3 uses 236-node data. Replace/supplement with 894-node, 3-source results:
- 163 contradictions → 110 auto-resolved (67%) with zero LLM calls
- Scale effect: auto-resolve rate 16% → 67% as graph grows
- Cross-author conflicts are genuine (conditional vs unconditional collapse)

**Where to add**: Section 3 (Empirical Results), Section 7 (Independent Convergence)

### Priority 2 — Cross-Source Structural Signatures

Empirically distinguishable edge distribution between within-source and cross-source edges. The independence guarantee is observable in the data.

**Where to add**: New subsection in Section 3 or Section 7

### Priority 3 — Revise Limitations (Section 8)

- "Single-source graph" limitation is now removed — we have 3 independent sources
- "Support count not support depth" partially addressed by edge weight by reasoning quality (1.0x/0.5x)
- 11% false positive rate on contested nodes in cross-author content (up from 0% single-author)

**Where to add**: Section 8

### Priority 4 — Salience vs Confidence, Edge Weights, Semantic Edges

Same as previous session state — still relevant but lower priority than the new conflict data.

## Experiments Still Available

1. **Three-way interaction analysis** — where do all 3 sources agree? Where does each stand alone? (next up)
2. **Batch remaining 181 physics conversations** — would test at much larger scale
3. **Run conflict resolution on remaining 38** — manual review of strong_recommendation and ambiguous pairs

## Key Files

| File | Contents |
|------|----------|
| `docs/research/topological-truth-paper.md` | Paper 2 draft |
| `docs/research/conflict-resolution-findings.md` | Both conflict resolution runs (236-node + 894-node) |
| `docs/research/cross-author-analysis.md` | SEP collapse theories vs physics theory |
| `docs/research/v2-reingestion-findings.md` | Full v2 experiment writeup |
| `docs/research/ingestion-pipeline-experiments.md` | Experiments 1-4 data |
| `docs/research/paper-roadmap.md` | 3-paper sequence plan |
| `docs/research/three-way-interaction-analysis.md` | Theory vs collapse vs QM foundations |
| `docs/decisions/019-semantic-vs-logical-edges.md` | related_to edge type |
| `docs/decisions/020-salience-confidence-separation.md` | Salience, edge weights, concept nodes |
| `docs/decisions/021-contradicts-gate-prompt.md` | Contradicts gate improvement |
| `docs/ccm-whitepaper.md` | Paper 1 (published) |

## Project Context

- Python prototype, slices 1-14b complete, 731 tests passing
- Physics theory KG: `/data/physics-theory-kg/` (894 nodes post-resolution, 110 superseded)
- Source conversations: `/data/physics-theory/` (188 total, 7 ingested)
- OS: CachyOS, venv at `.venv/`, MCP server via `bin/oi-mcp`
- LLM: Cerebras `gpt-oss-120b` via litellm
