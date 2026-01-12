# Living Knowledge Networks

> A conversation system that compacts based on conclusions, not token limits.

## Where We Came From

### The Problem
Traditional chatbots have a fundamental limitation: they maintain a growing chat log until they hit a token limit, then either truncate or summarize everything. This loses important context and treats all messages as equally important.

### Evolution
1. **Thread/Conclusion model** (v1) - Conversations grouped into threads, each thread extracted to a conclusion when resolved. Problem: What about unresolved discussions?

2. **SQLite storage** (reverted) - Tried to optimize storage before proving the concept. Lesson learned: prove the model first, optimize later.

3. **Artifact model** (current) - Replaced threads/conclusions with a single flexible artifact type. An "effort" can be open or resolved, with a resolution field capturing decisions.

## Where We Are

### Data Model
```
Artifact
├── artifact_type: "effort" | "fact" | "event"
├── summary: str           # What this is about
├── status: "open" | "resolved" (efforts only)
├── resolution: str        # What was decided (resolved efforts)
├── tags: list[str]        # For searchability
├── expires: bool          # Facts/events can expire
└── ref_count: int         # For future: expiration based on references
```

### How It Works
```
User message
    ↓
build_context()  →  [system prompt + artifacts + last 5 exchanges]
    ↓
LLM responds
    ↓
append_exchange()  →  chatlog.jsonl (permanent raw archive)
    ↓
interpret_exchange()  →  LLM decides: create artifact? what type?
    ↓
state.json  →  artifacts only (compressed knowledge)
```

### Key Files
```
src/oi/
├── models.py        # Artifact, ConversationState
├── conversation.py  # build_context(), process_turn()
├── interpret.py     # Agentic interpretation (LLM decides artifacts)
├── chatlog.py       # Raw chat log (append-only JSONL)
├── storage.py       # JSON persistence
├── cli.py           # Command-line interface
├── llm.py           # LiteLLM wrapper
└── prompts/
    ├── system.md    # Main AI system prompt
    └── interpret.md # Artifact interpretation rules
```

### Storage
```
~/.oi/
├── state.json      # Artifacts (compressed knowledge)
└── chatlog.jsonl   # Raw exchanges (permanent archive)
```

## Where We're Going

### Not Yet Implemented

1. **Search/Retrieval** - Currently all artifacts loaded into context. Need:
   - Keyword search through artifacts
   - Relevance-based retrieval
   - Only load relevant artifacts (RAG pattern)

2. **Artifact Linking** - When an effort resolves, it should link to/update the original open effort instead of creating a new one.

3. **Expiration** - Facts/events marked `expires: true` but no expiration logic yet. Need reference counting and cleanup.

4. **User Prompt Overrides** - Prompts in package, no user customization path yet.

### Design Principles

- **Raw chat is permanent** - chatlog.jsonl never deleted, always append
- **Artifacts are compressed knowledge** - Summary of what matters
- **Agentic interpretation** - LLM decides what to capture, not rules
- **Context is JIT** - Load only what's needed, not everything

### Open Questions

1. Should artifacts link to each other? (effort → resolution)
2. How to handle multi-session efforts? (user returns days later)
3. When to expire unreferenced facts/events?
4. How to search when artifacts grow large?

## Key Decisions

See `docs/decisions/` for detailed decision records.

- **007-sqlite-storage.md** - REVERTED - premature optimization
- Artifact-only model chosen over Thread/Conclusion split
- External prompts in markdown for easy editing
