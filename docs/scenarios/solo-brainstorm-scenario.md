# Scenario: Solo Brainstorm to Dev Pipeline

A single agent or human ideates, refines a rough idea, and produces a brainstorm artifact ready for the dev pipeline.

---

## The Setup

Before the dev pipeline (story-agent → architect → test → dev → review → qa), ideas need to be captured and shaped. This scenario covers the **solo brainstorming flow**:

```
Raw Idea → Exploration → Refinement → Brainstorm Artifact → Dev Pipeline
```

The brainstormer works alone. No collaboration, no roundtable. Just one mind (human or AI) taking a vague notion and crystallizing it into something actionable.

---

## Artifacts & Kanban

All state is local. Artifacts carry their own status via frontmatter:

```yaml
---
status: backlog | ready-for-stories | in-progress | done
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, player-request]
---
```

Agents poll for artifacts matching their target status. No external system needed.

```
artifacts/
└── brainstorms/
    └── trade-history.md    ← status: ready-for-stories
```

---

## Morning: A Vague Idea Emerges

### The Spark

A developer is working on the game. They notice something:

```
"Players keep asking in Discord: 'Can I see what trades I did yesterday?'
There's no trade history. Huh."
```

This isn't a bug. It's not a planned feature. It's just... an observation.

### Capture Before It's Lost

The developer opens their brainstorm tool (could be a markdown file, a dedicated app, or just a chat with an AI):

```markdown
## Raw Idea
Players want trade history. Currently no way to see past trades.
```

That's it. 30 seconds. The idea is captured. The developer moves on with their day.

---

## Lunch: Exploration Phase

The developer returns to the idea during lunch. Time to explore.

### Asking Questions

```markdown
## Exploration

### Why do players want this?
- Verify they weren't scammed
- Track their economy progress
- Settle disputes ("I traded you 50 gold, not 5!")
- Nostalgia/journal feeling

### What would "trade history" even mean?
- List of all trades? Too much?
- Last N trades?
- Searchable archive?
- Just today's trades?

### What already exists?
- TradingSystem handles live trades
- No persistence after trade completes
- Database has player inventory, no trade logs

### What's the minimal version?
- Show last 10 trades per player
- Who, what, when
- No search, no export, just a list
```

The exploration isn't structured. It's messy. That's fine—this is brainstorming.

### Surfacing Concerns

```markdown
### Potential Issues
- Privacy: Can players see OTHER players' trade history?
- Storage: Do we keep trades forever? Disk cost?
- Performance: Query on every trade screen open?
- Abuse: Could this expose exploits? (mass gold duping visible in logs)
```

The developer isn't solving these yet. Just noting them.

---

## Afternoon: Refinement Phase

The raw exploration is useful but chaotic. Time to shape it.

### Defining Scope

```markdown
## Refined Concept

### Core Feature
"Players can view their own recent trade history"

### In Scope (v1)
- Player sees THEIR OWN trades only (not others')
- Last 20 trades displayed
- Shows: timestamp, other player, items exchanged
- Accessible from inventory screen

### Out of Scope (future)
- Searching/filtering trades
- Exporting trade history
- Admin view of all trades
- Trade dispute resolution system

### Key Decision
Privacy-first: Only show your own trades. No "see what X traded" feature.
```

### Validating Against Concerns

```markdown
### Concerns Addressed
- Privacy: ✅ Players only see own history
- Storage: ⚠️ Need to decide retention policy (suggest 30 days)
- Performance: ✅ Query only on screen open, index by player_id
- Abuse: ⚠️ Admins might want this later, but v1 is player-facing only
```

### The One-Liner Test

Can you explain it in one sentence?

```
"Players can view their last 20 trades from the inventory screen."
```

Yes. The idea is crystallized.

---

## Evening: Artifact Creation

The refined idea is ready to enter the dev pipeline. Time to create the brainstorm artifact.

### Writing the Artifact

```markdown
---
status: backlog
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, player-request]
priority: normal
---

# Add Player Trade History

## Summary
Players can view their own recent trade history from the inventory screen.

## Context
- Players frequently ask in Discord about past trades
- Currently no way to verify or review completed trades
- Common request for dispute resolution and progress tracking

## Proposed Solution
- Store trade records in database (new TradeHistory table)
- Show last 20 trades per player
- Display: timestamp, other player name, items given/received
- Access via new "History" tab on inventory screen

## Scope
**In scope:**
- Player views own trades only
- Last 20 trades
- Basic list display

**Out of scope (future work):**
- Search/filter
- Export
- Admin tools
- Cross-player visibility

## Open Questions
- Retention policy: 30 days? Forever?
- Should trades be immutable or can players "hide" entries?

## Success Indicators
What would make this feel "done" from a player's perspective?
- [ ] Player can open trade history from inventory
- [ ] Shows recent trades (last ~20)
- [ ] Each entry shows: date, other player, items exchanged
- [ ] Only player's own trades are visible

*Note: Story-agent will refine these into formal, testable acceptance criteria.*
```

