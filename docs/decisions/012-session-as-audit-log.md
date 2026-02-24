# Decision 012: Sessions as Audit Logs, Not Persistence Boundaries

**Date**: 2026-02-23
**Status**: Accepted

---

## Context

Decision 010 removed projects and sessions as user-facing concepts. Decision 011 made the knowledge graph the single persistent layer. This raised the question: do sessions matter at all?

The initial assumption was no — ambient chat (greetings, tangents) has no value as a node, so sessions are just disposable runtime buffers. But this misses something.

## The Problem

A brainstorm session might touch five existing nodes, reject two approaches, riff on a tangent, and produce one new node. The graph captures the one node. Everything else is lost:

- **Which nodes were referenced** during the conversation (but not modified)
- **The order** things were considered
- **Dead ends** — approaches explored and rejected
- **Ambient reasoning** that didn't crystallize into a node yet

This "dark matter" between nodes is the connective tissue that shows *how you got there*, not just *what you concluded*. A throwaway tangent today might be the missing link six months later when trying to remember why approach B was rejected.

Node timestamps don't solve this:
- `updated` shifts when a node is modified from a different chat — original temporal position lost
- References without modifications create no edges — the interaction is invisible in the graph
- There's no record of which nodes were accessed together, or in what order

## Decision

**Sessions are first-class artifacts — chronological audit logs of graph interactions + ambient conversation.**

A session is NOT:
- A persistence boundary (nodes live in the global graph)
- A scoping mechanism (knowledge flows across sessions)
- A user-managed container (no naming, no selecting)

A session IS:
- An append-only chronological record
- A log of which nodes were created, referenced, or modified
- The ambient conversation that surrounded those interactions
- Linkable from any node that was touched during it
- Queryable later ("what was I thinking when I created this decision?")

### What gets captured

| Event | Captured? | Why |
|-------|-----------|-----|
| Node created | Yes | Links back to the session that produced it |
| Node referenced (read/queried) | Yes | Shows the brainstorm path |
| Node modified | Yes | Shows when and why it changed |
| Ambient conversation | Yes | The reasoning between node interactions |
| Greetings, chatter | Yes (as part of ambient) | Cheap to store, might provide context |

### Relationship to nodes

Every node already has a `raw_file` field linking to its source conversation. That source conversation lives in a session log. The session log also contains everything that happened *around* that node — the context that led to its creation.

A session log might produce zero nodes (pure brainstorm, no conclusions yet). That's fine — the session is still valuable as a record of exploration.

## What this changes from Decision 010

Decision 010 said "no sessions to manage." That still holds — the user doesn't name, select, or organize sessions. But sessions exist as an implementation artifact:

- Each `oi` invocation creates a session log
- The log captures everything chronologically
- Nodes link back to their originating session
- Sessions are queryable ("show me the session where I created this node")

The key shift: **sessions are raw material that hasn't been refined into nodes yet, but might be someday.**

## Storage

```
~/.oi/
  sessions/
    2026-02-23T10-15-00.jsonl   # chronological log
    2026-02-23T14-30-00.jsonl
  graph/
    knowledge.yaml              # nodes + edges (the persistent layer)
  ...
```

Session logs are append-only JSONL. Each entry is timestamped and typed (user message, assistant message, node-created, node-referenced, tool-call, etc.).

## Not decided yet

- **Retention**: How long do session logs persist? Forever? Decay after N months? Only if linked from a node?
- **Queryability**: Full-text search? Or only via node backlinks?
- **Size**: Do session logs get compacted/summarized over time?

These can be deferred — the architectural commitment is that sessions are captured, not how long they're kept.

## Risks

- **Storage growth**: Every conversation is logged. Mitigation: JSONL is compact; retention policy TBD.
- **Over-engineering**: Maybe nobody ever looks at old session logs. Mitigation: cheap to capture, expensive to lose. Capture now, decide value later.
