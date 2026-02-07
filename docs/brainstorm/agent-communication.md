# Agent Communication: Disputes, Escalation, and Coordination

How peer agents communicate, disagree, and escalate without a central director.

---

## Core Principle: Stateless Agents, Stateful Items

Agents are ephemeral. They:
- Pick up work
- Do the work (one effort = one chat)
- Update the item
- Die

All state lives in the **kanban item**, not the agent.

---

## Communication Mechanisms

Agents don't talk to each other. They communicate via:

| Mechanism | Purpose |
|-----------|---------|
| **Kanban columns** | Workflow state (ready, in-progress, blocked) |
| **Artifact comments** | Detailed feedback, questions, disputes |
| **Item metadata** | failure_count, escalation_tier, tags |
| **Column moves** | Trigger next agent, backflow for issues |

---

## Disputes: When Agents Disagree

### Example: Dev thinks test is wrong

```
DEV-AGENT                              TEST-ARCHITECT
    │                                        │
    │ 1. Comments on test artifact:          │
    │    "Test assumes sync, but arch        │
    │     specifies async. Test is wrong."   │
    │                                        │
    │ 2. Moves issue to "Ready for Tests"    │
    │                                        │
    │ 3. Dies (effort complete)              │
    │                                        │
    │                          4. Picks up issue
    │                          5. Reads comment
    │                          6. Either:
    │                             a) Agrees → fixes test
    │                             b) Disagrees → replies
    │                                        │
    │ 7. If disagreed:                       │
    │    - Reply comment added               │
    │    - Issue moves to "Ready for Dev"    │
    │    - Test-architect dies               │
    │                                        │
    │ 8. Dev-agent picks up                  │
    │    Reads reply, continues or accepts   │
```

### Comment Structure

```yaml
# Artifact: tests/247-trading-tests.md
# Metadata: tests/247-trading-tests.meta.yaml

comments:
  - id: c001
    author: dev-agent
    timestamp: 2024-01-17T14:30:00
    target: "test_trade_cancellation"  # specific test/section
    content: |
      This test assumes synchronous cancellation, but the
      architecture doc specifies async event-driven cancellation.
      Test will always fail with correct implementation.
    status: open

  - id: c002
    author: test-architect
    timestamp: 2024-01-17T15:45:00
    parent: c001  # reply to
    content: |
      You're right. Architecture says async. Updating test
      to use async/await pattern with proper event mocking.
    status: resolved
    resolution: accepted
```

### Dispute Resolution Flow

```
┌─────────────────────────────────────────────────────────┐
│                  DISPUTE PROTOCOL                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Agent comments with specific concern                │
│  2. Agent moves issue backward to previous stage        │
│  3. Previous-stage agent picks up, reads comment        │
│  4. Previous agent either:                              │
│     ├─► AGREES: fixes, marks resolved, moves forward    │
│     └─► DISAGREES: replies, moves back to disputer      │
│  5. Repeat until resolution                             │
│  6. After N rounds (3?): auto-flag for human            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Circuit Breaker

Prevent infinite ping-pong:

```yaml
issue: 247
dispute_rounds: 3
dispute_agents: [dev-agent, test-architect, dev-agent, test-architect]
status: needs-human-review
flag: "Agents disagree after 3 rounds - human decision needed"
```

---

## Escalation: When Agents Can't Solve

Different from disputes. Escalation = "I can't do this" not "I disagree with you".

### The Problem

If agent A spawns agent B for escalation:
- Does A need to stay alive?
- A's context is wasted waiting
- Process dependency = fragile

### The Solution: Stateless Escalation

**The kanban item carries escalation state, not the agent.**

```yaml
# Issue 247 in kanban
issue: 247
status: ready-for-dev
failure_count: 3
failure_history:
  - attempt: 1
    model: glm-4
    reason: "Test expects 42, got 41"
  - attempt: 2
    model: glm-4
    reason: "Same issue, tried different approach"
  - attempt: 3
    model: sonnet
    reason: "Still failing, suspect loop boundary"
