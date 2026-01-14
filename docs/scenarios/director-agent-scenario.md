# Scenario: Director Agent with Effort-Scoped Context

A day in the life of a 24/7 director agent using the effort-scoped context model.

---

## The Setup

The director agent runs continuously. Its context never hits the limit because:
1. Each spawned worker agent is **one effort = one chat**
2. When a worker completes, the effort compacts to an artifact
3. Director's context contains only: current orchestration state + compacted effort summaries
4. Raw details available via RAG if needed

---

## Morning: A New Feature Arrives

I'm the director agent. I've been running for 3 days straight. My context is at 45% capacity - plenty of room.

A new GitHub issue lands in the kanban:
```
Issue #247: Add resource trading between players
Label: ready
```

I pick it up. This is a new effort starting. I update my context:
```
[effort:open] Issue #247 - Resource trading feature
  Status: Starting pipeline
  Current stage: story
```

### Spawning Story Agent

I spawn a story-agent. This creates a **new chat** for the story effort:

```
SPAWN: story-agent
EFFORT: "Write user stories for Issue #247"
WEIGHT: medium (standard feature, not critical)
CONTEXT: Issue description + relevant artifacts from my memory
```

The story-agent runs in its own context window. I don't see the back-and-forth - I just wait for completion.

20 minutes later, the story-agent returns:
```
[effort:resolved] Write stories for Issue #247
  => Created docs/stories/resource-trading.md
  => 4 user stories, 12 acceptance criteria
  => PO approval needed before continuing
[Tokens: 8,420 raw → 156 compacted | Savings: 98%]
```

The full conversation is stored, but I only receive the compacted artifact. My context grows by ~156 tokens, not 8,420.

I update my orchestration state and pause - waiting for PO label.

---

## Midday: Parallel Efforts

The PO approved the stories. I continue the pipeline.

But wait - two more items appeared in kanban:
```
Issue #248: Fix logout bug (label: bug, priority: high)
Issue #249: Update docs for API changes (label: docs)
```

I can handle multiple efforts. Each spawns its own agent with its own context:

```
PARALLEL SPAWN:
1. architect-agent for #247 (medium weight)
2. debugger-agent for #248 (high weight - critical bug)
3. docs-agent for #249 (low weight - just docs)
```

Each agent is **one effort = one chat**. They run concurrently. I track:
```
[effort:open] #247 architecture design - architect-agent running
[effort:open] #248 logout bug investigation - debugger-agent running
[effort:open] #249 API docs update - docs-agent running
```

The high-weight bug gets maximum context budget. The docs update runs lean.

---

## Early Afternoon: Worker Reports Back

The debugger-agent finishes first (high priority = more resources):
```
[effort:resolved] Investigate logout bug #248
  => Root cause: Session token not cleared on server
  => Fix: Add server-side session invalidation
  => Tests needed: Yes, spawning test-architect recommended
[Tokens: 12,891 raw → 203 compacted | Savings: 98%]
```

I immediately spawn test-architect for the fix:
```
SPAWN: test-architect
EFFORT: "Write failing tests for logout bug fix"
WEIGHT: high (inherited from parent effort)
CONTEXT: Debugger findings artifact + relevant code artifacts
```

Meanwhile, architect-agent returns:
```
[effort:resolved] Design architecture for #247
  => Integration points: InventorySystem, NetworkManager, UI
  => New systems: TradingSystem, TradeUI
  => Risk: Need to handle mid-trade disconnection
[Tokens: 15,234 raw → 287 compacted | Savings: 98%]
```

My context is now at 52%. Still healthy. I spawn test-architect for #247.

---

## Late Afternoon: Child Efforts

The test-architect for #247 hits a snag. The user stories have a gap - they don't specify what happens if a player disconnects mid-trade.

This is a **child effort** - it contributes to the parent:
```
SPAWN: story-agent
EFFORT: "Clarify disconnection handling for #247" (CHILD of #247)
WEIGHT: medium (inherited)
CONTEXT: Parent effort summary + specific gap identified
```

The child effort resolves:
```
[effort:resolved] Clarify disconnection handling
  => Added acceptance criterion: "Trade cancelled if either player disconnects"
  => Added acceptance criterion: "Resources returned to original owners"
  => Updated docs/stories/resource-trading.md
[Tokens: 3,200 raw → 89 compacted | Savings: 97%]
```

