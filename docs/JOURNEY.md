# Journey Log

> Where we are in implementing the thesis. For humans and agents to regain context.

## Source of Truth

- **Thesis**: [thesis.md](thesis.md) - The 5 core theses and vision
- **Slices**: [slices/README.md](slices/README.md) - Implementation roadmap
- **Technical**: [PROJECT.md](PROJECT.md) - Current architecture and code structure

Read those first. This doc tracks **implementation progress and pivots**.

---

## Current Status: Slice 1 via oi-pipe TDD Pipeline

Pivoted to **dev-first approach** ([decision 008](decisions/008-dev-first-pivot.md)). Building Slice 1 (two-log proof) using the oi-pipe TDD pipeline (`D:/Dev/oi/pipeline/`). Current effort: `efforts/chat-cli/`.

### Pipeline Progress: Test Architect Stage

Generated tests for Stories 4-9 using the pipeline. Key improvements made to oi-pipe during this effort:

| Improvement | What | Why |
|-------------|------|-----|
| Package skeleton | AST-based code context (~500 tokens) | Full source caused pattern-copying; no context caused wrong package names |
| Scenario context | Target architecture injected into prompt | Tests verify new file-based architecture, not existing object model |
| Stub generator | Auto-creates missing functions from test imports | Tests run and fail meaningfully (AssertionError) instead of opaque ImportError |
| SUT rule | Rule #10: every test has an unmocked System Under Test | Eliminated defective tests that compute behavior inline |
| Model switch | deepseek-reasoner for test-architect | Better TDD: invents new interfaces instead of constraining to existing functions |
| `--story N` flag | Extract single story from stories.md | Review tests one story at a time |
| `--experiment` flag | Save to tests/experiments/ by model name | Compare model outputs without overwriting |

### What's Built (Slice 1a Legacy)

### What's Built

| Component | Status | Notes |
|-----------|--------|-------|
| Raw chatlog | ✅ Done | Append-only JSONL, permanent archive |
| Artifact model | ✅ Done | effort/fact/event with status/resolution |
| Agentic interpretation | ✅ Done | LLM decides what artifacts to create |
| Configurable schemas | ✅ Done | YAML-based, user can override |
| External prompts | ✅ Done | Markdown files, editable |
| Context building | ⚠️ Partial | Loads ALL artifacts + last 5 raw exchanges |

### What's Missing (to complete 1a)

- **Relevance-based retrieval** - Currently loads all artifacts, should load only relevant
- **Remove "last 5 exchanges" crutch** - Artifacts should carry continuity, not raw chat
- **Mark exchanges as processed** - So they don't load into context

---

## Implementation Pivots

### Pivot 1: Effort→Conclusion to Flexible Artifacts

**Original**: Thread model with effort→conclusion pairs, triggered by explicit conclusions.

**Pivot**: Single `Artifact` type with dynamic `artifact_type` field. Types: effort (with status/resolution), fact, event. More flexible, captures more patterns.

**Why**: Not everything is an effort→conclusion. Facts ("What's the capital of France?") and events ("I'm tired") don't fit the effort model.

### Pivot 2: Static Context File to Dynamic Assembly

**Original mental model**: A hybrid file with compressed artifacts + unprocessed raw chat.

**Pivot**: Keep raw chatlog and artifacts separate, dynamically assemble context JIT based on the query.

**Why**: Cleaner architecture. Different queries need different context. Scales better.

---

## Architectural Insight: Context Builder as Core

The context builder is the heart of the system:

```
User query → Context Builder → Assembled context → LLM → Response → Interpreter → Artifact
                   ↑
         Retrieval (programmatic) + Selection (agentic)
```

Everything should be a user-extensible primitive:
- `~/.oi/schemas/*.yaml` - artifact types ✅
- `~/.oi/prompts/*.md` - prompts
- `~/.oi/tools/*.py` - custom retrieval/assembly (future)

---

## For Agents

1. **Read [thesis.md](thesis.md)** - understand the vision
2. **Read [slices/README.md](slices/README.md)** - see the roadmap
3. **Read [PROJECT.md](PROJECT.md)** - current technical state
4. **Current work**: Completing Slice 1a - relevance-based retrieval, removing raw chat crutch
5. **Key gap**: Context builder loads everything, should load only relevant artifacts

---

## Open Decisions

- How to determine artifact relevance? (embeddings? keywords? recency? LLM selection?)
- When to fall back to raw chatlog for detail?
- How to handle multi-session efforts? (user returns days later)
