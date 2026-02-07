# Scenario: Roundtable Ideation to Dev Pipeline

Multiple AI models deliberate on an idea, challenge each other's assumptions, reach consensus, and produce a brainstorm artifact ready for the dev pipeline.

---

## The Setup

Before the dev pipeline, some ideas benefit from **multiple perspectives**. Instead of one mind refining an idea, several AI models debate it:

```
Seed Idea → Round 1 (Isolated Thinking) → Round 2+ (Engagement) → Synthesis → Brainstorm Artifact
```

Why multiple models?
- Different training → different blind spots
- Adversarial pressure surfaces weak assumptions
- Consensus across models = higher confidence the idea is sound

---

## Artifacts & Kanban

All state is local. Artifacts carry their own status via frontmatter:

```yaml
---
status: backlog | ready-for-stories | in-progress | done
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, economy]
---
```

Roundtables produce two artifacts:
```
artifacts/
├── synthesis/
│   └── auction-house-roundtable.md    ← Full reasoning (status: n/a)
└── brainstorms/
    └── bulletin-board.md              ← Actionable scope (status: ready-for-stories)
```

The synthesis is reference material. The brainstorm artifact enters the pipeline.

---

## The Participants

A typical roundtable:

| Model | Role | Tendency |
|-------|------|----------|
| Claude | Balanced analysis | Nuanced, considers edge cases |
| GPT | Broad exploration | Creative, expansive thinking |
| Gemini | Technical depth | Implementation-focused |

The **host** (could be any model or a human) manages the flow. Panelists respond to prompts.

---

## Morning: A Seed Idea Arrives

A human (or automated trigger) seeds the roundtable:

```markdown
ROUNDTABLE SEED:
"Should we add an in-game auction house where players can list items for sale?"

Context:
- Current system: Direct player-to-player trades only
- Player feedback: "Trading is tedious, hard to find buyers"
- Concern: Could this break the economy?
```

The host frames the question and kicks off Round 1.

---

## Round 1: Isolated Deliberation

**Critical rule**: In Round 1, panelists think independently. They don't see each other's responses. This prevents groupthink.

### Host Prompt

```
Round 1: Initial Position

Consider the auction house proposal. In 150 words or less:
1. What's your initial stance? (Support, Oppose, Conditional)
2. What's the strongest argument for your position?
3. What's the biggest risk you see?

Respond independently. You'll see other perspectives in Round 2.
```

### Claude's Response (Isolated)

```
STANCE: Conditional Support

ARGUMENT FOR:
An auction house solves the discovery problem. Players can't trade what they
can't find buyers for. Async listings let players sell while offline—critical
for different time zones.

BIGGEST RISK:
Price deflation. If supply becomes visible and accessible, prices drop. Rare
items become less rare when everyone can see 50 listings. The scarcity illusion
breaks.

CONDITION:
Support IF we limit listing slots per player and add listing fees to create
friction.
```

### GPT's Response (Isolated)

```
STANCE: Support

ARGUMENT FOR:
Player friction is real. Every hour spent spamming "WTS [item]" in chat is an
hour not playing the game. Auction houses are proven in WoW, FF14, EVE. Players
expect this feature.

BIGGEST RISK:
Bot exploitation. Automated sniping of underpriced items. Without safeguards,
bots will dominate the market and extract value from regular players.

RECOMMENDATION:
Support with anti-bot measures: CAPTCHA on listing, minimum list duration,
rate limits.
```

### Gemini's Response (Isolated)

```
STANCE: Oppose (for now)

ARGUMENT AGAINST:
Implementation complexity is high. Auction house requires: new database tables,
search/filter UI, payment escrow, expiration handling, notification system.
This is 3-4 sprints of work minimum.

BIGGEST RISK:
We build it, economy breaks, we can't un-ship it. Auction houses are nearly
impossible to remove once players depend on them.

RECOMMENDATION:
Start smaller: add a "bulletin board" where players post what they want to
buy/sell, but trades still happen directly. Test demand before building full
auction infrastructure.
```

---

## Round 2: Engagement

Now panelists see each other's Round 1 responses. The host prompts engagement:

### Host Prompt

```
Round 2: Challenge and Refine

You've seen all positions. Now:
1. Which argument from another panelist do you find most compelling?
2. Which argument do you disagree with, and why?
3. Has your position shifted? If so, how?
```

### Claude's Response (Engaged)

```
MOST COMPELLING (from Gemini):
The "bulletin board first" approach is smart. It tests demand with 10% of the
implementation cost. We learn if players actually use async trading before
committing to full auction infrastructure.

DISAGREE WITH (GPT):
"Players expect this feature" is weak reasoning. Players expect lots of things.
The question is whether THIS game benefits from it. We're not WoW.

POSITION SHIFT:
Moving from "Conditional Support" to "Support Bulletin Board First."
Build the minimal async trading. If adoption is high, then build full auction.
```

