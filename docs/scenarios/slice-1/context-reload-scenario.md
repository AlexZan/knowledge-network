# Slice 1 Scenario: Context Reload Without Full Raw Log

A walkthrough showing how the manifest + artifacts provide compressed context, enabling quick reloading without parsing the entire raw conversation history.

---

## The Session

Yesterday, I had a long debugging session about authentication issues. We produced three artifacts: one about middleware order, one about token expiry configuration, and one about database connection pooling. The raw log is over 200 exchanges—probably 15,000 tokens if loaded verbatim.

Today, I start a new conversation. I type: "I want to continue working on the auth system. Remind me what we figured out yesterday."

The AI doesn't load the full raw log. Instead, it reads the manifest from yesterday's session and responds:

"Yesterday's auth debugging session had three segments:

1. **Middleware Order Fix** (lines 1-67): You fixed intermittent 401 errors by reordering middleware so token validation happens before database operations. Artifact: `debugging/auth-middleware-order.md`

2. **Token Expiry Configuration** (lines 68-134): You adjusted token expiry from 24 hours to 1 hour for security, and implemented refresh tokens. Artifact: `debugging/token-expiry-config.md`

3. **Connection Pool Tuning** (lines 135-203): You increased the database connection pool size to 20 and enabled connection keep-alive to reduce latency. Artifact: `debugging/db-pool-tuning.md`

I've loaded all three artifacts for context. What would you like to focus on today?"

I notice the AI gave me compressed summaries, not the full verbatim exchanges. Each summary is linked to a specific line range if I want details. The artifacts are already in context.

I respond: "The token expiry change is causing issues. Users are getting logged out too quickly. I want to adjust the refresh flow."

The AI replies: "Got it. You're building on segment 2 from yesterday. Here's what the artifact says about the current refresh token setup..." and proceeds to reference the `token-expiry-config.md` artifact.

We discuss the problem. The refresh token flow requires users to re-authenticate every hour, but mobile users are complaining because the app doesn't handle refresh smoothly in the background. We explore solutions: extend the refresh token lifetime to 7 days, implement silent refresh on the client side, and keep the access token at 1 hour.

After working through the details, I say: "Okay, updated approach: 1-hour access token, 7-day refresh token, client handles silent refresh in background."

The AI confirms: "That resolves the mobile UX issue while keeping short-lived access tokens for security. Should I create a new artifact for this update?"

I confirm: "Yes, but link it to yesterday's token expiry artifact since this builds on that decision."

The AI creates `debugging/token-refresh-flow-update.md` with a `source` field pointing to both yesterday's chat and the previous artifact. The manifest for today's session now has one segment linking to the new artifact.

I check the new artifact and see it references `related_to: debugging/token-expiry-config.md` in the frontmatter. If I ever need to trace the evolution of this decision, the artifact chain is explicit.

---

## What I Observed

**Manifest-Based Context Loading**
- AI loaded yesterday's manifest instead of 200+ raw exchanges
- Manifest provided segment summaries with line ranges
- Token cost: ~500 tokens (manifest) vs ~15,000 tokens (full raw log)
- Context reconstruction took seconds, not minutes

**Artifacts as Portable Context**
- Each artifact from yesterday was already self-contained
- AI loaded artifact files directly without needing the full conversation
- Artifacts contain enough context to understand the decision without re-reading the chat

**Selective Expansion to Raw Log**
- If I had asked "What exactly did I say about connection pooling?", the AI could expand segment 3 (lines 135-203)
- Manifest line ranges enable precise jumping into the raw log
- Full verbatim is available but not required for normal context loading

**Cross-Session Artifact Links**
- New artifact explicitly linked to the previous artifact via `related_to` field
- The artifact chain documents evolution: token expiry → refresh flow update
- Traceability without requiring full chat history

**Segments Enable Focused Discussion**
- AI identified I was building on segment 2 (token expiry)
- Didn't waste tokens loading irrelevant segments (middleware, connection pool)
- Manifest acts as an index for targeted context retrieval

**No Token Waste on Dead Ends**
- The raw log includes exploratory threads that didn't lead anywhere
- Manifest summaries skip the dead ends, capture only the resolutions
- Token budget spent on conclusions, not raw exploration logs

**Session Continuity Without Session Persistence**
- Yesterday's session concluded, but today's session seamlessly continues
- No "let me reload the context" delay
- Manifest + artifacts bridge sessions transparently

