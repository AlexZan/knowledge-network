# Slice 1a Scenario: A Debugging Session

A complete walkthrough of the slice 1a experience.

---

## The Session

I open my terminal and run `oi`. A simple prompt appears, ready for input.

I type: "I'm getting a 401 error when calling the API. What could cause this?"

The AI responds with a detailed explanation about authentication - expired tokens, invalid credentials, missing headers. It suggests checking if my token has expired.

I reply: "Ah, you're right - the token was expired. Refreshing it fixed the issue. Thanks!"

The moment I send that message, something happens. The system recognizes I've resolved the issue. I see:

```
[effort:resolved] Debug 401 API error
  => Token was expired, refresh fixed it
[Tokens: 1,247 raw → 68 compacted | Savings: 95%]
```

The verbose back-and-forth about the 401 error has been compressed into an effort artifact with its resolution. I can see exactly how many tokens were saved.

Now I have a different question: "My database queries are running slowly. Any ideas?"

The AI starts helping me debug the database issue. We go back and forth - it suggests indexing, I say that's not it, it suggests connection pooling, I push back saying I already have that configured. Finally it asks about my query patterns and identifies an N+1 problem.

I respond: "Oh wow, that's exactly it. I was fetching related records in a loop instead of joining. Thanks!"

Again, the system detects my resolution:

```
[effort:resolved] Debug slow database queries
  => N+1 problem - fetching in loop instead of joining
[Tokens: 2,891 raw → 94 compacted | Savings: 97%]
```

Now I'm curious if the system actually remembers. I ask: "So between the auth issue and the database thing, which was easier to fix?"

The AI responds referencing both effort artifacts - the token refresh was a quick fix, while the N+1 required refactoring queries. It remembers both issues without me re-explaining them, and without loading the full conversation history.

I exit with `exit`. The program closes cleanly.

---

Later that evening, I run `oi` again. The prompt appears, and I type: "What were those two issues I was debugging earlier?"

The AI immediately recalls: the 401 token expiration and the N+1 database problem. My effort artifacts persisted. I'm back in the same conversation, picking up where I left off.

I continue debugging a new issue, and the cycle continues - questions, answers, effort artifacts extracted, tokens saved.

---

## What I Observed

1. Starting the CLI was instant - just a prompt
2. Conversation flowed naturally - no special commands needed
3. When I resolved an issue, effort artifacts appeared automatically
4. Token savings were shown after each artifact extraction
5. Later questions could reference earlier effort artifacts
6. Exiting and restarting continued the same conversation
7. The AI knew resolved efforts without me repeating them

## What I Didn't Have To Do

- No commands to memorize
- No manual "save" or "resolve" actions
- No managing separate chats or sessions
- No re-explaining context after restarting
