# Decision 014: Sessions as Perspective Containers

**Date**: 2026-02-26
**Status**: Accepted

---

## Context

Decision 012 established sessions as audit logs — chronological records of graph interactions. But this undersells them. The question "should there be separate chats?" kept surfacing without a compelling answer beyond "audit trail."

The compelling answer: **perspective**.

## The Insight

A session develops a coherent viewpoint through its system prompt, accumulated context, and reasoning history. Two sessions prompted differently — one from a UI perspective, one from a Backend perspective — produce fundamentally different reasoning about the same problem, even when operating on the same codebase and knowledge graph.

This is impossible in a single session. A single context has one perspective and tends toward confirmation bias — it reinforces its own framing rather than challenging it.

## Decision

**Sessions are perspective containers. Perspective is a first-class property of a session.**

A session's perspective emerges from:
- **System prompt**: The framing, role, and priorities given to the agent
- **Accumulated context**: The facts, decisions, and reasoning developed during the session
- **Knowledge graph subset**: Which nodes were queried and expanded (the "lens" on shared knowledge)

### What this enables

**Multi-agent debate**: Two or more sessions, each with a distinct perspective, can engage each other on a shared problem. Each argues from its developed viewpoint rather than a generic one.

Example: Designing a unified schema
- Session A: prompted as UI/frontend specialist, has developed opinions about client-side data shapes
- Session B: prompted as backend/API specialist, has developed opinions about storage and validation
- They debate via a peer-to-peer channel (WebSocket, MCP, or similar), creating a schema neither would produce alone

This is the Vault roundtable pattern (see `D:\Dev\Open-Intelligence\vault\docs\roundtables\`) made persistent and reusable. The Vault roundtables were one-shot (Round 1: independent, Round 2: engage). With perspective-carrying sessions, the "rounds" can span days, accumulate evidence, and evolve.

### Scaling

| Pattern | Participants | Mechanism |
|---------|-------------|-----------|
| Solo session | 1 agent | Standard chat — single perspective |
| Peer debate | 2 agents | Point-counterpoint on a shared problem |
| Roundtable | 3+ agents + moderator | Structured deliberation with synthesis |
| Adversarial review | 2 agents | One builds, one attacks (red team) |

## What this changes from Decision 012

Decision 012: Sessions are audit logs (passive records).
This decision: Sessions are perspective containers (active viewpoints that can engage each other).

The audit log function remains — it's a subset. But the primary value of a session is the perspective it develops, not just the trail it leaves.

## Implications for the KG

Session perspective should be capturable in the knowledge graph:
- A session's **perspective node** could summarize its viewpoint, biases, and key positions
- Debate outcomes produce higher-quality nodes (tested from multiple angles)
- The graph tracks not just *what was decided* but *which perspectives informed the decision*

This connects to the abstraction layer model ([Decision 013](013-unified-kg-architecture.md)):
- Individual session perspectives are Layer 1 (contextual, personal)
- Debate-validated conclusions are Layer 2 (general, multi-perspective)
- Cross-debate principles are Layer 3 (universal)

## Not decided yet

- **Transport mechanism**: WebSocket, MCP, shared file, or something else for inter-session communication?
- **Debate protocol**: How do agents take turns? Who moderates? When does debate conclude?
- **Perspective persistence**: Is the perspective a KG node, a session metadata field, or derived from the session log?

These are being explored in a separate brainstorm.

## References

- [Decision 012: Sessions as Audit Logs](012-session-as-audit-log.md)
- [Decision 013: Unified KG Architecture](013-unified-kg-architecture.md)
- [Vault Roundtable 001](D:\Dev\Open-Intelligence\vault\docs\roundtables\001-distributed-storage-tech.md) — prior art for multi-model debate
