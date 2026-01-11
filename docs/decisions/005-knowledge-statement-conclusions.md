# Decision 005: Conclusions as Knowledge Statements

## Context

Initial implementation summarized conversations:
> "The user asked why plants need water, and the assistant explained it's essential for photosynthesis."

This is meta-information about what happened, not extracted knowledge.

## Decision

Conclusions should be standalone knowledge statements:
> "Water is essential for plants for photosynthesis and nutrient transport."

## Reasoning

1. **Knowledge network, not conversation archive** - We're building a graph of facts, not a log of discussions
2. **Standalone meaning** - Each conclusion should be meaningful without knowing there was a conversation
3. **Reusable context** - Knowledge statements can inform future threads directly
4. **Composable** - Facts can be combined, cross-referenced, and built upon

## Implementation

Updated prompt in `src/oi/prompts/conclusion_extraction.md`:

```
Extract the key fact or conclusion from this conversation.
State it as standalone knowledge - not as a summary of what was discussed.
Be concise - one sentence.
```

## Before/After

| Before (conversation summary) | After (knowledge statement) |
|-------------------------------|----------------------------|
| "The user asked why plants need water, and the assistant explained..." | "Water is essential for plants for photosynthesis and nutrient transport." |
