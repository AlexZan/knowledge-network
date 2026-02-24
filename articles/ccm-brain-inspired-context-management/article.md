# Your LLM Forgets Everything After 200K Tokens. The Brain Doesn't. Here's What I Borrowed.

Every LLM conversation has the same failure mode. It starts smart, stays sharp for a while, then hits a wall. The context window fills up. Older messages get truncated. Summaries get lossy. And suddenly your AI assistant has forgotten the first half of the conversation you've been building on for the last hour.

This is the context window problem, and every approach I've seen treats it the same way: as a storage optimization problem. Compress more. Retrieve better. Slide the window. Make the window bigger.

I took a different approach. I asked: how does the brain handle this? And it turns out the brain solved this problem millions of years ago.

## The Insight That Changed Everything

Human working memory holds about 4 items. Not 4,000. Not 200,000. Four.

Yet we navigate complex multi-topic conversations effortlessly. We debug code while remembering a meeting from this morning while planning dinner tonight. How?

The brain doesn't keep everything in active memory. It compresses — but not when memory is "full." It compresses **when understanding is achieved**. When you solve a bug, that 45-minute investigation collapses into "oh, it was a race condition in the cache layer." The verbose exploration is gone from working memory, but the conclusion persists. And if someone asks you about it tomorrow, you can reconstruct the details from that compressed cue.

Three specific neuroscience findings shaped the design:

**Conclusion-triggered consolidation.** Insight moments trigger dopamine release, which tags memories for long-term storage. The "aha" is the compaction signal — not a timer, not a capacity limit.

**The Zeigarnik effect.** Incomplete tasks occupy working memory until resolved. Your brain literally won't let go of an unfinished problem. But the moment it's resolved? Released.

**Interference-based forgetting.** You don't forget things because they're old. You forget them because new, more relevant information pushes them out. Time-based decay is a myth — relevance-based displacement is how it actually works.

## The Architecture: Four Tiers, Like the Brain

I built Cognitive Context Management (CCM) as a four-tier system that mirrors these mechanisms:

**Tier 1 — Raw Log** (episodic memory). Every message ever exchanged. Append-only, never deleted, never loaded into context directly. This is your full history, preserved forever.

**Tier 2 — Manifest** (semantic memory). An index of all "efforts" — topics you've worked on. Each concluded effort has a summary that acts as a retrieval cue. Think of it as your brain's index of "things I know about."

**Tier 3 — Open Efforts** (Zeigarnik buffer). Unresolved topics. These stay accessible — like that bug you haven't fixed yet that keeps nagging at you. They don't get compressed because they're not done.

**Tier 4 — Working Context** (working memory). The bounded set of information that actually gets passed to the model each turn. Hard limit. About 4K tokens. Everything else is in the tiers below, retrievable but not active.

## How It Works in Practice

Say you're chatting with an AI assistant. You start debugging an auth bug. CCM opens an "effort" — the full conversation about this bug lives in its own log. You work through it, find the fix, say "that solved it."

That conclusion triggers compaction. The entire investigation — maybe 5,000 tokens of back-and-forth — collapses to a ~200-token summary: "Fixed 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor."

The raw conversation is preserved on disk. But working context just freed up 4,800 tokens.

Now you switch to planning a fishing trip. Then come back to discussing a performance issue. Then someone asks "what was that auth fix again?" CCM searches the manifest, finds the summary, and can expand the full raw log back into context on demand.

The key: working memory stays at ~4K tokens regardless of how long the conversation runs.

## The Numbers

I tested this on three real conversations ranging from 58K to 240K tokens:

**Multi-topic dev (138K tokens)**
Traditional working memory: 138,219 → CCM: 4,076 → **97.1% reduction**

**Deep single-topic (240K tokens)**
Traditional working memory: 200,000* → CCM: 4,102 → **97.9% reduction**

**Brainstorm session (58K tokens)**
Traditional working memory: 57,630 → CCM: 3,994 → **93.1% reduction**

*Hit the 200K context cap — all content beyond that is permanently lost in traditional mode. CCM stays at 4.1K.

The working memory stays flat at ~4K tokens across all three conversations. Less than 3% variation. That's O(1) — constant — versus O(n) linear growth.

And those "2-3 active summaries" in working memory at any given time? That's not a hardcoded limit. It emerges naturally from a 20-turn eviction threshold interacting with how humans actually switch topics. The architecture produces brain-like bounds without being told to.

## It Actually Works Live

This isn't just a retroactive analysis. I built and tested the system end-to-end with real LLM calls. The AI correctly:

- Opens an effort when you say "help me with my back pain" but ignores "hey, how's it going?"
- Keeps sub-topics in the parent effort — reporting arm pain during a back pain discussion doesn't spawn a new effort
- Auto-collapses expanded context after you've moved on to unrelated topics
- Finds evicted summaries via search when you ask about something from 20+ turns ago
- Resets eviction counters when you casually mention a past topic

The full test suite covers all of this — unit tests, integration tests, and end-to-end tests with real LLM calls across health advice, software debugging, and travel planning.

## What This Means for the Future of AI Memory

Current LLMs have a dirty secret: they're stateless. Every turn, the entire context window is assembled from scratch. There's no real memory — just increasingly desperate attempts to fit everything into a finite window.

CCM suggests a different path. Instead of making windows bigger (which is expensive and still finite), make the content smarter. Compress when understanding is achieved. Keep unresolved problems active. Displace by relevance, not by time.

The auxiliary operations — summary generation, relevance scoring — don't even need the primary model. In practice, I use DeepSeek-chat for summaries while the main conversation runs on whatever model you want. The overhead is minimal.

And this is just the memory management layer. The broader vision includes cross-session persistence (efforts that survive between conversations), semantic search (embeddings instead of keyword matching), and eventually a knowledge graph where conclusions link across sessions and confidence emerges from network topology.

## Try It Yourself

The implementation is open source. The paper has all the details.

- **Paper:** [Zenodo (DOI)](https://zenodo.org/records/18752096)
- **Code:** [GitHub](https://github.com/AlexZan/knowledge-network)
- **Tests:** 101 unit tests + end-to-end with real LLM calls

The core insight is simple: stop treating AI memory as a storage problem. Treat it as a reasoning problem. Compress when you understand, not when you run out of space.

Your brain figured this out a long time ago. It's time our AI systems caught up.

---

*This article represents the original ideas and writing of Alexander Zanfir, edited and refined through an agentic editorial process.*
