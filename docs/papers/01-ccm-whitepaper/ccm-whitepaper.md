---
title: "Cognitive Context Management: Brain-Inspired Architecture for Bounded AI Memory"
author: "Alexander Zanfir, Independent Researcher"
date: "February 2026"
abstract: |
  Large Language Models face a fundamental limitation: context windows are finite, but reasoning is not. Current approaches to this problem---summarization at capacity limits, sliding windows, or retrieval-augmented generation---treat memory as a storage optimization problem.

  I propose a different approach: drawing from cognitive science to build a bounded, self-managing context architecture. The human brain consolidates memories when insights occur, maintains unresolved problems in working memory, and reconstructs detailed memories from compressed cues. By modeling AI context management after these biological mechanisms, CCM achieves 93--98% token reduction while maintaining full retrieval capability---measured across three real conversations (58K--240K tokens, 43 effort phases total).

  This paper introduces Cognitive Context Management (CCM), a framework inspired by human memory systems. Drawing from neuroscience research on working memory, consolidation, and retrieval, I propose a four-tier architecture that: (1) separates working memory from long-term storage; (2) triggers compaction on conclusions, not capacity; (3) uses relevance-based displacement; and (4) enables cue-based retrieval. A working implementation tested end-to-end with real LLM calls validates all mechanisms in real-time across diverse topics (health advice, software debugging, travel planning). Retroactive analysis on three real conversations (58K--240K tokens) demonstrates O(1) working memory (~4K tokens constant) regardless of conversation length, compared to O(n) linear growth in traditional approaches.
fontsize: 11pt
geometry: margin=1in
colorlinks: true
linkcolor: "blue!60!black"
urlcolor: "blue!60!black"
numbersections: true
version: "0.5"
---

## 1. Introduction

### 1.1 The Problem

Modern LLMs operate within fixed context windows—typically 8K to 200K tokens. When conversations exceed this limit, systems must discard or compress information. Current approaches include:

| Approach | Mechanism | Limitation |
|----------|-----------|------------|
| Truncation | Drop oldest messages | Loses potentially relevant context |
| Sliding window | Keep only recent N tokens | Arbitrary cutoff, no semantic awareness |
| Summarization | Compress at capacity | Lossy, timing is capacity-driven not semantic |
| RAG | Retrieve relevant chunks | Requires separate index, retrieval may miss nuance |

All these approaches share a fundamental flaw: **they treat memory as a storage problem rather than a reasoning problem**. They compress when space runs out, not when understanding is achieved.

### 1.2 The Insight: Learn from the Brain

Human memory doesn't work this way. The brain has solved the memory problem elegantly over millions of years of evolution. We don't forget things because our brains are "full." We consolidate memories when:

- We reach an insight or conclusion (dopamine-mediated consolidation)
- We complete a task (Zeigarnik effect release)
- New information integrates with existing knowledge (schema assimilation)

This suggests a different approach: **borrow design principles from the brain's memory architecture**. Instead of inventing new compression algorithms, adopt patterns that evolution has already optimized:

- **Working memory limits** (~4 chunks) that force prioritization
- **Conclusion-triggered consolidation** that compacts resolved reasoning
- **Interference-based displacement** that removes irrelevant content
- **Cue-based reconstruction** that retrieves full memories from summaries

Instead of compressing when context fills, compress when reasoning resolves.

### 1.3 Contributions

This paper makes the following contributions:

1. **A neuroscience-grounded theory** of AI context management based on working memory, consolidation, and retrieval research
2. **A four-tier architecture** (Raw Log, Manifest, Open Efforts, Working Context) that separates concerns appropriately
3. **Specific mechanisms** for conclusion detection, relevance-based eviction, and cue-based retrieval
4. **A working implementation** tested end-to-end with real LLM calls across diverse topics (health advice, software debugging, travel planning), demonstrating that all mechanisms operate correctly in real-time
5. **Empirical validation** across three real conversations (58K-240K tokens) showing 93-98% token savings and O(1) working memory

