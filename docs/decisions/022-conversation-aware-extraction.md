# Decision 022: Conversation-Aware Extraction

**Date**: 2026-03-06
**Status**: Accepted

## Context

The current ingestion pipeline for ChatGPT conversations splits each conversation into turn pairs (user + assistant) and sends each pair independently to the LLM for claim extraction. This produces fragmented claims and false conflicts because:

1. **No conversational context** — the LLM sees turn 3 without knowing turns 1-2. Exploratory ideas proposed in turn 1 and refuted in turn 3 get extracted as separate "facts."
2. **Every turn gets extracted** — hypotheticals, rhetorical questions, and scaffolding discussion all become claims.
3. **No synthesis** — a conclusion that emerges across 5 turns becomes 5 fragment-claims instead of 1 synthesized node. This directly causes intra-author contradictions in the graph (e.g., "screen collapses first" vs "detector collapses first" from the same person refining their position).
4. **Expensive** — N LLM calls per conversation (one per turn pair) instead of 1.

This contradicts the project's own thesis: CCM (Paper 1) says to compact at conclusion boundaries, not capacity limits. The ingestion pipeline should practice what it preaches.

## Decision

Replace turn-pair chunking with **whole-conversation extraction** for ChatGPT imports. The LLM reads the full conversation and extracts only settled conclusions, committed positions, and key ideas — not every assertion made along the way.

### Algorithm

**Small/medium conversations** (fits in model context window):
1. Concatenate the full conversation text
2. Send to LLM with a conclusion-focused prompt
3. One call → structured nodes

**Large conversations** (exceeds context window):
1. Send the first chunk (up to ~90% of context window, leaving room for prompt)
2. LLM extracts initial nodes (conclusions, facts, ideas)
3. Send the next chunk + **node summaries from previous steps** (compressed context)
4. LLM updates, extends, contradicts, or adds to the existing nodes
5. Repeat until conversation is exhausted

The key insight: **the extracted nodes ARE the compressed context**. 50 node summaries might be ~2K tokens regardless of how much raw conversation they represent. The graph is the compression layer between chunks. This is the project's own thesis applied to its own pipeline.

### Prompt Design

The extraction prompt should explicitly instruct:
- Extract conclusions, settled positions, committed ideas
- Ignore exploratory hypotheticals, ideas proposed then abandoned
- Ignore rhetorical questions and scaffolding discussion
- Each node should represent something the participants committed to
- If an idea was proposed early and revised later, extract the final version

### Conversation Size Distribution (188 physics theory conversations)

| Metric | Chars | Est. Tokens |
|--------|-------|-------------|
| Median | 10,941 | ~2,700 |
| Mean | 28,108 | ~7,000 |
| 90th percentile | ~120,000 | ~30,000 |
| Max | 551,087 | ~138,000 |

With a 128K token context window (Cerebras/Llama 3.1), ~95% of conversations fit in a single call. The iterative node-carry-forward method handles the rest.

## Consequences

- **Fewer, better nodes** — synthesized conclusions instead of per-turn fragments
- **Fewer false conflicts** — no more "turn 3 says X" vs "turn 7 says Y" from the same person
- **Lower cost** — 1 LLM call instead of ~10 per conversation
- **Aligned with thesis** — the pipeline practices conclusion-triggered extraction
- **Keep old mode for documents** — chunk-based extraction still makes sense for structured documents (papers, markdown files with sections) where each section is independently meaningful
