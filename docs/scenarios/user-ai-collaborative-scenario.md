# Scenario: User-AI Collaborative Brainstorm to TDD Pipeline

A user and AI assistant brainstorm together, iteratively refining an idea through conversation, producing a brainstorm artifact that feeds into the TDD dev pipeline.

---

## The Setup

This is the most common brainstorming pattern: a human with a rough idea talks it through with an AI assistant. The conversation is the refinement process.

```
User's Rough Idea → Conversation → Brainstorm Artifact (.md) → TDD Pipeline
```

The AI doesn't just take notes—it **challenges, clarifies, and suggests**. The user doesn't just dictate—they **react, redirect, and decide**.

---

## Artifacts & Kanban

All state is local. Artifacts carry their own status via frontmatter:

```yaml
---
status: backlog | ready-for-stories | in-progress | done
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, social]
---
```

Agents poll for artifacts matching their target status. No external system needed.

```
artifacts/
└── brainstorms/
    └── guild-system-v1.md    ← status: ready-for-stories
```

---

## Morning: The Conversation Begins

### User Has a Rough Idea

```
User: I want to add guilds to the game. Like, players can form groups
      and do stuff together.
```

That's it. Vague. "Do stuff together" isn't a spec.

### AI Starts Exploring

```
AI: Guilds can mean a lot of things. Let me ask a few questions to
    narrow this down.

    What's the primary purpose of guilds in your game?
    - Social (chat, identity, belonging)
    - Cooperative gameplay (guild quests, raids)
    - Competitive (guild vs guild battles)
    - Economic (shared resources, guild bank)

    Which of these feels most important for v1?
```

```
User: Social first. Players keep asking for a way to "stick together"
      with their friends. The Discord is full of people forming informal
      groups already.
```

```
AI: So the core need is formalizing groups that already exist informally.

    That suggests a minimal v1:
    - Create/join a guild
    - Guild member list
    - Guild chat channel

    No quests, no bank, no battles. Just "we're a group."

    Does that feel right, or is something missing?
```

```
User: Yeah that's close. But I also want some kind of guild identity.
      Like a name and maybe a tag that shows next to your name.
```

```
AI: Got it. So:
    - Guild has a name and a short tag (e.g., "[WOLF] PlayerName")
    - Tag displays in chat and nameplates

    That adds identity without adding mechanics. Still minimal.

    One question: who can create a guild? Anyone? Or some requirement?
```

```
User: Hmm. If anyone can create one, we'll have thousands of dead guilds.
      Maybe require... 3 players to form one? You need a founding group.
```

```
AI: Smart. Prevents spam guilds.

    So the flow is:
    1. Player invites 2 others to "found" a guild
    2. All 3 accept → guild is created
    3. After that, the leader can invite more members

    What about leaving/kicking? Can members leave freely? Can leaders
    kick members?
```

```
User: Yeah, both. Leave freely, leader can kick. And if the leader leaves,
      the oldest member becomes leader automatically.
```

---

## Mid-Morning: Challenging Assumptions

### AI Pushes Back

```
AI: Automatic succession could cause drama. What if the oldest member
    doesn't want to lead?

    Alternative: When leader leaves, they pick a successor. If they don't
    pick (or ragequit), THEN it falls to oldest member.

    Or: The guild enters a "leaderless" state and members vote.

    Which feels right for your game's culture?
```

```
User: Voting sounds like overkill for v1. Let's do your first suggestion:
      leader picks successor, fallback to oldest member.
```

```
AI: Noted. One edge case: what if a guild drops below 3 members? Does it
    disband, or can it keep existing?
```

```
User: Keep existing. The 3-member requirement is only for creation. Once
      it exists, even 1 person can keep it alive.
```

```
AI: Makes sense. Prevents losing guild history/name if people go inactive.

    Last question on scope: guild size limit?
```

```
User: Hadn't thought about that. What do other games do?
```

```
AI: Varies widely:
    - Small (10-20): Tight-knit, everyone knows everyone
    - Medium (50-100): Room to grow, some strangers
    - Large (200+): Basically a community, lots of inactive members

    For a social-first guild with no mechanics (no raids that need 40
    people), I'd suggest starting small: 20-30 max. You can always
    increase later, but decreasing is painful.
```

```
User: Yeah, let's do 25 max for v1. We can bump it later if people ask.
```

---

## Late Morning: Surfacing Concerns

### AI Identifies Risks

