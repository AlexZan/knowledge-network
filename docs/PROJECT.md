# Project Technical Reference

> Current architecture and code structure. For the vision, see [thesis.md](thesis.md).

## Related Docs

- **Vision**: [thesis.md](thesis.md) - The 5 theses driving this project
- **Roadmap**: [slices/README.md](slices/README.md) - Implementation phases
- **Progress**: [JOURNEY.md](JOURNEY.md) - Where we are, pivots made

---

## Data Model

```
Artifact
├── artifact_type: str     # Dynamic - loaded from schemas/artifact_types.yaml
├── summary: str           # What this is about
├── status: "open" | "resolved" (for types with has_status)
├── resolution: str        # What was decided (for resolved items)
├── tags: list[str]        # For searchability
├── expires: bool          # From schema - whether this type can expire
└── ref_count: int         # For future: expiration based on references
```

## Configurable Schemas

Artifact types defined in YAML (user can override):

```yaml
# src/oi/schemas/artifact_types.yaml (defaults)
# ~/.oi/schemas/artifact_types.yaml (user overrides)
types:
  effort:
    description: "Goal-oriented work"
    has_status: true
    has_resolution: true
    expires: false
  fact:
    description: "Simple Q&A, specific knowledge"
    expires: true
  event:
    description: "Casual exchange, context"
    expires: true
```

## Flow

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

## Key Files

```
src/oi/
├── models.py        # Artifact, ConversationState
├── conversation.py  # build_context(), process_turn()
├── interpret.py     # Agentic interpretation (LLM decides artifacts)
├── chatlog.py       # Raw chat log (append-only JSONL)
├── storage.py       # JSON persistence
├── cli.py           # Command-line interface
├── llm.py           # LiteLLM wrapper
├── prompts/
│   ├── system.md    # Main AI system prompt
│   └── interpret.md # Artifact interpretation rules
└── schemas/
    ├── __init__.py        # Schema loader utilities
    └── artifact_types.yaml # Default type definitions
```

## Storage

```
~/.oi/
├── state.json      # Artifacts (compressed knowledge)
└── chatlog.jsonl   # Raw exchanges (permanent archive)
```

## Key Decisions

See `docs/decisions/` for detailed records.

| Decision | Outcome |
|----------|---------|
| 007-sqlite-storage.md | REVERTED - premature optimization |
| Data model | Artifact-only (not Thread/Conclusion split) |
| Prompts | External markdown files |
| Schemas | Configurable YAML, user can override |
