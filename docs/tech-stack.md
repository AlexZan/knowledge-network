# Tech Stack

## Philosophy

**Anti-monolith**: Small, composable pieces over large frameworks.

**Open source**: Community accessible, forkable, modifiable.

**Hackable primitives**: Users can modify tools, instructions, schemas without rebuilding.

---

## Decision

**Language**: Python 3.11+

**Rationale**:
- Lowest barrier to modify (most devs can hack Python)
- AI ecosystem native (transformers, embeddings, RAG all Python-first)
- Pydantic schemas are readable/editable
- Fast iteration for prototyping
- Can optimize hot paths later if needed

---

## Architecture Layers

```
LAYER           IMPLEMENTATION      HACKABLE?
──────────────────────────────────────────────
Instructions    Markdown files      ✓ Just edit text
Schemas         Pydantic models     ✓ Readable Python
Tools           Python functions    ✓ Drop in new tools
CLI             Python (typer)      ✓ Extend commands
Embeddings      sentence-transform  ✓ Swap models
Storage         SQLite + JSON       ✓ Inspectable
Config          YAML                ✓ Edit settings
```

---

## Dependencies

| Package | Purpose | Why |
|---------|---------|-----|
| `litellm` | Multi-provider LLM calls | 100+ providers, one interface |
| `typer` | CLI framework | Modern, type-hinted, auto-docs |
| `pydantic` | Data structures | Validation, serialization |
| `sentence-transformers` | Embeddings | Local, no API cost |
| `chromadb` | Vector storage | Simple, local, good enough |
| `rich` | Terminal UI | Pretty output, tables, trees |

---

## Model Escalation Tiers

Start cheap, escalate on failure:

| Tier | Models | Cost | Use When |
|------|--------|------|----------|
| **Free** | GLM-4, DeepSeek | $0 | Default starting point |
| **Standard** | Sonnet, GPT-4o | $$ | After 2 failures at free |
| **Expensive** | Opus, o1 | $$$$ | Complex reasoning, last resort |

```python
import litellm

# Same interface, just change the string
response = litellm.completion(
    model="glm-4",  # or "claude-sonnet-4-20250514" or "claude-opus-4-20250514"
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

## User-Hackable Locations

```
~/.oi/
├── config.yaml           # Global settings, model preferences
├── instructions/         # System prompts, agent instructions
│   ├── system.md
│   └── agents/
│       ├── dev-agent.md
│       └── qa-agent.md
├── schemas/              # Pydantic models (if overriding)
├── tools/                # Custom tools (drop-in Python)
│   └── my_tool.py
└── state/                # Artifacts, chat logs (inspectable)
    ├── artifacts.db
    └── logs/
```

**Everything is files**. No hidden databases, no binary blobs, no cloud lock-in.

---

## What We're NOT Using

| Option | Reason Rejected |
|--------|-----------------|
| `openai` SDK | Implies lock-in, litellm is provider-agnostic |
| LangChain | Too heavy, too much abstraction, hard to debug |
| Raw `httpx` | Reinventing the wheel |
| Rust | Harder to modify for average user |
| TypeScript | Another runtime, no advantage for CLI |
| Cloud vector DBs | Cost, lock-in, complexity |

---

## Future Considerations

| Need | Solution | When |
|------|----------|------|
| Web dashboard | TypeScript/React | After core CLI stable |
| Performance hotspots | Rust/PyO3 | If profiling shows need |
| 3D visualization | Three.js/WebGL | Much later |
| Mobile | React Native or PWA | Maybe never |

---

## Example: Adding a Custom Tool

```python
# ~/.oi/tools/my_search.py

def search_jira(query: str) -> list[dict]:
    """Search JIRA for issues matching query."""
    # Your implementation
    return results

# Auto-discovered, available to agents
```

---

## Example: Modifying Agent Instructions

```markdown
<!-- ~/.oi/instructions/agents/dev-agent.md -->

# Dev Agent

You are a development agent focused on writing code.

## Rules
- Never modify tests
- Always run tests after changes
- Escalate after 2 failures

## Tools Available
- read_file
- write_file
- run_tests
- my_search  <!-- custom tool auto-loaded -->
```

---

## Storage Strategy

| Data | Format | Location | Why |
|------|--------|----------|-----|
| Artifacts | SQLite | `~/.oi/state/artifacts.db` | Queryable, single file |
| Chat logs | JSONL | `~/.oi/state/logs/*.jsonl` | Appendable, streamable |
| Embeddings | ChromaDB | `~/.oi/state/vectors/` | Local, no API |
| Config | YAML | `~/.oi/config.yaml` | Human-editable |
| Instructions | Markdown | `~/.oi/instructions/` | Just text |

---

## Applications: Configurations of Primitives

The primitives are domain-agnostic. Applications are configurations for specific use cases.

```
~/.oi/
├── applications/
│   ├── coding/                    # TDD pipeline for development
│   │   ├── agents/
│   │   │   ├── dev-agent.md
│   │   │   ├── test-architect.md
│   │   │   ├── qa-agent.md
│   │   │   └── director-agent.md
│   │   ├── tools/
│   │   │   └── run_tests.py
│   │   └── config.yaml            # coding-specific settings
│   │
│   ├── research/                  # Different agents, same primitives
│   │   ├── agents/
│   │   │   ├── search-agent.md
│   │   │   └── summarize-agent.md
│   │   └── config.yaml
│   │
│   └── writing/                   # Yet another configuration
│       ├── agents/
│       │   ├── outline-agent.md
│       │   └── editor-agent.md
│       └── config.yaml
```

**First target**: Coding assistant with TDD pipeline (dev-agent, test-architect, QA, director).

**Key insight**: The primitives ARE the product. Applications are just configurations.

See [thesis.md](thesis.md) for the full vision.
