# Journey Log

> Where we are in implementing the thesis. For humans and agents to regain context.

## Source of Truth

- **Thesis**: [thesis.md](thesis.md) - The 5 core theses and vision
- **Slices**: [slices/README.md](slices/README.md) - Implementation roadmap
- **Technical**: [PROJECT.md](PROJECT.md) - Current architecture and code structure

Read those first. This doc tracks **implementation progress and pivots**.

---

## Current Status: Slice 1a (Partial)

We're implementing [Slice 1a: Minimal Conclusion Tracking](slices/slice-1a-minimal.md).

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