```
AI: Let me flag a few risks I see:

    1. NAME SQUATTING
       Players grab good guild names and sit on them.
       Mitigation: Inactive guilds (no logins for 60 days) lose their name?

    2. OFFENSIVE NAMES/TAGS
       "[NAZI] PlayerName" in your game.
       Mitigation: Profanity filter + report mechanism + manual review queue.

    3. GUILD SPAM INVITES
       Players get bombarded with random invites.
       Mitigation: Opt-in ("allow guild invites" setting) or invite cooldown.

    Which of these worry you most?
```

```
User: All of them actually. But for v1... let's do profanity filter on
      names, and an opt-out setting for invites. The name squatting thing
      can wait—we'll see if it's actually a problem first.
```

```
AI: Sounds pragmatic. Ship, learn, iterate.

    I think we have enough for a solid v1 scope. Want me to draft the
    brainstorm artifact?
```

```
User: Yeah, let's see it.
```

---

## Noon: The Artifact

AI produces the brainstorm artifact:

```markdown
---
status: backlog
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, social, player-request]
priority: normal
---

# Guild System (v1)

## Origin
User-AI collaborative session, 2024-01-15

## Core Concept
Formalize player groups that already exist informally. Social-first guilds
focused on identity and belonging, not mechanics.

## Scope

### In Scope (v1)
- Create guild (requires 3 founding members)
- Guild name + short tag (e.g., "[WOLF]")
- Tag displays on nameplates and in chat
- Member list (view who's in the guild)
- Guild chat channel
- Join by invite only
- Leave guild freely
- Leader can kick members
- Leader can transfer leadership
- Auto-succession if leader leaves without transferring (oldest member)
- Max 25 members
- One guild per player (no multi-guild)

### Out of Scope (future)
- Guild quests/missions
- Guild bank/shared resources
- Guild vs guild battles
- Guild leveling/progression
- Public guild listings/recruitment
- Guild alliances

## Key Decisions

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Creation requirement | 3 founders | Prevents spam/dead guilds |
| Minimum to persist | 1 member | Don't lose history if people leave |
| Size limit | 25 | Social-first, can increase later |
| Succession | Leader picks, fallback to oldest | Simple, avoids voting complexity |
| Invite model | Invite-only, opt-out setting | Prevents spam, respects player choice |
| Multi-guild | No, one per player | Simplicity, clear identity |

## Risks & Mitigations

| Risk | Mitigation | Status |
|------|------------|--------|
| Offensive names | Profanity filter + report | v1 |
| Guild invite spam | Opt-out setting | v1 |
| Name squatting | Monitor, address if problem | Deferred |

## Open Questions (for story-agent)
- What's the max length for guild name? Tag?
- Can guild names contain spaces/special characters?
- Where does guild chat appear in the UI? New tab? Existing chat?

## Success Indicators
- [ ] Players can create a guild with 2 others
- [ ] Guild tag appears on member nameplates
- [ ] Members can chat in guild channel
- [ ] Leader can invite, kick, and transfer leadership
- [ ] Guild persists even with 1 member
- [ ] Profanity filter blocks offensive names

*Note: Story-agent will refine these into formal, testable acceptance criteria.*
```

### User Reviews

```
User: This looks good. Perfect. Let's ship it to the pipeline.
```

---

## Afternoon: Handoff to Pipeline

### Save the Artifact

The brainstorm artifact is saved:

```
artifacts/brainstorms/guild-system-v1.md
```

### Human Gate

The user (who just brainstormed) can directly approve by updating the frontmatter:

```yaml
---
status: ready-for-stories
created: 2024-01-15
updated: 2024-01-15
tags: [enhancement, social, player-request]
priority: normal
---
```

Or a PO can review artifacts with `status: backlog` and approve.

---

## The TDD Pipeline Takes Over

From [peer-agent-scenario](./peer-agent-scenario.md):

### Story Agent Claims the Artifact

```
[TRIGGER] Artifact with status: ready-for-stories detected

story-agent starts new chat:
EFFORT: Write user stories for guild-system-v1
MY CONTEXT: Brainstorm artifact (guild-system-v1.md)
```

The story-agent reads the brainstorm artifact. It transforms **success indicators** into **formal user stories with acceptance criteria**:

```markdown
---
status: ready-for-tests
created: 2024-01-16
source: artifacts/brainstorms/guild-system-v1.md
---

# User Stories: Guild System (v1)

## Story: Create a Guild

As a player with 2 friends online,
I want to create a guild with them,
So that we have a formal group identity.

### Acceptance Criteria
- Given I have invited 2 players to found a guild
- And both players have accepted
- When the guild is created
- Then all 3 players are members
- And I am the guild leader
- And the guild appears in all members' guild panels
- And the guild name passes profanity filter validation

### Acceptance Criteria (Edge Case)
- Given I try to create a guild with a name containing profanity
- When I submit the name
- Then creation is blocked
- And I see an error: "Guild name not allowed"
```

