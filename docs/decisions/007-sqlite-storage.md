# Decision 007: SQLite Storage [REVERTED]

> **Status: REVERTED** - See `docs/lessons-learned/001-premature-optimization.md`
>
> We optimized before proving the concept. The data model evolved significantly
> during brainstorming (threads → efforts → self-evolving artifact schemas).
> Reverted to simple JSON for faster iteration.

---

*Original decision below for reference:*

## Context

We went through several iterations trying to make JSON files work:
1. Single `state.json` - grows unbounded
2. Split `network.json` + `threads/{id}.json` - multiple files, still loads everything
3. JSONL for history - better append, but can't index
4. Individual conclusion files - filesystem as database

Each fix added complexity to work around JSON's fundamental limitation: **you can't do JIT (Just-In-Time) access without loading the whole file**.

## Decision

Use SQLite for all storage.

## Reasoning

SQLite solves everything natively:

| Need | JSON Workaround | SQLite |
|------|-----------------|--------|
| JIT by ID | Individual files or load all | Indexed primary key, O(1) |
| Chronological access | JSONL, read backwards | `ORDER BY timestamp DESC LIMIT N` |
| Append without rewrite | JSONL | Just INSERT |
| Search | Load all, filter in memory | SQL queries, FTS if needed |
| Relationships | Manual ID linking | Foreign keys, JOINs |
| ACID | Manual file handling | Built-in transactions |

Additional benefits:
- **Built into Python** - zero dependencies
- **Single file** - still portable (`oi.db`)
- **Battle-tested** - billions of deployments
- **Future-proof** - can add indexes, FTS, etc.

## Schema

```sql
-- The knowledge network
CREATE TABLE conclusions (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source_thread_id TEXT NOT NULL,
    created TEXT NOT NULL
);

-- Conversation threads
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'open',
    conclusion_id TEXT,
    created TEXT NOT NULL
);

-- Thread context links (many-to-many)
CREATE TABLE thread_context (
    thread_id TEXT NOT NULL,
    conclusion_id TEXT NOT NULL,
    PRIMARY KEY (thread_id, conclusion_id)
);

-- Messages within threads
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

-- Chronological history log
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,      -- 'event' or 'knowledge'
    label TEXT,              -- for events: 'greeting', etc.
    thread_id TEXT,
    conclusion_id TEXT,      -- for knowledge entries
    timestamp TEXT NOT NULL
);

-- Singleton tables for global state
CREATE TABLE token_stats (id INTEGER PRIMARY KEY CHECK (id = 1), ...);
CREATE TABLE state (id INTEGER PRIMARY KEY CHECK (id = 1), active_thread_id TEXT);
```

## JIT Access Patterns

```python
# Load only what you need
conclusion = load_conclusion("abc123")  # Single row lookup

# Recent history (backwards chronological)
recent = load_recent_history(limit=10)  # Last 10 entries

# Active thread only
thread = load_thread(active_thread_id)  # Don't load concluded threads
```

## Migration

The JSON files (`network.json`, `threads/`) are no longer used. The database file is `~/.oi/oi.db`.

## Lesson Learned

Don't patch around fundamental limitations. When you find yourself adding complexity layer after layer, step back and ask if the underlying choice is wrong.