### GPT's Response (Engaged)

```
MOST COMPELLING (from Gemini):
Implementation cost is real. I underweighted the engineering effort. A bulletin
board MVP is a reasonable middle ground.

DISAGREE WITH (Claude):
"Scarcity illusion" concerns are overblown. Visible supply doesn't destroy
value—it creates efficient markets. Real scarcity (drop rates) remains.

POSITION SHIFT:
Still support auction house long-term, but concede that bulletin board is a
reasonable Phase 1. Willing to compromise on phased approach.
```

### Gemini's Response (Engaged)

```
MOST COMPELLING (from Claude):
Listing fees and slot limits as friction mechanisms. If we DO build an auction
house later, these constraints would address my economy concerns.

DISAGREE WITH (GPT):
"Anti-bot measures" like CAPTCHA are user-hostile. Rate limits are better.
Don't punish legitimate players to stop bots.

POSITION SHIFT:
Remain opposed to full auction house in v1. But if bulletin board succeeds
and we add friction mechanisms, I'd support Phase 2 auction house.
```

---

## Round 3: Convergence

The host pushes for actionable consensus:

### Host Prompt

```
Round 3: Synthesis

We need a concrete recommendation. Propose a single path forward that
addresses the concerns raised. What should we build?
```

### Emerging Consensus

All three panelists converge on a phased approach:

```
PHASE 1: Bulletin Board (MVP)
- Players post "Want to Buy" and "Want to Sell" listings
- Listings are searchable
- Trades still happen directly (players contact each other)
- Minimal implementation: just a listing table + basic UI
- Success metric: >30% of active players use it within 2 weeks

PHASE 2: Full Auction House (if Phase 1 succeeds)
- Automated buy/sell with escrow
- Listing fees (gold sink)
- Limited slots per player (anti-flood)
- Rate limits (anti-bot)

DECISION POINT:
After Phase 1, review usage data. If bulletin board is heavily used AND
players request automation, proceed to Phase 2. Otherwise, bulletin board
is sufficient.
```

---

## Afternoon: Synthesis Document

The host produces a synthesis artifact capturing the roundtable outcome:

```markdown
---
type: synthesis
created: 2024-01-15
roundtable: auction-house-proposal
participants: [claude, gpt, gemini]
---

# Roundtable Synthesis: Auction House Proposal

## Verdict: CONDITIONAL PROCEED (Phased)

## Summary
The roundtable reached consensus on a phased approach:
1. Build a bulletin board MVP to test async trading demand
2. If successful, proceed to full auction house with economy safeguards

## Key Insights by Panelist

| Panelist | Initial Stance | Final Stance | Key Contribution |
|----------|---------------|--------------|------------------|
| Claude | Conditional Support | Support Phase 1 | Friction mechanisms (fees, limits) |
| GPT | Support | Support Phased | Validated player demand for async trading |
| Gemini | Oppose | Support Phase 1 | MVP approach, implementation pragmatism |

## Risks Identified
1. Economy disruption (mitigated by: phased rollout, friction mechanisms)
2. Bot exploitation (mitigated by: rate limits, minimum list duration)
3. Implementation cost (mitigated by: bulletin board MVP first)

## Open Questions for Story Phase
- What's the listing expiration period?
- How do players contact each other from a listing? (in-game mail? whisper?)
- Should listings cost gold to post, or only on successful sale?

## Recommendation
Proceed to dev pipeline with Phase 1 (Bulletin Board) only.
Phase 2 is a separate future artifact, gated on Phase 1 success metrics.
```

Saved to: `artifacts/synthesis/auction-house-roundtable.md`

---

## Evening: Brainstorm Artifact Creation

The synthesis becomes a brainstorm artifact with frontmatter status:

```markdown
---
status: backlog
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, player-request, economy]
priority: normal
source: artifacts/synthesis/auction-house-roundtable.md
---

# Add Player Trading Bulletin Board

## Summary
A searchable board where players post buy/sell listings. Trades still
happen directly between players.

## Context
- Roundtable Synthesis: artifacts/synthesis/auction-house-roundtable.md
- Player feedback indicates trading friction is a top complaint
- This is Phase 1 of a potential auction house system

## Proposed Solution
- New "Bulletin Board" accessible from main menu
- Players can post "Want to Buy" or "Want to Sell" listings
- Listings include: item, quantity, price, player name
- Basic search/filter by item type
- Listings expire after 7 days
- Players contact each other via in-game mail to complete trade

## Scope
**In scope (Phase 1):**
- Listing creation and browsing
- Search by item name/type
- Listing expiration
- Contact seller via mail link

**Out of scope (Phase 2, separate artifact):**
- Automated transactions
- Escrow system
- Listing fees
- Purchase history

## Success Indicators
- [ ] Players can create buy/sell listings
- [ ] Players can browse and search listings
- [ ] Players can contact listing owner
- [ ] Listings auto-expire after 7 days
- [ ] >30% of active players use within 2 weeks (success metric for Phase 2 gate)

*Note: Story-agent will refine these into formal, testable acceptance criteria.*

## Open Questions
- Listing limit per player? (suggest 5-10)
- Can players bump/renew listings?
```

