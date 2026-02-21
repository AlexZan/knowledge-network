# Cognitive Context Management (CCM)

**Brain-inspired bounded context architecture for LLMs.**

CCM draws from neuroscience research on working memory, consolidation, and retrieval to manage LLM context. Instead of compressing when context fills, CCM compresses when reasoning resolves -- producing O(1) working memory (~4K tokens constant) regardless of conversation length.

Paper: [Cognitive Context Management: Brain-Inspired Architecture for Bounded AI Memory](docs/ccm-whitepaper.md) (arXiv preprint, February 2026)

## Key Results

- **93-98% token savings** across three real conversations (58K-240K tokens)
- **O(1) bounded working memory** -- ~4K tokens constant vs O(n) linear growth
- **Zero storage loss** -- all raw conversation data preserved and retrievable
- **Live-tested** end-to-end with real LLM calls across diverse topics

## How It Works

Four-tier architecture inspired by human memory:

| Tier | Brain Analog | Function |
|------|-------------|----------|
| Raw Log | Episodic memory | Full verbatim record, append-only, never in context |
| Manifest | Semantic memory | Effort index with summaries, searchable |
| Open Efforts | Zeigarnik buffer | Unresolved topics, elevated accessibility |
| Working Context | Working memory | Bounded active subset (~4 chunks), passed to model |

Core mechanisms:
- **Conclusion-triggered compaction** -- efforts compact to summaries when resolved, not when space runs out
- **Relevance-based displacement** -- new topics push out less-relevant ones (interference, not time decay)
- **Salience decay** -- expanded efforts auto-collapse after N turns without reference
- **Cue-based retrieval** -- summaries act as retrieval cues; `search_efforts` finds evicted content

## Repository Structure

```
src/oi/               # Implementation
  orchestrator.py     #   Turn processing, context assembly
  tools.py            #   Effort lifecycle tools (open, close, expand, search)
  decay.py            #   Salience decay, summary eviction
  state.py            #   State I/O (manifest, expanded, session)
  llm.py              #   LLM API interface
  tokens.py           #   Token counting
  prompts/            #   System prompt templates

tests/                # Test suite (101 unit + integration + e2e)
  test_orchestrator.py
  test_tools.py
  test_decay.py
  test_proof_run.py   #   Proof runs demonstrating bounded growth
  test_e2e_real_llm.py  # End-to-end with real LLM calls
  test_integration_llm.py

scripts/              # Paper reproduction
  ccm_comparison.py   #   Retroactive CCM analysis on conversation logs

docs/
  ccm-whitepaper.md   #   Paper source (single source of truth)
  research/           #   Comparison results data
  slices/             #   Implementation specs per slice
  thesis.md           #   Broader Knowledge Network vision
```

## Reproducing Paper Results

```bash
# Run unit + integration tests
python -m pytest tests/ -v --ignore=tests/experiments

# Run e2e tests with real LLM (requires DEEPSEEK_API_KEY)
python -m pytest tests/test_e2e_real_llm.py -v -s

# Run retroactive comparison (requires conversation log + config)
python scripts/ccm_comparison.py --config scripts/config-example.json
```

## Requirements

- Python 3.11+
- `litellm`, `pyyaml`, `tiktoken` (see pyproject.toml)
- `DEEPSEEK_API_KEY` for e2e tests and live usage

## License

CC BY 4.0
