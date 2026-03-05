# Paper Session State — Topological Truth (Paper 2)

> Saved 2026-03-05 for continuation after NixOS → new distro migration.

## What We Were Doing

Assessing what to add to the Topological Truth white paper (Paper 2) based on findings accumulated since the first draft. The user is also running experiments recommended below with the dev agent (in parallel).

## Paper Location

- **Source**: `docs/research/topological-truth-paper.md`
- **Markdown source for Paper 1 (CCM)**: `docs/ccm-whitepaper.md` (published, DOI: 10.5281/zenodo.18752096)
- **Paper roadmap**: `docs/research/paper-roadmap.md`

## Current Paper Draft State

The topological truth paper draft is complete but was written against the **236-node, single-document graph** (thesis.md). Since then, 4 more experiments and 3 architectural decisions have generated new findings that should be folded in.

## Assessment: What to Add (Agreed Plan)

### Priority 1 — Multi-Source Data (removes the paper's self-acknowledged weakness)

The paper's Section 8 admits "single-source graph" as the biggest limitation. We now have:
- 5 documents ingested: 643 nodes, 3,587 edges, 155 contradictions
- **Zero false positives** in 13 cross-source contradiction edges
- **Cross-source structural signature**: 77%/18%/5% (related_to/supports/contradicts) vs 56%/39%/6% within-document — empirically distinguishable
- **24 nodes reached `high` confidence** from 3+ independent sources (first emergence)
- **Contested node stability**: 19 contested at both 2-doc and 5-doc scale, 0 false positives
- Data is in `docs/research/ingestion-pipeline-experiments.md` (Experiments 2-3)

**Where to add**: Expand Section 3 (Empirical Results) + new subsection on cross-source structural signatures + revise Section 8 limitations.

### Priority 2 — Contested Node Analysis (strengthens "honest abstention" narrative)

- 19 contested nodes, manually classified: 0 false positives
- 9/19 (47%) = theory evolution across conversations — unique capability
- 3 = theory vs standard QM (correct), 4 = within-theory tension, 2 = borderline

**Where to add**: Section 4 (What the System Refused to Resolve) + potentially a 5th property in Section 5 ("surfaces intellectual evolution").

### Priority 3 — Salience vs Confidence Separation

- `fact-019` (self-referential result): high confidence, salience 0.02
- `decision-074`: salience 0.54, medium confidence
- Proves topological centrality ≠ logical justification — two distinct epistemic signals

**Where to add**: New section ~8.5 or fold into Section 7 (Independent Convergence).

### Priority 4 — Edge Weight by Reasoning Quality

- 1.0x for edges with reasoning justification, 0.5x without
- Partially addresses the "support count not support depth" limitation in Section 8

**Where to add**: Brief note in Section 8 revising the limitation.

### Priority 5 — Semantic vs Logical Edge Separation (Decision 019)

- `related_to` edge type: logical=false, excluded from PageRank
- 42% of edges reclassified from `supports` to `related_to` in run 5
- Architecturally significant for what "support" means

**Where to add**: Section 2 (Mechanism) or new subsection.

### Priority 6 — Contradicts Gate (Decision 021)

- 4/4 within-theory tensions reclassified from `contradicts` to `related_to`
- Shows iterative improvement in graph construction quality

**Where to add**: Brief mention in Section 8 (Limitations → perception/judgment separation).

## Experiments Still In Progress (Dev Agent)

These were recommended and the user said they're being run:

1. **Re-run conflict resolution on the 5-doc graph** (643 nodes, 155 contradictions) — would give much stronger empirical section than current 236-node results
2. **Full re-ingestion with Decision 021 gate** — validate contested count drops from 19 to ~15 at scale
3. **Cross-author data** — even one document by a different author would test independence guarantee

## Key Files

| File | Contents |
|------|----------|
| `docs/research/topological-truth-paper.md` | Paper 2 draft |
| `docs/research/ingestion-pipeline-experiments.md` | Experiments 1-4 data |
| `docs/research/conflict-resolution-findings.md` | Original 236-node conflict data |
| `docs/research/paper-roadmap.md` | 3-paper sequence plan |
| `docs/decisions/019-semantic-vs-logical-edges.md` | related_to edge type |
| `docs/decisions/020-salience-confidence-separation.md` | Salience, edge weights, concept nodes |
| `docs/decisions/021-contradicts-gate-prompt.md` | Contradicts gate improvement |
| `docs/ccm-whitepaper.md` | Paper 1 (published) |

## Project Architecture Context

- Python prototype, slices 1-14b complete
- 908 active nodes in knowledge-network's own KG (`~/.oi/`)
- 643 nodes in physics theory KG (`/mnt/storage/physics-theory-kg/`)
- MCP server: FastMCP, stdio transport
- Test baseline: 727 passed, 1 skipped, 55 deselected
- LLM: Cerebras `gpt-oss-120b` via litellm

## Migration Notes

- Venv at `/tmp/oi-venv` will be gone — rebuild needed
- NixOS-specific `LD_LIBRARY_PATH` and nix store paths in CLAUDE.md will be invalid — update after migration
- Ollama models at `/mnt/storage/ollama/models/` — path may change
- `.env` file has all API keys — survives if `/mnt/storage/Dev/knowledge-network/` is preserved
- `nix-shell -p gh` for GitHub CLI — will need direct install on new distro
