# Scenario: Problem-First Discovery to Dev Pipeline

Start with a pain point, research the problem space, discover solutions, and produce a brainstorm artifact ready for the dev pipeline.

---

## The Setup

Sometimes you don't have an idea—you have a **problem**. Something's wrong, players are frustrated, metrics are dropping. The solution isn't obvious.

```
Problem Signal → Investigation → Research → Solution Discovery → Brainstorm Artifact
```

This is **discovery work**. You're not refining an idea; you're finding one.

---

## Artifacts & Kanban

All state is local. Artifacts carry their own status via frontmatter:

```yaml
---
status: backlog | ready-for-stories | in-progress | done
created: 2024-01-15
updated: 2024-01-15
tags: [churn-fix, trading]
priority: high
---
```

Discovery produces two artifacts:
```
artifacts/
├── discovery/
│   └── trading-churn-discovery.md    ← Full investigation (status: n/a)
└── brainstorms/
    └── trade-escrow.md               ← Phase 1 solution (status: ready-for-stories)
```

The discovery report is reference material. The brainstorm artifact enters the pipeline.

---

## The Difference

| Approach | Starts With | Process |
|----------|-------------|---------|
| Solo Brainstorm | "What if we added X?" | Refine the idea |
| Roundtable | "Should we do X?" | Debate the idea |
| Problem-First | "Something's broken" | Find the solution |

Problem-first doesn't assume a solution. It investigates first.

---

## Morning: A Problem Signal

### The Symptom

The data team flags an anomaly:

```
ALERT: Player churn spiked 23% this week
- Cohort: Players with 10-50 hours played
- Pattern: Last session was a trade attempt
- No recent deployments or changes
```

This isn't a bug report. It's not a feature request. It's a **signal that something's wrong**.

### Problem Statement (Initial)

```markdown
## Problem Signal

SYMPTOM: Mid-game players churning after trade attempts
IMPACT: 23% increase in week-over-week churn for 10-50hr cohort
UNKNOWN: Why are trade attempts causing churn?
```

We don't know the solution yet. We barely understand the problem.

---

## Investigation Phase

### Gathering Evidence

The investigator (human or AI agent) starts collecting data:

**Player Support Tickets (Last 7 Days)**
```
- "Tried to trade but other guy went offline. Wasted 20 mins."
- "Got scammed. Showed sword in trade window, I accepted, got nothing."
- "Trading is broken. Clicked accept, nothing happened, other player left."
- "How do I find someone to trade with? Chat moves too fast."
```

**Discord Feedback**
```
- "Trading in this game is painful. I'm going back to [competitor]."
- "Spent an hour trying to sell my drops. Nobody buying."
- "Got scammed twice today. Any way to report?"
```

**Session Replay Analysis**
```
Sampled 50 churned players from the cohort:
- 34/50 had failed trade attempts in final session
- Average time spent in trade UI before churn: 12 minutes
- Common pattern: Open trade → Wait → Other player disconnects → Quit game
```

### Problem Refinement

The vague symptom becomes a clearer problem:

```markdown
## Problem Statement (Refined)

CORE ISSUE: Trading is frustrating enough to make players quit

CONTRIBUTING FACTORS:
1. Discovery friction - Hard to find trading partners
2. Trust issues - Scams happen, no recourse
3. Reliability - Trades fail due to disconnections
4. Time waste - Players spend 10+ mins on failed trade attempts

IMPACT: 23% churn spike in mid-game cohort (our most valuable segment)

ROOT CAUSE HYPOTHESIS:
Trading requires synchronous presence of two players with matching needs.
This is rare. Players waste time waiting, get frustrated, leave.
```

---

## Research Phase

Now we understand the problem. Time to research solutions.

### How Do Others Solve This?

**Competitor Analysis**
```markdown
## Trading Systems in Similar Games

### World of Warcraft
- Auction House: Async listings, automated transactions
- Result: Trading is a non-issue. Players rarely quit over it.

### Path of Exile
- Trade website: External tool, search listings, whisper in-game
- Result: Works but clunky. Community complains about friction.

### EVE Online
- Full market system with buy/sell orders
- Result: Trading is a core gameplay loop, not friction.

### Animal Crossing
- No built-in solution. Community uses Discord/Reddit.
- Result: Players accept it because game is casual.

PATTERN: Successful games either have async trading OR are casual enough
that trading friction doesn't matter. We're neither.
```

**Academic/Industry Research**
```markdown
## Relevant Patterns

### Escrow Systems
Hold items until both parties confirm. Prevents "show then swap" scams.

### Reputation Systems
Track trade history. Flag accounts with scam reports.

### Async Marketplaces
Remove synchronous requirement entirely. List → Buy → Done.

### Trade Windows with Confirmation
Force both players to confirm twice. Reduces accidental accepts.
```

### What's Feasible For Us?