---

## 2. Neuroscience Foundations

The CCM framework draws design inspiration from neuroscience research on memory consolidation, working memory capacity, and retrieval mechanisms. The mappings below are structural analogies — cognitively inspired design principles, not claims of mechanistic equivalence with biological systems.

### 2.1 Working Memory Capacity

Cowan's research establishes that working memory is limited to approximately **4 independent chunks** [1]. This isn't arbitrary—it reflects the bandwidth of the attention system implemented in prefrontal cortex.

**Design implication**: Working context should have a hard limit (~4 active topics), not unlimited growth.

### 2.2 Consolidation Triggers

Memory consolidation is **not purely time-based**. Research identifies several consolidation triggers:

| Trigger | Mechanism | Source |
|---------|-----------|--------|
| Insight/"Aha" moments | Dopamine surge tags memory as important | Kizilirmak et al. [2] |
| Emotional significance | Amygdala modulates hippocampal encoding | Dolcos et al. [3] |
| Schema congruence | New info matching existing knowledge consolidates within 48 hours | Tse et al. [4] |
| Prediction error | Reward prediction errors enhance encoding | Rouhani et al. [5] |

**Design implication**: Compaction should trigger at conclusions/insights, not capacity limits.

### 2.3 The Zeigarnik Effect

Bluma Zeigarnik's research demonstrates that **incomplete tasks maintain elevated cognitive accessibility** [6]. The brain allocates working memory resources to unresolved items. Completion is a *release* signal.

**Design implication**: Unresolved topics should remain in working context. Resolution should trigger compaction and release.

### 2.4 Interference vs. Time Decay

Research increasingly shows that **interference, not time, is the primary cause of working memory decay** [7]. Similar content competes during retrieval. New topics push out old ones.

**Design implication**: Don't age-out content automatically. Displace by relevance, not timestamp.

### 2.5 Retrieval as Reconstruction

Memory retrieval is **pattern completion**, not file retrieval [8]. The hippocampus reconstructs memories from partial cues. Effective cues match encoding conditions.

**Design implication**: Store good retrieval cues (summaries), not just compressed content. The summary's job is to trigger reconstruction of the full memory.

### 2.6 Schema Integration

When new information matches existing knowledge (schema congruence), consolidation happens **10x faster** [4]. The medial prefrontal cortex detects congruency and expedites neocortical storage.

**Design implication**: Conclusions that connect to existing knowledge can compact more aggressively than truly novel conclusions.

---

## 3. The Four-Tier Architecture

Based on these neuroscience findings, I propose a four-tier context architecture:

```
+---------------------------------------------------------------+
|  1. RAW LOG                                                    |
|     Biological analog: Episodic memory archive                 |
|     --------------------------------------------------------- |
|     - Full verbatim record of all exchanges                    |
|     - Append-only, never modified                              |
|     - Never loaded into context directly                       |
|     - Source for retrieval/reconstruction when needed          |
+---------------------------------------------------------------+
|  2. MANIFEST                                                   |
|     Biological analog: Semantic memory / Long-term index       |
|     --------------------------------------------------------- |
|     - Segment summaries (both concluded and open)              |
|     - Artifact references and links                            |
|     - Searchable for "what did we discuss?"                    |
|     - Schema-like abstracted knowledge                         |
+---------------------------------------------------------------+
|  3. OPEN EFFORTS                                               |
|     Biological analog: Zeigarnik buffer / Pending tasks        |
|     --------------------------------------------------------- |
|     - All unresolved topics/threads                            |
|     - Maintains elevated accessibility (like uncompleted tasks)|
|     - NOT in active context, but quick to retrieve             |
|     - Items leave when concluded (resolution = release)        |
+---------------------------------------------------------------+
|  4. WORKING CONTEXT                                            |
|     Biological analog: Working memory (~4 chunks)              |
|     --------------------------------------------------------- |
|     - Currently RELEVANT subset of open efforts                |
|     - Hard capacity limit (3-5 active topics)                  |
|     - What actually gets passed to the model each turn         |
|     - Interference-based displacement                          |
|     - Non-effort content (greetings, one-off exchanges)        |
|       resides in ambient window, displaced by recency          |
+---------------------------------------------------------------+
```

