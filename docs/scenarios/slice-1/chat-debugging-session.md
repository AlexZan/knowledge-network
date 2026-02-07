# Slice 1 Scenario: Debugging Session with Continuous Capture

A complete walkthrough of debugging a feature with continuous capture, showing how raw exchanges become structured knowledge through conclusion-triggered compaction.

---

## The Session

I'm debugging why user authentication keeps failing intermittently. I start a conversation with the AI assistant.

I type: "Auth is failing randomly. Users get 401 errors even with valid tokens."

The AI responds with questions about the token validation flow, expiry times, and whether it's happening on specific endpoints. I answer each one, explaining that it's mostly on the `/api/profile` endpoint and tokens are set to expire after 24 hours.

As we go back and forth, I'm not thinking about saving anything. The conversation just flows. The AI suggests checking if tokens are being validated before the database query. I pull up the code and realize—we're hitting the database first, THEN checking the token. If the token expired between the request start and the DB call, we get a weird half-validated state.

I say: "That's it. We need to validate the token before any DB operations."

The AI confirms this makes sense and suggests I update the middleware order. I implement the fix: move token validation to happen before the database middleware. I test it locally and the 401 errors stop happening.

I tell the AI: "Fixed it. Token validation now happens first. The issue was middleware order."

The AI responds: "Great! That's a solid resolution. This follows the principle of validating at trust boundaries before performing expensive operations. Should I capture this as an artifact?"

I say: "Yes, log it."

A moment later, the AI confirms: "Artifact created: `artifacts/debugging/auth-middleware-order.md` with status 'resolved'. The full conversation is preserved in the chat log, and the manifest has been updated with a segment summary and link to the artifact."

I don't have to manually save anything, export the conversation, or reconstruct what we figured out. It's already captured.

---

## What I Observed

**Continuous Capture (No Manual Save)**
- Every exchange was automatically appended to `chatlog.jsonl` as it happened
- No "end of session" prompt asking if I want to save
- No risk of losing the conversation if I closed the window

**Manifest Updated After Each Turn**
- The manifest tracked the evolving conversation in segments
- The first segment summary: "User reported intermittent auth failures, AI explored token validation flow"
- Each manifest update referenced specific line ranges in the raw log (e.g., lines 1-8, 9-16)
- The running summary compressed the exploration without losing the thread

**Conclusion Triggered Artifact Creation**
- When I said "Fixed it. Token validation now happens first," the system detected resolution
- AI offered to create an artifact (didn't assume)
- Artifact created only after I confirmed
- Artifact linked back to the conversation segment

**Manifest Links to Artifact**
- Final segment summary: "Identified root cause (middleware order), implemented fix, verified resolution"
- Segment contains: `artifacts: ["debugging/auth-middleware-order.md"]`
- The manifest now serves as a compressed view of the conversation with artifact links

**Raw Log Remains Untouched**
- Full verbatim record preserved in `chatlog.jsonl`
- If I ever need to review the exact reasoning, it's all there
- Manifest provides the compressed summary for quick context loading

**Artifact Is Independent**
- Saved to `artifacts/debugging/auth-middleware-order.md`
- Contains frontmatter with `status: resolved`, created/updated timestamps, tags
- Can be referenced in future conversations without reloading the entire chat
- Carries its own context (summary of problem + solution)

---

## What I Didn't Have To Do

- No manual "save session" or "export conversation" step
- No copying/pasting conclusions into a separate notes file
- No end-of-session review asking "did we capture everything?"
- No worrying about losing context if the session crashed
- No managing file names or deciding where to save things
- No switching between chat and note-taking apps
- No manually creating the artifact file or writing frontmatter
- No rebuilding the timeline later—the manifest tracks segments with line refs
- No re-explaining this fix in future conversations—the artifact exists

---

## Technical Details (Implementation View)

For implementers, this scenario demonstrates:

**Two-Log Architecture:**
```
~/.oi/chats/{chat_id}/
├── raw.jsonl          # Append-only, full verbatim
└── manifest.yaml      # Updated each turn, segments with summaries
```

**Raw Log Entry (JSONL):**
```jsonl
{"turn": 1, "role": "user", "content": "Auth is failing randomly...", "ts": "2024-01-17T10:00:00Z"}
{"turn": 2, "role": "assistant", "content": "Let's investigate...", "ts": "2024-01-17T10:00:15Z"}
```

**Manifest Structure (YAML):**
```yaml
chat_id: "debug_auth_20240117"
started: "2024-01-17T10:00:00Z"
updated: "2024-01-17T10:45:00Z"
status: concluded

segments:
  - id: seg_1
    summary: "User reported intermittent auth failures, AI explored token validation flow"
    raw_lines: [1, 16]
    artifacts: []

  - id: seg_2
    summary: "Identified root cause (middleware order), implemented fix, verified resolution"
    raw_lines: [17, 32]
    artifacts: ["debugging/auth-middleware-order.md"]
```

**Artifact (Markdown + Frontmatter):**
```yaml
---
status: resolved
created: 2024-01-17T10:45:00Z
updated: 2024-01-17T10:45:00Z
tags: [debugging, auth, middleware]
source: chats/debug_auth_20240117
---

# Auth Middleware Order Fix

## Problem
Intermittent 401 errors on `/api/profile` despite valid tokens.

## Root Cause
Token validation happened AFTER database middleware. If token expired between request start and DB call, created inconsistent state.

## Solution
Reordered middleware: token validation now runs before database operations.

## Outcome
401 errors resolved. Validates at trust boundary before expensive operations.
```

**Capture Loop (Each Turn):**
1. User message → AI response
2. Append to `raw.jsonl`
3. Update `manifest.yaml` with running segment summary
4. If conclusion detected → prompt to create artifact
5. If artifact created → link in manifest segment

**Context Reconstruction:**
- Load manifest for compressed view
- Load specific artifacts referenced in segments
- Optionally expand to raw log for full verbatim if needed
- No full raw log required for normal context loading