The artifact is saved to `artifacts/brainstorms/trade-history.md`. It sits in the backlog.

---

## Later: Human Gate

A product owner reviews the backlog. They open artifacts with `status: backlog`:

```
PO Review:
- Good scope, clear success indicators
- Aligns with player feedback
- Approved for pipeline
```

The PO updates the frontmatter:

```yaml
---
status: ready-for-stories
created: 2024-01-15
updated: 2024-01-16
tags: [enhancement, player-request]
priority: normal
---
```

**The dev pipeline begins.** Story-agent polls for `status: ready-for-stories` and claims the artifact.

---

## Success Indicators vs Formal AC

The brainstorm phase produces **success indicators**—rough, user-facing descriptions of what "done" looks like. The story-agent later refines these into **formal acceptance criteria** that are precise and testable.

| Phase | Produces | Character |
|-------|----------|-----------|
| Brainstorm | Success indicators | "What would make players happy?" |
| Story-agent | Formal AC | "How does QA prove it works?" |

**Example transformation:**

```
SUCCESS INDICATOR (from brainstorm):
"Shows recent trades (last ~20)"

FORMAL AC (from story-agent):
"Given a player with 25 completed trades
 When they open the trade history screen
 Then they see exactly 20 trades
 And trades are ordered by timestamp descending
 And the oldest 5 trades are not displayed"
```

The brainstormer focuses on **intent**. The story-agent focuses on **verification**.

---

## What Made This Work

### 1. Capture First, Refine Later
The raw idea was saved in 30 seconds. Exploration happened hours later. No pressure to have a complete thought immediately.

### 2. Exploration Before Commitment
Asking "why" and "what could go wrong" happened BEFORE writing the artifact. Concerns were surfaced early.

### 3. Explicit Scoping
"In scope" and "out of scope" prevent feature creep. The artifact is clear about what it IS and ISN'T.

### 4. The One-Liner Test
If you can't explain it in one sentence, it's not ready. This forces clarity.

### 5. Human Gate Before Pipeline
The PO reviews before it enters the dev pipeline. Bad ideas get filtered. Good ideas get blessed.

### 6. Self-Contained State
The artifact carries its own status. No external system to sync. Git tracks history.

---

## Variations

### AI-Assisted Solo Brainstorm

Same flow, but the developer uses an AI assistant:

```
Developer: "Players keep asking about trade history. Brainstorm this with me."

AI: "What problem does trade history solve for players?"

Developer: "Mostly disputes and verifying trades."

AI: "So the core need is trust verification, not comprehensive logging.
     A minimal version might just show recent trades.
     Do you want v1 to be player-facing or include admin tools?"

Developer: "Player-facing only."

AI: "Got it. Here's a draft scope..."
```

The AI accelerates the exploration and refinement phases but doesn't replace them.

### Fully Autonomous AI Brainstorm

An AI agent notices a pattern (e.g., analyzing Discord feedback) and initiates:

```
[TRIGGER] Discord analysis shows 47 mentions of "trade history" in past week

AI Brainstorm Agent starts new effort:
- Explores the concept
- Identifies scope
- Drafts artifact with status: needs-review
- Human reviews before moving to ready-for-stories
```

The human gate is still mandatory. AI can brainstorm, but humans approve what enters the pipeline.

---

## Artifacts Produced

By the end of a solo brainstorm:

```
artifacts/brainstorms/trade-history.md    ← The artifact (with frontmatter status)
```

The artifact is the only required output. Kanban state lives in the frontmatter.

---

## Connection to Dev Pipeline

Once the artifact status changes to `ready-for-stories`:

```
Solo Brainstorm Output          Dev Pipeline Input
        ↓                              ↓
   Brainstorm Artifact  ───────→  story-agent polls status: ready-for-stories
   (status updated)                    ↓
                                  story-agent claims (status: in-progress-stories)
                                       ↓
                                  (pipeline continues)
```

The brainstorm phase is complete. The dev pipeline takes over.
