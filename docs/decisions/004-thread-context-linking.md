# Decision 004: Thread Context via Conclusion IDs

## Context

Threads can be follow-ups to previous discussions. Without context, messages like "What about water?" are meaningless - water in relation to what?

## Problem

How do we make threads self-contained and understandable without modifying the chat history?

## Options Considered

1. **Thread linking** - Store `related_conclusion_ids`, traverse links to build context on read
2. **Context field** - Store text snapshot of relevant conclusions when thread starts
3. **Message expansion** - Rewrite ambiguous messages to be self-contained

## Decision

Use **conclusion ID linking** (variant of option 1, but with simple lookup not traversal).

```python
class Thread:
    context_conclusion_ids: list[str]  # IDs of conclusions that provide context
```

## Reasoning

**Option 3 rejected**: Modifying chat history breaks trust. The history should be a faithful record of what was actually said, not a cleaned-up version.

**Option 2 rejected**: Duplicates data that already exists in conclusions.

**Option 1 chosen** because:
- Conclusions already exist as standalone knowledge - reuse them
- No data duplication
- Simple ID lookup (O(1) with dict), not chain traversal
- Thread remains a faithful record of what was said
- Context is recoverable by looking up the linked conclusions

## Example

```json
{
  "id": "thread-2",
  "messages": [{"role": "user", "content": "What about water?"}],
  "context_conclusion_ids": ["abc123"]
}
```

Look up `abc123` → "Plants require sunlight for photosynthesis..."

Now "What about water?" makes sense: it's asking about water in the context of plant biology.
