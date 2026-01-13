# Scenarios & Artifact Analysis

## Purpose
Analyze each scenario to determine what artifact type (if any) should be created.

---

## Scenario 1: Recency Query
**User:** "Where did we leave off?"

**Context:** User opens new session after working on game dev project yesterday.

**Expected AI behavior:** Scan recent artifacts, respond with summary of recent activity.

**Artifact created from THIS exchange?** No - this is a query, not new work.

**Suggested artifact type:** `query` (or none - just a lookup)

---

## Scenario 2: Fresh Start - New Idea
**User:** "I have an idea for a multiplayer mode"

**Context:** User starting something new.

**Expected AI behavior:** Engage with the idea, maybe ask clarifying questions.

**Artifact created?** Yes - this is the START of an effort.

**Suggested artifact type:** `effort` (open)
```json
{
  "type": "effort",
  "status": "open",
  "summary": "Exploring multiplayer mode idea",
  "detail": "User proposed adding multiplayer, type TBD"
}
```

---

## Scenario 3: Search Query
**User:** "What was that bug we fixed with the player falling through floors?"

**Context:** User trying to recall past work.

**Expected AI behavior:** Search artifacts for "player" + "floor" or "collision", return match.

**Artifact created from THIS exchange?** No - this is a lookup.

**Suggested artifact type:** `query` (or none)

---

## Scenario 4: Continuation Without Conclusion
**Session 1:**
- User: "I'm thinking about adding multiplayer"
- AI: "Interesting! What kind - co-op or competitive?"
- User: "Not sure yet, let me think about it"
- [Session ends - NO CONCLUSION]

**Session 2:**
- User: "Okay I decided - let's do co-op"

**Expected AI behavior:** Know about the open effort, continue it.

**Artifact from Session 1?** Yes - open effort
```json
{
  "type": "effort",
  "status": "open",
  "summary": "Deciding on multiplayer type (co-op vs competitive)"
}
```

**Artifact from Session 2?** Yes - conclusion/resolution
```json
{
  "type": "conclusion",
  "summary": "Decided on co-op multiplayer",
  "resolves_effort": "<effort_id>"
}
```

---

## Scenario 5: Emotional/Personal Context
**User:** "I'm frustrated, this bug has taken 3 days"
*[AI helps, bug gets fixed]*

**Later:** "Remember that nightmare bug?"

**Expected AI behavior:** Connect "nightmare bug" to the 3-day frustrating bug.

**Artifact created?** Yes - effort with emotional context
```json
{
  "type": "effort",
  "status": "resolved",
  "summary": "Fixed rendering bug (3-day struggle)",
  "tags": ["frustrating", "nightmare"],
  "time_spent": "3 days",
  "conclusion": "Fixed by updating shader cache"
}
```

---

## Scenario 6: Learning/Education
**User:** "Explain quantum entanglement to me"
*[AI explains, user asks follow-ups, eventually understands]*

**Artifact created?** Yes - learning effort
```json
{
  "type": "effort",
  "category": "learning",
  "status": "resolved",
  "summary": "User learned quantum entanglement",
  "conclusion": "Key insight: measurement collapses entangled states simultaneously"
}
```

---

## Scenario 7: Simple Q&A (Public Knowledge)
**User:** "What's the capital of France?"
**AI:** "Paris"
**User:** "Thanks"

**Artifact created?** Maybe not - or very lightweight.

**Analysis:**
- Public knowledge, no value added
- BUT if referenced frequently, might be worth keeping
- Could start with ref_count=0, expire if never referenced

**Suggested artifact type:** `fact` (lightweight, can expire)
```json
{
  "type": "fact",
  "summary": "Capital of France is Paris",
  "ref_count": 0,
  "expires": true
}
```

**Alternative:** Don't create artifact, only raw chat log.

---

## Scenario 8: Casual Chat
**User:** "How's it going?"
**AI:** "Good! How are you?"
**User:** "Tired, long day"
**AI:** "Hope you get some rest"

**Artifact created?** Probably not - no goal, no resolution.

**Analysis:**
- No effort, no knowledge gained
- "User was tired on Oct 8th" - relevant if referenced later
- Could capture as lightweight event, expire if unreferenced