### 3.1 Information Flow

```
                    +--------------+
                    |  NEW INPUT   |
                    +------+-------+
                           |
                           v
                    +--------------+
         +---------+   WORKING    +<--------+
         |         |   CONTEXT    |         |
         |         +------+-------+         |
         |                |                 |
    interference     conclusion        relevance
    (pushed out)     (resolved)      (pulled in)
         |                |                 |
         v                v                 |
   +----------+    +----------+             |
   |   OPEN   |    | MANIFEST |             |
   | EFFORTS  +----+(summary) |             |
   +----+-----+    +----+-----+             |
        |               |                   |
        |               v                   |
        |         +----------+              |
        |         | RAW LOG  |              |
        |         |(verbatim)|              |
        |         +----------+              |
        +-----------------------------------+
              (becomes relevant again)
```

### 3.2 Lifecycle States

| State | Location | Trigger to Enter | Trigger to Exit |
|-------|----------|------------------|-----------------|
| Active | Working Context | Relevance detected | Interference or conclusion |
| Pending | Open Efforts | Pushed from working, or new unresolved topic | Pulled to working, or concluded |
| Concluded | Manifest only | Resolution/insight detected | N/A (permanent) |
| Archived | Raw Log | Every exchange | N/A (permanent) |

---

## 4. Core Mechanisms

### 4.1 Conclusion Detection

Conclusions trigger compaction. The following detection patterns are identified:

| Pattern | Example | Confidence |
|---------|---------|------------|
| Explicit declaration | "I conclude X", "The answer is Y" | High |
| Resolution pattern | Problem stated → solution verified → "That fixed it" | High |
| Negation confirmed | "Option A doesn't work because Z" | Medium-High |
| User confirmation | "Yes, that's the issue", "Perfect" | High |
| Evidence convergence | Multiple reasoning paths reach same answer | High |
| Task completion | "Done", "Implemented", "Merged" | High |

The system should:
1. Recognize these patterns in real-time
2. Offer to compact (or auto-compact for high-confidence detections)
3. Create a summary that serves as a retrieval cue
4. Move the topic from Open Efforts to Manifest
5. Release working context resources

### 4.2 Relevance Scoring

When selecting what enters Working Context from Open Efforts:

| Signal | Weight | Rationale |
|--------|--------|-----------|
| Explicitly mentioned this turn | Highest | Direct relevance |
| Semantically similar to current input | High | Schema activation / pattern matching |
| Recently in working context | Medium | Recency = still "warm" |
| User-flagged important | Medium | Amygdala modulation analog |
| Connected to current topic in manifest | Medium | Network proximity |
| Long time since touched | Low | Interference has weakened access |
| No connections to current topic | Lowest | Leave in open efforts |

### 4.3 Interference-Based Displacement

When Working Context is at capacity and a new relevant topic arrives:

1. Score all current items by relevance to incoming topic
2. Identify lowest-relevance item
3. Push that item back to Open Efforts (not lost, just not active)
4. Pull in the new relevant topic

This is inspired by the brain's interference-based displacement: new content pushes out less-relevant content, not oldest content.

### 4.4 Cue-Based Retrieval

When a topic is referenced that exists in Manifest but not Working Context:

1. Summary acts as retrieval cue
2. System can choose to:
   - Answer from summary alone (if sufficient)
   - Expand specific segments from Raw Log
   - Pull topic back into Working Context for extended discussion

This is analogous to hippocampal pattern completion: partial cues (summaries) enable reconstruction of full memories (raw dialogue).

---

## 5. Core Thesis: Conclusion-Triggered Compaction

**Current systems compact based on capacity. CCM compacts based on understanding.**