Story-agent produces: `artifacts/stories/guild-system-v1.md`
Story-agent updates brainstorm artifact: `status: in-progress-stories` → `status: stories-complete`

### Test Architect Claims It

```
[TRIGGER] Story artifact with status: ready-for-tests detected

test-architect starts new chat:
EFFORT: Write failing tests for guild-system-v1
MY CONTEXT: Brainstorm artifact + story artifact
```

Test architect writes executable tests that currently fail:

```python
def test_guild_creation_requires_three_founders():
    player1 = create_player()
    player2 = create_player()
    player3 = create_player()

    guild = Guild.create(
        name="Wolves",
        tag="WOLF",
        founders=[player1, player2, player3]
    )

    assert guild.member_count == 3
    assert guild.leader == player1
    assert player1.guild == guild
    assert player2.guild == guild
    assert player3.guild == guild

def test_guild_creation_fails_with_two_founders():
    player1 = create_player()
    player2 = create_player()

    with pytest.raises(InsufficientFoundersError):
        Guild.create(
            name="Wolves",
            tag="WOLF",
            founders=[player1, player2]
        )

def test_guild_tag_appears_on_nameplate():
    guild = create_guild_with_members(3)
    member = guild.members[0]

    nameplate = member.get_nameplate_display()

    assert f"[{guild.tag}]" in nameplate
```

Test architect produces: `artifacts/tests/guild-system-v1.md` (or actual test files)
Test architect updates: `status: ready-for-dev`

### Dev Agent Implements

```
[TRIGGER] Artifact with status: ready-for-dev detected

dev-agent starts new chat:
EFFORT: Implement guild system to pass tests
MY CONTEXT: All artifacts + test files + relevant codebase
```

Dev agent writes code until tests pass:

```
18/18 tests passing
```

Dev agent updates: `status: ready-for-review`

### Review and QA

The pipeline continues through reviewer-agent and qa-agent as described in peer-agent-scenario.

---

## What Made This Work

### 1. Conversation as Refinement
The back-and-forth naturally surfaced edge cases, risks, and decisions. The AI asked questions the user hadn't considered.

### 2. AI Challenges, User Decides
AI pushed back on assumptions (succession, multi-guild) but the user made final calls. AI advises, human decides.

### 3. Artifact Captures Decisions
The .md artifact records not just WHAT was decided but WHY (the "Reasoning" column). Future readers understand the context.

### 4. Clean Handoff
The brainstorm artifact contains everything story-agent needs. No conversation history required—just the artifact.

### 5. Self-Contained State
The artifact carries its own status in frontmatter. No external system to sync. Git tracks history.

### 6. TDD Pipeline Unchanged
The pipeline doesn't care how the brainstorm happened. It just needs an artifact with the right status. Solo, roundtable, or collaborative—same pipeline.

---

## Comparison: All Brainstorm Scenarios

| Scenario | Best For | Output |
|----------|----------|--------|
| Solo Brainstorm | Clear idea, one person refining | brainstorm artifact |
| Roundtable | Controversial/risky ideas, need debate | synthesis + brainstorm artifact |
| Problem-First | Unknown solution, diagnostic work | discovery report + brainstorm artifact |
| User-AI Collaborative | Rough idea, need exploration | brainstorm artifact |

All produce a **brainstorm artifact** (with frontmatter status) that feeds the same TDD pipeline.

---

## Artifacts Produced

```
artifacts/brainstorms/guild-system-v1.md    ← The artifact (with frontmatter status)
```

The brainstorm artifact is the only required output. Kanban state lives in the frontmatter.

---

## Connection to TDD Pipeline

```
Brainstorm Phase                    TDD Pipeline
      ↓                                  ↓
  Conversation
      ↓
  Brainstorm Artifact (.md)  ──────→  story-agent polls status: ready-for-stories
      ↓                                  ↓
  (status updated)                  story-agent claims (status: in-progress-stories)
                                         ↓
                                    story-agent → test-architect → dev-agent → ...
```

The brainstorm artifact is the **input** to the TDD pipeline. What happens before (solo, roundtable, collaborative) doesn't matter—the pipeline consumes artifacts, not conversations.