This artifact **rolls up** to the parent effort. My tracking:
```
[effort:open] #247 Resource trading
  ├─ [resolved] Story writing → 4 stories created
  ├─ [resolved] Architecture → TradingSystem designed
  ├─ [resolved] Story clarification (child) → disconnection handled
  └─ [in-progress] Test writing → test-architect running
```

---

## Evening: Alignment Gate

Test-architect finishes for #247. Time for alignment check.

I spawn alignment-agent:
```
SPAWN: alignment-agent
EFFORT: "Verify test alignment for #247"
WEIGHT: high (gate - must be thorough)
CONTEXT: All #247 effort artifacts + test files + story files
```

The alignment-agent uses multi-model verification (Opus + Gemini). Returns:
```
[effort:resolved] Alignment check for #247
  => Score: 78% (PASS with notes)
  => Gap: No test for UI feedback during trade
  => Gap: Reconnection scenario not tested
  => Recommendation: Add 2 tests before dev
[Tokens: 22,450 raw → 312 compacted | Savings: 99%]
```

I spawn test-architect again for the gaps (child effort), then proceed.

---

## Night: Context Maintenance

It's 2am. My context is at 71% - approaching the compaction zone.

I review my open efforts:
```
[effort:open] #247 - dev-agent running (high weight)
[effort:open] #248 - dev-agent running (high weight)
[effort:open] #249 - completed, awaiting merge
```

#249 is done. I can fully compact it:
```
[effort:closed] #249 API docs update
  => Updated 3 doc files
  => PR #891 merged
  Summary archived to chat log
```

My context drops to 68%. Back in the safe zone.

---

## The Next Morning: Continuity

I've been running for 4 days. A human checks in:

**Human**: "What's the status of the trading feature?"

I don't need to search or reconstruct. My context has the compacted effort tree:
```
#247 Resource Trading
├─ Stories: 4 written, PO approved, 1 clarification added
├─ Architecture: TradingSystem + TradeUI designed
├─ Tests: 18 tests written, alignment 92%
├─ Dev: In progress, 14/18 tests passing
└─ Estimate: ~4 more dev cycles to completion
```

**Human**: "Show me the disconnection handling decision"

I RAG-retrieve the child effort's raw log:
```
Retrieved: Clarification effort for #247-disconnection
Full conversation available at: logs/247-disconnection-clarify.jsonl
Summary: Trade cancelled on disconnect, resources returned
```

The human gets exactly what they need without me having stored the full conversation in my active context.

---

## What Made This Work

### 1. One Effort = One Chat (Per Worker)
Each spawned agent has a single focused effort. No topic drift. Clean compaction boundaries.

### 2. Effort Weight = Context Budget
- Critical bugs get maximum context (high weight)
- Docs updates run lean (low weight)
- Director inherits/assigns weight appropriately

### 3. Lazy Compaction at Natural Boundaries
Worker completes → effort resolves → compacts to artifact. Not arbitrary cutoff.

### 4. Child Efforts Roll Up
Clarifications and sub-tasks link to parent. Hierarchy preserved in compact form.

### 5. RAG for Details on Demand
Raw logs exist. Full conversations stored. Retrieved when specifically needed, not loaded always.

### 6. Director Context = Orchestration State
Director doesn't hold full conversations. Holds:
- Open effort summaries
- Compacted resolved efforts
- Kanban state
- Relevant artifacts (RAG-retrieved as needed)

---

## Context Profile Over Time

```
Day 1: 20% (fresh start)
Day 2: 55% (many open efforts)
Day 2 evening: 35% (efforts resolved, compacted)
Day 3: 60% (new sprint started)
Day 3 evening: 40% (sprint completed)
Day 4: 45% (steady state)
...continues indefinitely
```

The context oscillates but never approaches limit because:
- Workers have bounded lifetimes (one effort)
- Director compacts on resolution
- Old resolved efforts age out or compress further
- RAG handles historical detail retrieval

---

## Comparison: Old Model vs New Model

| Old Model | New Model |
|-----------|-----------|
| Director's context grows until forced compaction | Director's context naturally bounded |
| Workers return text, director stores it | Workers return artifacts, director stores summaries |
| Topic drift in long conversations | One effort = one chat enforced |
| Arbitrary compaction loses detail | Semantic compaction preserves meaning |
| Context limit = hard wall | Context limit = never reached |
