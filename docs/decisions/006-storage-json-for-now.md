# Decision 006: JSON Storage with Network/Thread Split

## Context

Single JSON file won't scale forever. Discussed alternatives: file sharding, SQLite, graph databases.

## Decision

Use JSON with a split structure:

```
~/.oi/
├── network.json        # Conclusions + metadata (small, always loaded)
└── threads/
    └── {thread-id}.json  # Individual thread files (loaded on demand)
```

## Reasoning

1. **Conclusions are primary** - The knowledge network is what matters; threads are source material
2. **Network stays small** - Only conclusions and metadata, loads fast every time
3. **Threads isolated** - Old threads don't bloat the main file
4. **Load on demand** - Only active thread loaded; concluded threads stay on disk
5. **Still simple JSON** - Inspectable, debuggable, no dependencies

## Structure

**network.json**:
- `conclusions[]` - The knowledge network
- `active_thread_id` - Reference to current thread (if any)
- `token_stats` - Aggregate statistics

**threads/{id}.json**:
- `id`, `messages[]`, `status`, `conclusion_id`
- `context_conclusion_ids[]` - Links to conclusions that provide context

## Future Options

When scale becomes an issue:

| Option | Pros | Cons |
|--------|------|------|
| SQLite | Built-in, ACID, indexes, FTS | Still a file abstraction |
| Graph DB | Native to knowledge network structure | Added dependency |

## Migration Path

The current model translates directly to relational:
- `conclusions` table
- `threads` table
- `messages` table
- `thread_context` junction table (thread_id, conclusion_id)

When ready, swap `storage.py` implementation - the rest of the system doesn't need to know.