When a thread of reasoning reaches resolution — a bug is fixed, a decision is made, a question is answered — that's when compaction should occur. The conclusion is extracted as a summary, linked to its raw source, and the verbose exploration is released from active context.

The inspiration from neuroscience: insight moments trigger dopamine release, which tags memories for consolidation (Section 2.2). The "aha" is the compaction signal. Incomplete tasks persist in working memory until resolved (Section 2.3, Zeigarnik effect). The result is a system where:

- **Open efforts stay in working context** — unresolved topics maintain elevated accessibility
- **Concluded efforts compact to summaries** — resolved topics release working memory resources
- **Summaries serve as retrieval cues** — not just compressed content, but triggers for full reconstruction (Section 2.5)
- **Working memory stays bounded** — old summaries evict based on relevance, not time (Section 2.4)

This single principle — compact on conclusion, not capacity — produces the O(1) working memory behavior demonstrated in Section 6.4. CCM's compaction summaries are generated at semantically meaningful boundaries (when understanding is achieved), producing higher-quality summaries than capacity-triggered systems that must compress mid-thought.

CCM provides the memory management layer for a broader vision of persistent AI knowledge. Directions such as cross-session knowledge networks, abstraction hierarchies, and emergent confidence from network topology are explored in companion work.

---

## 6. Implementation Architecture

### 6.1 File Structure

```
{session_dir}/
+-- raw.jsonl              # Tier 1: Full verbatim log (append-only)
+-- manifest.yaml          # Tier 2: Effort index (open + concluded summaries)
+-- expanded.json          # Tier 3-4: Working context state
|                          #   - expanded efforts (full context loaded)
|                          #   - last_referenced_turn (for decay/eviction)
|                          #   - summary_last_referenced_turn (for summary eviction)
+-- session_state.json     # Turn counter, timestamps
+-- efforts/
    +-- {effort-id}.jsonl  # Per-effort raw conversation log
```

### 6.2 Data Schemas

**Raw Log Entry (JSONL)** — append-only, never modified
```json
{"role": "user", "content": "Help me debug the auth bug"}
{"role": "assistant", "content": "I'll look into that..."}
```

**Manifest** — effort index with lifecycle states
```yaml
efforts:
  - id: auth-bug
    status: concluded
    summary: "Fixed 401 errors by adding automatic token refresh on expiry."
    raw_file: efforts/auth-bug.jsonl
    active: false

  - id: perf-optimization
    status: open
    active: true
    raw_file: efforts/perf-optimization.jsonl
```

**Expanded State** — tracks what's in working context and reference history
```json
{
  "expanded": ["auth-bug"],
  "expanded_at": {"auth-bug": "2024-01-17T11:00:00"},
  "last_referenced_turn": {"auth-bug": 42},
  "summary_last_referenced_turn": {"auth-bug": 20, "perf-fix": 15}
}
```

Working context is built dynamically each turn from these files — not stored as a separate file. The orchestrator assembles: system prompt + active effort summaries (filtered by eviction) + expanded effort raw logs + ambient window (last N messages from raw.jsonl).

### 6.3 Token Budget Analysis

**Theoretical model:**

```
Traditional:  min(total_tokens, 200K)    — linear growth, hard cap, lossy above limit

CCM:          active_summaries + ambient_window + system_prompt
            = (2-3 × 202 avg) + (10 exchanges × 2 × 100) + 1,500
            ≈ 4,000 tokens                — O(1), constant regardless of conversation length
```

**Measured across three real conversations (58K-240K tokens, 43 effort phases):**

| Component | Conv A (138K) | Conv B (240K) | Conv C (58K) |
|-----------|--------------|--------------|-------------|
| Active summaries (2-3 recent) | 576 | 602 | 494 |
| Ambient window (last 10 exchanges) | ~2,000 | ~2,000 | ~2,000 |
| System prompt + tools | ~1,500 | ~1,500 | ~1,500 |
| **CCM working context** | **4,076** | **4,102** | **3,994** |
| **Traditional context** | **138,219** | **200,000*** | **57,630** |
| **Savings** | **97.1%** | **97.9%** | **93.1%** |