---

## What I Didn't Have To Do

- No "scroll up and read yesterday's conversation" manual context loading
- No summarizing yesterday's findings in my own words
- No searching for "where did we decide about token expiry?"
- No copying/pasting from yesterday's chat into today's chat
- No maintaining separate context notes between sessions
- No asking "can you remind me what we concluded?" with vague results
- No paying token cost for the full 15,000-token raw log
- No managing file paths manually—AI knows where artifacts are
- No manually linking the new artifact to the old one—frontmatter handles it

---

## Technical Details (Implementation View)

For implementers, this scenario demonstrates:

**Yesterday's Manifest (Reference for AI):**
```yaml
chat_id: "debug_auth_20240117"
started: "2024-01-17T10:00:00Z"
updated: "2024-01-17T16:30:00Z"
status: concluded

segments:
  - id: seg_1
    summary: "Fixed intermittent 401 errors via middleware reordering"
    raw_lines: [1, 67]
    artifacts: ["debugging/auth-middleware-order.md"]

  - id: seg_2
    summary: "Adjusted token expiry to 1 hour, implemented refresh tokens"
    raw_lines: [68, 134]
    artifacts: ["debugging/token-expiry-config.md"]

  - id: seg_3
    summary: "Tuned database connection pool for latency reduction"
    raw_lines: [135, 203]
    artifacts: ["debugging/db-pool-tuning.md"]
```

**Today's Session Context Load:**
1. User asks for context from yesterday
2. AI reads `debug_auth_20240117/manifest.yaml`
3. AI loads all artifacts referenced in segments
4. AI returns compressed summary (manifest + artifact content)
5. Total tokens: ~500 (manifest) + ~300 per artifact = ~1400 tokens
6. Avoids loading raw.jsonl (~15,000 tokens)

**New Artifact with Linkage:**
```yaml
---
status: resolved
created: 2024-01-18T09:30:00Z
updated: 2024-01-18T09:30:00Z
tags: [debugging, auth, token-refresh]
source: chats/debug_auth_20240118
related_to: debugging/token-expiry-config.md
---

# Token Refresh Flow Update

## Context
Builds on previous token expiry decision (1-hour access tokens, see `token-expiry-config.md`).

## Problem
Mobile users logged out too frequently. Client doesn't handle refresh smoothly in background.

## Updated Solution
- Access token: 1 hour (unchanged)
- Refresh token: 7 days (extended from implicit 1 hour)
- Client implements silent background refresh before access token expiry

## Outcome
Mobile UX improved while maintaining short-lived access token security.
```

**Today's Manifest (After New Conclusion):**
```yaml
chat_id: "debug_auth_20240118"
started: "2024-01-18T09:00:00Z"
updated: "2024-01-18T09:30:00Z"
status: active

segments:
  - id: seg_1
    summary: "Loaded context from yesterday's auth session (3 artifacts)"
    raw_lines: [1, 8]
    artifacts: []

  - id: seg_2
    summary: "Resolved mobile logout issue by extending refresh token lifetime to 7 days"
    raw_lines: [9, 42]
    artifacts: ["debugging/token-refresh-flow-update.md"]
```

**Context Budget Calculation:**

| Approach | Token Cost | What's Loaded |
|----------|------------|---------------|
| Full Raw Log | ~15,000 | Every exchange verbatim |
| Manifest + Artifacts | ~1,400 | Segment summaries + resolution documents |
| Savings | ~13,600 (90%) | Only conclusions, not exploration paths |

**Selective Expansion (If Needed):**
- User: "What exactly did I say about connection pooling?"
- AI: Reads lines 135-203 from `debug_auth_20240117/raw.jsonl`
- Returns verbatim exchanges from that segment
- Total expansion cost: ~2,000 tokens for one segment
- Still cheaper than loading all 15,000 tokens

**Artifact Chain Traversal:**
```
token-expiry-config.md
  ↓ related_to
token-refresh-flow-update.md
  ↓ (future)
token-refresh-mobile-polish.md
```

AI can traverse `related_to` links to understand decision evolution without loading all raw logs.

**Key Implementation Insight:**
The manifest is the index. Artifacts are the conclusions. Raw log is the archive. Normal context loading uses manifest + artifacts. Raw log expansion is on-demand only.