```markdown
## Feasibility Assessment

| Solution | Addresses | Effort | Risk |
|----------|-----------|--------|------|
| Escrow (hold items) | Scams | Low | Low |
| Double-confirm | Accidental accepts | Low | Low |
| Reputation system | Scams | Medium | Medium (gaming) |
| Bulletin board | Discovery | Medium | Low |
| Full auction house | Discovery, async | High | High (economy) |
| External trade site | Discovery | Medium | Medium (fragmentation) |

RECOMMENDED COMBINATION:
1. Quick win: Escrow + double-confirm (fix trust/reliability)
2. Medium term: Bulletin board (fix discovery)
3. Long term: Evaluate auction house based on data
```

---

## Solution Discovery

The solution emerges from the research:

```markdown
## Proposed Solution

### Insight
The problem isn't one thing—it's three:
1. Trust (scams, failed trades)
2. Discovery (can't find partners)
3. Sync requirement (both online simultaneously)

### Phased Approach

PHASE 1: Trust & Reliability (Quick Wins)
- Add escrow: Items locked during trade, released on confirm
- Add double-confirm: Both players confirm twice before execution
- Add trade log: Record of completed trades for dispute resolution
- Effort: ~1 sprint
- Impact: Addresses scams and failed trades immediately

PHASE 2: Discovery (Medium Term)
- Add bulletin board (see: roundtable synthesis)
- Effort: ~2 sprints
- Impact: Addresses "can't find partners" problem

PHASE 3: Async (Long Term, Conditional)
- Full auction house IF Phase 1+2 don't reduce churn sufficiently
- Gate: Re-evaluate churn metrics 4 weeks after Phase 2

### Success Metrics
- Primary: Reduce 10-50hr cohort churn to baseline (pre-spike levels)
- Secondary: Reduce average time-in-trade-UI from 12min to <3min
- Secondary: Zero scam reports in support tickets
```

---

## Afternoon: Documentation

### Discovery Report

The full investigation becomes a discovery artifact:

```markdown
---
type: discovery
created: 2024-01-15
problem: trading-churn
---

# Discovery Report: Trading-Related Churn

## Executive Summary
Mid-game player churn spiked 23% due to trading friction. Investigation
identified three root causes: trust issues, discovery friction, and
synchronous requirements. Recommend phased solution starting with quick
wins (escrow, double-confirm) before larger investments.

## Problem Evidence
[Support tickets, Discord feedback, session replay data]

## Root Cause Analysis
[The three contributing factors with evidence]

## Research Findings
[Competitor analysis, industry patterns, feasibility matrix]

## Recommended Solution
[Phased approach with effort/impact for each phase]

## Success Metrics
[How we'll know it worked]

## Open Questions
- Should we notify players when someone wants to trade their listed item?
- Do we need a "report scammer" button or just use existing report system?
- What happens to escrowed items if a player disconnects mid-trade?
```

Saved to: `artifacts/discovery/trading-churn-discovery.md`

---

## Brainstorm Artifact Creation

Phase 1 becomes a brainstorm artifact:

```markdown
---
status: backlog
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, churn-fix, trading]
priority: high
source: artifacts/discovery/trading-churn-discovery.md
---

# Add Trade Escrow and Double-Confirm

## Summary
Add escrow and double-confirm to existing trade system to address
trust and reliability issues causing player churn.

## Context
- Discovery Report: artifacts/discovery/trading-churn-discovery.md
- 23% churn spike in 10-50hr player cohort
- Root cause: Trade failures and scams frustrate players

## Proposed Solution

### Escrow System
- When trade is initiated, items are "locked" (can't be modified)
- Items remain locked until trade completes or is cancelled
- Prevents "show then swap" scam pattern

### Double-Confirm
- After both players add items, first confirm locks the offer
- Second confirm executes the trade
- Either player can cancel before second confirm
- UI shows clear state: "Waiting for confirm" → "Ready to execute"

### Trade Log
- Record completed trades: who, what, when
- Players can view their own trade history
- Enables dispute resolution via support

## Scope
**In scope:**
- Escrow locking during trade
- Two-phase confirmation
- Basic trade history (last 20 trades)

**Out of scope (separate artifacts):**
- Bulletin board (Phase 2)
- Auction house (Phase 3, conditional)
- Reputation system (not pursuing)

## Success Indicators
- [ ] Items are locked when trade window opens
- [ ] Trade requires two confirms from each player
- [ ] Players can view their recent trade history
- [ ] Scam pattern (show/swap) is no longer possible
- [ ] Metric: Support tickets mentioning "scam" drop to zero
- [ ] Metric: Churn in 10-50hr cohort returns to baseline within 4 weeks

*Note: Story-agent will refine these into formal, testable acceptance criteria.*

## Open Questions
- What happens to locked items if a player disconnects?
- Timeout duration for escrow (suggest: 5 minutes, then auto-cancel)?

## Linked Documents
- Discovery Report: artifacts/discovery/trading-churn-discovery.md
- Phase 2 (Bulletin Board): Will be separate artifact
- Phase 3 (Auction House): Conditional on Phase 1+2 results
```