*Conv B exceeded 200K hard cap — traditional management loses all excess content.

The savings are O(1) vs O(n): CCM working memory stays flat at ~4K tokens regardless of conversation length, while traditional context grows linearly until hitting the 200K hard cap. The 2-3 active summaries shown above are not a hardcoded limit — they emerge from a 20-turn eviction threshold (concluded effort summaries not referenced in the last 20 user messages are evicted from working memory). The number of active summaries at any point depends on how frequently topics change in real conversation. The eviction threshold and ambient window are configurable parameters — applications with larger context budgets can retain more active summaries, while resource-constrained environments can tighten bounds further. Note: this analysis measures working context size only. CCM introduces per-turn overhead for conclusion detection (LLM tool-calling) and per-conclusion overhead for summary generation. These costs are not reflected in the token budget but are a practical consideration for deployment. However, CCM's auxiliary operations — summary generation, relevance scoring, and potentially conclusion detection — are independent tasks that do not require the primary conversation model. In practice, summaries can be generated by lightweight or local models (the case study uses DeepSeek-chat), and relevance scoring is purely programmatic. This multi-model decomposition means CCM's overhead costs can be significantly lower than the per-token cost of the primary model.

### 6.4 Case Study: Retroactive CCM Analysis

I retroactively applied CCM rules to three real Claude Code conversations, covering different conversation types:

| Conversation | Total Tokens | User Messages | Effort Phases | Domain |
|---|---|---|---|---|
| A: Multi-topic development | 138K | 188 | 11 | Pipeline dev, testing, architecture |
| B: Deep single-topic | 240K | 429 | 17 | TDD pipeline iteration |
| C: Brainstorm/architecture | 58K | 190 | 15 | Project design, tech decisions |

For each conversation, I identified effort phase boundaries by analyzing topic transitions in user messages, then generated LLM summaries for each phase using the same `summarize_effort` function CCM uses in production (DeepSeek-chat).

**Compaction results across all three conversations:**

| Metric | Conv A (138K) | Conv B (240K) | Conv C (58K) |
|--------|--------------|--------------|-------------|
| Effort phases | 11 | 17 | 15 |
| Total summary tokens | 2,218 | 3,081 | 2,600 |
| Avg summary size | 202 tok | 181 tok | 173 tok |
| Raw compaction savings | 98.4% | 98.7% | 95.5% |
| CCM working memory (end) | 4,076 tok | 4,102 tok | 3,994 tok |
| Traditional working memory (end) | 138,219 tok | 200,000 tok* | 57,630 tok |
| **Overall savings** | **97.1%** | **97.9%** | **93.1%** |

*Conv B exceeded the 200K context window cap — traditional management would suffer permanent data loss. CCM stays at 4.1K.

**Growth curve comparison (Conv B — worst case for traditional):**

| Turn | Traditional | CCM | Ratio |
|------|------------|-----|-------|
| 13 | 6,283 | 3,668 | 2x |
| 63 | 27,292 | 3,706 | 7x |
| 168 | 77,369 | 3,919 | 20x |
| 300 | 151,747 | 3,655 | 42x |
| 370 | 199,730 | 3,678 | 54x |
| 429 | 200,000* | 3,908 | 51x |

*Hit 200K hard cap at turn ~370. All subsequent content lost in traditional mode.

**Key finding: CCM working memory is stable at ~4K tokens across all three conversations**, regardless of total conversation size (58K to 240K), number of effort phases (11 to 17), or conversation type (multi-topic, deep single-topic, brainstorm). The variation across conversations is <3% (3,994-4,102 tokens).

Average summary sizes are also stable: 173-202 tokens across conversations, confirming that summary compression is consistent regardless of effort size (1K-51K raw tokens per effort).