**Suggested artifact type:** `event` (lightweight, expires fast)
```json
{
  "type": "event",
  "summary": "Casual check-in, user mentioned being tired",
  "ref_count": 0,
  "expires": true
}
```

**Alternative:** Raw chat only, no artifact.

---

## Scenario 9: Creative Writing
**User:** "Help me write a short story about a robot"
*[Multiple sessions, drafts, revisions]*

**Artifact created?** Yes - hierarchical efforts
```json
{
  "type": "effort",
  "status": "open",
  "summary": "Writing robot short story",
  "children": [
    {"type": "effort", "summary": "Developed main character Axis", "status": "resolved"},
    {"type": "effort", "summary": "Wrote first draft (2000 words)", "status": "resolved"},
    {"type": "effort", "summary": "Revising ending", "status": "open"}
  ]
}
```

---

## Scenario 10: Planning
**User:** "Help me plan a trip to Japan"

**Artifact created?** Yes - hierarchical effort
```json
{
  "type": "effort",
  "category": "planning",
  "summary": "Planning Japan trip",
  "children": [
    {"summary": "Decided dates: April 10-20", "status": "resolved"},
    {"summary": "Book flights", "status": "open"},
    {"summary": "Plan itinerary: Tokyo 3d, Kyoto 4d", "status": "resolved"}
  ]
}
```

---

## Summary: Artifact Types

| Type | When to Use | Expires? |
|------|-------------|----------|
| `effort` | Goal-oriented work (open or resolved) | No |
| `conclusion` | Resolution/knowledge from an effort | No |
| `fact` | Simple Q&A, public knowledge | Yes (if unreferenced) |
| `event` | Casual exchange, context that might matter | Yes (fast) |
| `query` | User asking to look something up | No artifact needed |

---

## Open Questions

1. Should `fact` and `event` even create artifacts, or just stay in raw chat?
2. How does the LLM decide which type to use?
3. What's the expiration policy? Time-based? Reference-based? Both?
4. Should hierarchical efforts be nested or linked by ID?

---

## Context Building Scenarios

These scenarios inform how the AI retrieves context using tools.

### Scenario: State Query
**User:** "What are we working on?"

**AI behavior:** Calls `get_open_objectives()` + `get_recent_resolved(5)`

**Response:** "You have 3 open objectives for Project X:
1. Fix login bug
2. Add dark mode
3. Refactor auth

Recently finished: Payment integration (2 days ago), User onboarding (last week).

Want to continue one of these?"

**Artifact created?** No - just a lookup.

---

### Scenario: Continue Last
**User:** "Let's continue from where we left off"

**AI behavior:** Calls `get_open_objectives()`, sorts by `updated` timestamp, picks most recent.

**Key insight:** Need `updated` timestamp, not just `created`. Most recently *active* objective, not most recently *created*.

**Response:** "Last time we were working on [most recent objective]. Want to continue?"

**Artifact created?** No - just retrieval + confirmation.

---

### Scenario: Topic Query
**User:** "My skin condition is getting worse"

**AI behavior:** Calls `search_artifacts("health skin condition")`, finds related objective (even if resolved).

**Response:** Uses history: "Last time we tried cream X and it worked for a bit. What's happening now?"

**Artifact created?** Maybe - updates existing objective or creates child effort.

---

### Scenario: Specific Search
**User:** "What was that bug with the player falling through floors?"

**AI behavior:** Calls `search_artifacts("bug player floor collision")`. If not found, calls `search_chatlog("floor falling")`.

**Response:** Returns match with context.

**Artifact created?** No - just lookup.

---

## Context Building Architecture

The AI has retrieval tools available and decides which to use:

```
Tools:
├── get_open_objectives()        # Current work
├── get_recent_resolved(n)       # Recently finished
├── search_artifacts(query)      # Find by tags/keywords/summary
└── search_chatlog(query)        # Raw history fallback

Instructions:
"Use retrieval tools based on what user is asking.
State queries → get open objectives.
Topic queries → search by relevance.
You can combine tools."
```

This is standard tool use - one LLM call, AI decides what context it needs.