Saved to: `artifacts/brainstorms/trade-escrow.md`

---

## Human Gate

PO reviews the discovery report and brainstorm artifact:

```
PO Review:
- Investigation is thorough, evidence is solid
- Phased approach makes sense—de-risks the big investment
- Phase 1 is low-effort, high-impact—approve for immediate work
```

The PO updates the frontmatter:

```yaml
---
status: ready-for-stories
priority: high
...
---
```

**Story-agent wakes up.** It polls for `status: ready-for-stories` and claims the artifact.

---

## Success Indicators vs Formal AC

| Phase | Produces | Character |
|-------|----------|-----------|
| Problem-First Discovery | Success indicators + metrics | "How do we know the problem is solved?" |
| Story-agent | Formal AC | "How does QA prove it works?" |

Problem-first discovery often includes **metrics** as success indicators because the goal is solving a measurable problem.

**Example transformation:**

```
SUCCESS INDICATOR (from discovery):
"Metric: Support tickets mentioning 'scam' drop to zero"

FORMAL AC (from story-agent):
"Given a player attempts the 'show then swap' scam pattern
 When they try to modify items after first confirm
 Then the modification is blocked
 And the other player sees no change in the trade window
 And the trade log records the attempt"
```

---

## What Made This Work

### 1. Started With Evidence, Not Assumptions
The investigation gathered data before proposing solutions. No "I think the problem is X."

### 2. Problem Refinement
Vague symptom (churn spike) became specific problems (trust, discovery, sync).

### 3. Research Before Solutioning
Looked at how others solved it. Avoided reinventing the wheel.

### 4. Feasibility-Aware Recommendations
Solutions mapped to effort and risk. Not just "what's ideal" but "what's practical."

### 5. Phased De-Risking
Big solution (auction house) deferred until smaller solutions prove insufficient.

### 6. Metrics as Success Criteria
Problem-first work ties to measurable outcomes. "Did churn go down?" is the real test.

### 7. Self-Contained State
Artifacts carry their own status. No external system to sync. Git tracks history.

---

## When to Use Problem-First Discovery

| Situation | Recommended |
|-----------|-------------|
| Clear feature idea | Solo brainstorm or roundtable |
| Metric anomaly (churn, engagement, revenue) | Problem-first discovery |
| Vague user complaints | Problem-first discovery |
| "Something feels wrong" | Problem-first discovery |
| Competitor just shipped something | Roundtable |
| Known solution, unclear if we should build | Roundtable |

Problem-first is for **diagnostic work**. Use it when you don't know what to build.

---

## Variations

### AI-Driven Discovery

An AI agent notices the anomaly and self-initiates:

```
[TRIGGER] Churn anomaly detected in 10-50hr cohort

Discovery Agent starts:
- Pulls support tickets, Discord feedback
- Analyzes session replays
- Researches competitor solutions
- Produces discovery report
- Creates draft brainstorm artifact with status: needs-review
```

Human still gates entry to dev pipeline, but AI did the investigation.

### Collaborative Investigation

Multiple agents divide the research:

```
Agent 1: Support ticket analysis
Agent 2: Session replay analysis
Agent 3: Competitor research
Synthesis Agent: Combines findings into report
```

Parallelizes the discovery work.

### Continuous Discovery

Discovery isn't a one-time event. A "discovery agent" continuously monitors:

```
Always running:
- Watch churn metrics
- Scan support tickets for patterns
- Monitor Discord sentiment
- Flag anomalies for investigation
```

Problems are caught earlier when discovery is continuous.

---

## Artifacts Produced

```
artifacts/discovery/trading-churn-discovery.md    ← Full investigation
artifacts/brainstorms/trade-escrow.md             ← Phase 1 (with frontmatter status)
```

The discovery report captures the investigation. The brainstorm artifact enters the pipeline.

Later phases become separate artifacts when gated metrics are met.

---

## Connection to Dev Pipeline

```
Discovery Output                 Dev Pipeline Input
       ↓                               ↓
  Discovery Report ────────────→  Reference material
  Brainstorm Artifact  ────────→  story-agent polls status: ready-for-stories
  (status updated)                     ↓
                                  story-agent claims (status: in-progress-stories)
                                       ↓
                                  (pipeline continues)

Later:
  Phase 2 Artifact ────────────→  Created after Phase 1 success metrics met
  Phase 3 Artifact ────────────→  Conditional on Phase 1+2 results
```

Discovery often produces **multiple artifacts** (one per phase), but only the first enters the pipeline immediately. Later phases are gated on results.