**Qualitative difference:** Conversation A experienced 10 lossy compaction events under traditional management. Conversation B exceeded the 200K context limit, losing all content beyond that cap. Under CCM, all effort raw logs across all three conversations are preserved on disk and retrievable via `search_efforts` → `expand_effort`, with zero storage loss (though retrieval quality depends on summary cue accuracy).

### 6.5 Live System Validation

The retroactive analysis above demonstrates CCM's storage efficiency, but it was applied post-hoc to completed conversations. To validate that the mechanisms work in real-time — that an LLM can correctly detect effort boundaries, trigger compaction, manage decay, and retrieve evicted summaries from natural language alone — I built and tested a live implementation.

The system was tested end-to-end with real LLM calls (DeepSeek-chat) across diverse topic domains:

**Effort lifecycle (real-time detection):** The LLM correctly opens efforts from natural language cues ("Can you help me with a back pain issue", "Let's debug the auth bug — users get 401 errors after an hour") and correctly ignores ambient messages ("Hey, how's it going?", "What's the capital of France?"). Sub-topics stay within the parent effort — reporting arm pain during a back pain discussion does not spawn a second effort. When the user signals resolution ("Bug is fixed, we're done"), the LLM calls the close tool, generates a summary, and releases working memory.

**Salience decay (automatic eviction):** After expanding a concluded effort's raw log into working context, unrelated conversation causes automatic collapse. In testing, a cache bug investigation expanded into context was auto-collapsed after several unrelated factual questions, returning working memory to its bounded baseline. Users can re-expand at any time — the raw log is preserved, only the working context allocation changes.

**Bounded context under load:** With 15 ambient messages (exceeding the 10-exchange window), only the most recent exchanges appear in working context while all 30 raw log entries (15 turns x 2 messages) are preserved on disk. The LLM continues to function correctly with the windowed context.

**Evicted effort retrieval:** Concluded effort summaries evicted from working memory (not referenced in 20+ turns) are discoverable via the `search_efforts` tool. In testing, an auth-bug fix evicted from working memory was retrieved by asking "What was the fix for the auth bug we worked on?" — the LLM called `search_efforts`, found the match, and reported the fix. The full retrieval path (search → expand) was also validated: after searching, users can request expansion to reload the complete raw conversation.

**Reference-based counter reset:** A fishing trip planning effort set to evict at its threshold was saved by a casual mention ("remember that fishing trip we planned?"), which reset the eviction counter. The effort remained in working memory for another full threshold window, confirming that the interference-based model responds to genuine topical relevance rather than rigid time-based expiry.

These tests confirm that CCM's mechanisms operate correctly in real-time with natural language input, not just in controlled retroactive analysis. The complete test suite (unit, integration, and end-to-end) comprises ~180 tests covering all four slices of the architecture.

---

## 7. Comparison to Existing Approaches

| Feature | Truncation | Sliding Window | Summarization | RAG | CCM |
|---------|------------|----------------|---------------|-----|-----|
| Semantic awareness | No | No | Partial | Partial | Yes |
| Full retrieval | No | No | No | Partial | Yes |
| Conclusion-driven compaction | No | No | No | No | Yes |
| Bounded working memory (O(1)) | No | No | No | No | Yes |
| Relevance-based eviction | No | Partial | No | No | Yes |
| Zero storage loss | No | No | No | Yes | Yes |
| No external index required | Yes | Yes | Yes | No | Yes |

**Key differentiator**: CCM's primary contribution is not the invention of memory layering — modern agent frameworks already implement episodic logs, summary layers, and retrieval policies. Rather, CCM introduces **explicit lifecycle management** (open → concluded → evicted) as the organizing principle, with compaction triggered by semantic resolution rather than capacity limits. This produces naturally bounded working memory without requiring external vector infrastructure. Note that CCM and RAG are complementary: embedding-based retrieval could replace CCM's keyword matching for improved relevance scoring.

---

## 8. Limitations and Future Work

### 8.1 Current Limitations