Saved to: `artifacts/brainstorms/bulletin-board.md`

---

## Human Gate

The PO reviews artifacts with `status: backlog`:

```
PO Review:
- Roundtable process surfaced good risks
- Phased approach is sensible
- Success metric for Phase 2 gate is clear
- Approved for pipeline
```

The PO updates the frontmatter:

```yaml
---
status: ready-for-stories
...
---
```

**Story-agent wakes up.** It polls for `status: ready-for-stories` and claims the artifact.

---

## Success Indicators vs Formal AC

Same pattern as solo brainstorm:

| Phase | Produces | Character |
|-------|----------|-----------|
| Roundtable | Success indicators | "What would make players happy?" |
| Story-agent | Formal AC | "How does QA prove it works?" |

**Example transformation:**

```
SUCCESS INDICATOR (from roundtable):
"Players can browse and search listings"

FORMAL AC (from story-agent):
"Given 100 active listings across 5 item categories
 When a player searches for 'sword'
 Then only listings containing 'sword' in item name are displayed
 And results load within 500ms
 And results are paginated at 20 per page"
```

---

## What Made This Work

### 1. Isolated First Round
Panelists thought independently before seeing others. This prevented anchoring and groupthink.

### 2. Adversarial Pressure
Round 2 required engaging with disagreements. Weak arguments got challenged. Strong arguments survived.

### 3. Forced Convergence
Round 3 pushed for a single recommendation. No "we couldn't decide"—the roundtable must produce an actionable output.

### 4. Phased Recommendations
When full consensus isn't possible, phased approaches let cautious and aggressive voices both win: "try small, then expand."

### 5. Synthesis Document
The roundtable produced a document capturing the reasoning, not just the conclusion. Future readers understand WHY.

### 6. Human Gate
PO still reviews before pipeline entry. Roundtable advises, humans decide.

### 7. Self-Contained State
Artifacts carry their own status. No external system to sync. Git tracks history.

---

## When to Use Roundtable vs Solo

| Situation | Recommended |
|-----------|-------------|
| Simple feature, clear requirements | Solo brainstorm |
| Controversial, could break things | Roundtable |
| Economy/balance changes | Roundtable |
| High implementation cost | Roundtable |
| Reversible, low risk | Solo brainstorm |
| Multiple valid approaches | Roundtable |

Roundtables are expensive (multiple model calls, more time). Use them when the stakes justify the cost.

---

## Variations

### Human-in-the-Loop Roundtable

A human participates as a panelist alongside AI models:

```
Panelists: Claude, GPT, Human (Product Owner)
```

The human brings domain knowledge AI lacks. AI brings breadth and adversarial challenge.

### Async Roundtable

Panelists don't need to respond simultaneously. The host collects responses over hours/days:

```
Day 1: Round 1 responses collected
Day 2: Round 2 engagement
Day 3: Round 3 synthesis
```

Useful for busy teams or when deep thought is needed.

### Tie-Breaker Rounds

If Round 3 doesn't converge, add a tie-breaker:

```
Round 4: Final Vote

Given the discussion, vote: BUILD or DON'T BUILD.
Majority wins. Dissenting opinion recorded in synthesis.
```

Dissent is valuable signal—record it even when overruled.

---

## Artifacts Produced

```
artifacts/synthesis/auction-house-roundtable.md    ← Full reasoning
artifacts/brainstorms/bulletin-board.md            ← Actionable scope (with frontmatter status)
```

The synthesis captures WHY. The brainstorm artifact enters the pipeline.

---

## Connection to Dev Pipeline

```
Roundtable Output                Dev Pipeline Input
       ↓                               ↓
  Synthesis Doc ──────────────→  Reference material
  Brainstorm Artifact  ───────→  story-agent polls status: ready-for-stories
  (status updated)                     ↓
                                  story-agent claims (status: in-progress-stories)
                                       ↓
                                  (pipeline continues)
```

The roundtable phase is complete. The dev pipeline takes over.
