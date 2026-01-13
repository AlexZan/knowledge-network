# Self-Evolving Schemas (Future)

> Brainstorm for making the system learn HOW to store knowledge, not just WHAT.

## The Idea

Instead of hardcoded artifact types (effort, fact, event), the LLM proposes new types as it encounters new patterns. Like a "human-readable neural network" that develops structure over time.

## Open Questions

### 1. How does LLM propose a new type?
- Explicitly: "I haven't seen this pattern before, I suggest creating a 'recipe' type"
- Silently: Creates it, we review later
- Hybrid: Proposes, user approves

### 2. What defines an artifact type?
```yaml
type: recipe
description: "Step-by-step instructions for making something"
fields:
  - ingredients: list
  - steps: list
  - prep_time: string
expires: false
```

### 3. Where do type definitions live?
- `~/.oi/schemas/` folder?
- Inside state.json itself?
- Separate schemas.json?

### 4. How to prevent type explosion?
- LLM checks "is this really new, or does it fit existing type?"
- Types need minimum usage count to persist
- Periodic consolidation: "these 3 types are similar, merge?"

### 5. How does interpretation prompt adapt?
- Dynamically built from current schema definitions
- Each type definition includes its own interpretation hints

### 6. Is the schema itself an artifact?
```json
{
  "artifact_type": "schema_definition",
  "summary": "recipe - step-by-step instructions for making something",
  "fields": ["ingredients", "steps", "prep_time"]
}
```

This would make the system truly self-describing.

## Prerequisite

First implement **configurable schemas (B)** - user defines types in a config file. This creates the foundation for self-evolving schemas.

## Status

Parked for later. Focus on configurable schemas first.