- **Effort boundary detection**: The implementation uses LLM tool-calling to detect effort open/close events. Accuracy depends on the underlying model's ability to recognize topic transitions. Missed boundaries degrade compaction quality. This also introduces per-turn overhead: each turn requires the LLM to evaluate whether to call effort management tools, adding latency and cost not reflected in the token budget analysis.
- **Summary quality**: Summaries are generated by a single LLM call at conclusion time. A poor summary produces a poor retrieval cue, making the associated raw log effectively unreachable despite being preserved on disk. I have not yet evaluated summary quality, retrieval accuracy, or downstream reasoning correctness systematically — the case study measures storage efficiency only, not reasoning performance retention.
- **Single-session scope**: The current implementation operates within a single conversation session. Efforts do not persist across sessions.
- **Validation scale**: Retroactive analysis covers three development conversations (58K-240K tokens) by one author. Live testing spans diverse topics (health advice, travel planning, software debugging) but uses controlled scenarios, not organic multi-user conversations. Validation across multiple users, longer time horizons, and varied interaction styles is needed to confirm generalizability.
- **Adversarial interleaving**: The O(1) bound assumes a bounded number of concurrently relevant efforts. If a user rapidly alternates references across many past efforts, the system would thrash between expand/evict cycles. Amortized analysis under adversarial access patterns has not been performed.
- **Large atomic inputs**: When a single active effort contains content exceeding the working memory budget (e.g., a large file being refactored), CCM's bounded context cannot accommodate it without chunking strategies not yet addressed.

### 8.2 Designed Extensions (Out of Scope)

The limitations above are not open research problems — they have designed solutions at various stages of implementation, but fall outside the scope of this paper. The CCM architecture presented here is the memory management foundation for a broader system described in companion work:

- **Effort reopening**: Concluded efforts can be reopened and extended, not just viewed. When a user returns to a past topic, the system searches concluded efforts and offers to reopen the match or start fresh. The original raw log is preserved and new messages append to it; re-conclusion updates the summary. This completes the non-linear effort lifecycle (open → conclude → reopen → re-conclude).

- **Cross-session persistence**: Efforts and their summaries persist across conversation sessions, enabling long-running projects that span days or weeks. The manifest and raw log architecture already supports this — session-linking and manifest merging are the remaining implementation steps.

- **Semantic relevance scoring**: Embedding-based retrieval replaces CCM's current keyword matching for eviction decisions and effort search, keeping conceptually related efforts warm even without explicit keyword overlap. CCM's architecture is retrieval-method-agnostic — the eviction and search interfaces accept any scoring function.

- **Knowledge graph**: Cross-session effort connections form a growing graph where conclusions link through support, contradiction, and generalization edges. Confidence emerges from network topology (independent convergence, failed contradictions) rather than explicit assignment. This extends CCM from memory management into persistent knowledge accumulation.

These extensions are documented in the project's implementation roadmap and thesis documents, available in the project repository.

---

## 9. Conclusion

Current approaches to AI memory treat context limits as a storage problem to be optimized. By drawing from neuroscience research on human memory, I propose a fundamentally different approach: **Cognitive Context Management**.

The four-tier architecture — Raw Log, Manifest, Open Efforts, and Working Context — is inspired by the brain's separation of episodic archive, semantic index, pending tasks, and active working memory. CCM's conclusion-triggered compaction borrows from insight-driven consolidation. Its relevance-based eviction borrows from interference-driven forgetting. These are structural analogies, not mechanistic equivalences — but the design principles they produce are empirically effective.

A working implementation tested with real LLM calls validates that all mechanisms — effort detection, conclusion-triggered compaction, salience decay, bounded eviction, and cue-based retrieval — function correctly in real-time from natural language input. Case studies on three real conversations (58K-240K tokens, 43 effort phases total) demonstrate:
- **93-98% token savings** — working memory of ~4K tokens vs 58K-200K traditional
- **O(1) bounded growth** — working memory stays flat at ~4K across all conversations regardless of length, type, or effort count (<3% variation between conversations)
- **Zero storage loss** — all raw conversation data preserved on disk, retrievable via search and expansion (retrieval quality depends on summary cue accuracy)
- **Consistent summary sizes** — 173-202 token averages across conversations, stable regardless of per-effort raw size (1K-51K tokens)

