# Chat CLI - Effort Brief

## Core Value Proposition

**Users can have much longer conversations than traditional AI tools** because the system extracts artifacts when conclusions are reached, keeping active context small while knowledge accumulates.

Traditional AI: `Chat grows → Token limit → Truncate/summarize → Information loss`

This system: `Chat grows → Artifacts extracted → Context stays small → Nothing lost`

## Slice 1 Scope

From [01-core-capture.md](../../docs/slices/01-core-capture.md):

- Single artifact type: **effort** (with status/resolution)
- Compact on **conclusion only** (when user accepts/resolves)
- No sub-efforts, no token limit fallback
- Two-log model: raw.jsonl (verbatim) + manifest.yaml (summary + artifact links)

## What Slice 1 Proves

- Conclusion-triggered compaction works
- Artifacts can replace verbose exchanges
- Context stays small while knowledge persists
- Cross-session memory via artifacts

## Key Mechanism

From [refined-chat-model.md](../../docs/brainstorm/refined-chat-model.md):

```
User: "I'm getting a 401 error"
  → No artifact yet (conversation ongoing)

[... back and forth debugging ...]

User: "Oh! Token was expired, works now!"
  → DETECTOR: User accepted solution
  → COMPACT: Extract effort + resolution
  → SAVE: Artifact persists for future sessions
```

## Not In Scope (Slice 1)

- Fact/event artifact types
- Sub-efforts
- Token limit fallback
- Cross-chat search
- Fork/continue flow