```

### Model Ladder

Agent reads `failure_count`, configures itself:

```python
# Agent startup
issue = claim_next_issue("ready-for-dev")

MODEL_LADDER = {
    0: "glm-4",      # First try: free
    1: "glm-4",      # Second try: free
    2: "sonnet",     # Third try: standard
    3: "sonnet",     # Fourth try: standard
    4: "opus",       # Fifth try: expensive
    5: "opus",       # Sixth try: expensive
    6: None,         # Give up → escalate column
}

model = MODEL_LADDER.get(issue.failure_count)

if model is None:
    issue.comment("Failed 6 attempts across all model tiers")
    issue.move_to("needs-senior-dev")
    exit()

self.configure(model=model)
self.run(issue)
```

### Escalation Flow

```
ISSUE 247
─────────────────────────────────────────────────────
failure_count: 0 → dev-agent (GLM) → FAIL
failure_count: 1 → dev-agent (GLM) → FAIL
failure_count: 2 → dev-agent (Sonnet) → FAIL
failure_count: 3 → dev-agent (Sonnet) → FAIL
failure_count: 4 → dev-agent (Opus) → FAIL
failure_count: 5 → dev-agent (Opus) → FAIL
failure_count: 6 → moves to "needs-senior-dev"
─────────────────────────────────────────────────────

Senior-dev-agent picks up (starts with Sonnet/Opus)
If still fails → moves to "needs-human"
```

### Key Properties

| Property | How |
|----------|-----|
| **No process dependency** | Agent dies after each attempt |
| **Stateless agents** | All state in kanban item |
| **Configurable ladder** | YAML config per agent type |
| **Audit trail** | failure_history shows all attempts |
| **No director** | Item self-describes escalation state |

### Config: Model Ladder per Agent Type

```yaml
# ~/.oi/config/escalation.yaml

model_ladder:
  dev-agent:
    0-1: glm-4       # Simple stuff might work
    2-3: sonnet      # Medium complexity
    4-5: opus        # Hard problems
    6+: escalate     # Give up, need help

  test-architect:
    0-1: sonnet      # Tests need reasoning
    2-3: opus
    4+: escalate

  story-agent:
    0-2: haiku       # Stories are simpler
    3-4: sonnet
    5+: escalate

  qa-agent:
    0-1: sonnet      # QA needs attention
    2-3: opus
    4+: escalate
```

---

## Specialist Columns (Future)

When escalating, agent can specify WHY it's stuck:

```yaml
# Issue metadata
escalation_reason: concurrency
# or: security, performance, architecture, unknown
```

Maps to specialist columns:

| Reason | Column | Watched By |
|--------|--------|------------|
| concurrency | needs-concurrency-expert | concurrency-specialist |
| security | needs-security-review | security-specialist |
| performance | needs-perf-tuning | performance-specialist |
| architecture | needs-arch-clarification | architect-agent (senior) |
| unknown | needs-senior-dev | senior-dev-agent |

Specialists are just agents with:
- Specific column watches
- Higher default model tiers
- Domain-specific instructions

---

## Column Structure

Full kanban with escalation:

```
NORMAL FLOW:
ready → stories → arch → tests → dev → review → qa → done

ESCALATION COLUMNS:
needs-senior-dev
needs-concurrency-expert
needs-security-review
needs-human

BACKFLOW COLUMNS:
blocked-needs-story-clarification
blocked-needs-arch-clarification
blocked-needs-test-review

DISPUTE COLUMNS:
dispute-test-vs-dev
dispute-story-vs-arch
```

Or simpler: just use tags + a single "blocked" column with tags indicating why.

---

## Summary

| Concept | Mechanism | State Location |
|---------|-----------|----------------|
| **Workflow** | Column moves | Kanban column |
| **Disputes** | Comments + backflow | Artifact comments |
| **Escalation** | failure_count + model ladder | Item metadata |
| **Specialist help** | Escalation tags + columns | Item tags |
| **Human escalation** | "needs-human" column | Kanban column |

All stateless. All via kanban + artifacts. No director needed.