CCM provides the memory management foundation for persistent AI systems. By compacting when understanding is achieved rather than when space runs out, and by keeping unresolved topics accessible until completed, this takes a step toward AI systems that remember more like humans do — not by storing everything, but by knowing what matters.

---

## References

[1] Cowan, N. (2010). The magical mystery four: How is working memory capacity limited, and why? *Current Directions in Psychological Science*, 19(1), 51-57.

[2] Kizilirmak, J. M., et al. (2016). Learning by insight-like sudden comprehension as a potential strategy to improve memory encoding. *Frontiers in Psychology*, 7, 1579.

[3] Dolcos, F., LaBar, K. S., & Cabeza, R. (2004). Interaction between the amygdala and the medial temporal lobe memory system predicts better memory for emotional events. *Neuron*, 42(5), 855-863.

[4] Tse, D., et al. (2007). Schemas and memory consolidation. *Science*, 316(5821), 76-82.

[5] Rouhani, N., Norman, K. A., & Niv, Y. (2018). Dissociable effects of surprising rewards on learning and memory. *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 44(9), 1430.

[6] Zeigarnik, B. (1927). On finished and unfinished tasks. *Psychologische Forschung*, 9, 1-85.

[7] Oberauer, K., & Lewandowsky, S. (2008). Forgetting in immediate serial recall: Decay, temporal distinctiveness, or interference? *Psychological Review*, 115(3), 544.

[8] Staresina, B. P., et al. (2019). Hippocampal pattern completion is linked to gamma power increases and alpha power decreases during recollection. *eLife*, 8, e40562.

---

## Appendix A: Mechanism-to-Neuroscience Mapping

| Brain Mechanism | Function | CCM Analog | Implemented |
|-----------------|----------|------------|-------------|
| Working memory (~4 items) | Active processing bottleneck | Bounded working context (~3 active summaries) | Yes |
| Synaptic tagging & capture | Selective consolidation | Conclusion-triggered compaction | Yes |
| Sharp-wave ripple replay | Transfer to long-term | Effort summary written to manifest | Yes |
| Pattern completion | Cue-triggered reconstruction | Summary → search → expand retrieval path | Yes |
| Interference | Primary forgetting mechanism | Relevance-based summary eviction | Yes |
| Zeigarnik effect | Incomplete tasks persist | Open efforts stay in working context | Yes |
| Hippocampal binding | Temporary coherent trace | Per-effort raw log binding | Yes |
| Schema integration | Rapid learning with prior knowledge | Keyword-based reference detection | Partial |
| Dopamine/reward signaling | Marks significant events | LLM-detected conclusion patterns | Partial |

---

## Appendix B: Glossary

**Artifact**: A markdown file containing an extracted conclusion with metadata (status, links, tags).

**Compaction**: The process of summarizing a resolved thread and releasing it from working context.

**Conclusion**: A resolved piece of reasoning—a decision made, problem solved, or question answered.

**Effort**: A unit of focused work that is either open (unresolved) or concluded (resolved).

**Interference**: The displacement of less-relevant content by more-relevant content in working context.

**Manifest**: The index of all segment summaries across a conversation session.

**Open Effort**: An unresolved topic that maintains elevated accessibility until concluded.

**Raw Log**: The full verbatim record of all exchanges, preserved for retrieval.

**Segment**: A topically coherent portion of conversation, tracked in the manifest.

**Working Context**: The currently active, relevant subset of information passed to the model.

---

*Implementation source: [github.com/knowledge-network](https://github.com/knowledge-network) — Scripts and raw data for reproducing the empirical results are in `scripts/` and `docs/research/`.*
