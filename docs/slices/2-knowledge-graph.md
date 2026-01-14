# Slice 2: Cross-Session Knowledge Graph

Build on Slice 1 to create a persistent, queryable knowledge network.

---

## Goal

Conclusions from different sessions connect to form a growing knowledge graph.

---

## Prerequisites

- Slice 1 complete (conclusion tracking works)

---

## Key Features

### 1. Conclusion Connections

Detect relationships between conclusions:

```
Conclusion A: "Validate tokens before database queries"
Conclusion B: "Sanitize user input before SQL execution"
         ↓
Detected: Both are instances of "validate at trust boundaries"
         ↓
Create link: A ←supports→ [new abstraction] ←supports→ B
```

### 2. Automatic Linking

When a new conclusion is created:
- Compare against existing conclusions
- Detect: supports, contradicts, generalizes, specifies
- Create edges in the graph

### 3. Knowledge Queries

```
> /query "What do I know about input validation?"

Results:
- C001: Validate tokens before database queries (3 supports)
- C002: Sanitize SQL inputs (2 supports)
- C003: Never trust client-side validation (1 support)

Abstraction detected: "Validate at trust boundaries"
```

### 4. Context Enhancement

When starting a new conversation, relevant prior conclusions are automatically loaded based on topic detection.

---

## Data Structures

### Extended Conclusion

```
{
  ...slice1_conclusion,
  connections: [
    { target_id: string, type: "supports" | "contradicts" | "generalizes" | "specifies" }
  ],
  abstraction_level: number,  // 0=specific, higher=more abstract
  query_embedding: vector     // for semantic search
}
```

### Knowledge Graph

```
{
  conclusions: [Conclusion],
  edges: [
    { from: string, to: string, type: string, strength: number }
  ],
  abstractions: [
    { id: string, content: string, derived_from: [conclusion_ids] }
  ]
}
```

---

## Technical Considerations

- **Embedding storage**: For semantic search across conclusions
- **Graph queries**: Finding related conclusions efficiently
- **Abstraction detection**: LLM task to identify patterns across conclusions

---

## Success Criteria

1. [ ] Conclusions from session A are available in session B
2. [ ] Related conclusions are automatically linked
3. [ ] Can query the knowledge base semantically
4. [ ] New sessions get relevant prior context automatically
5. [ ] Abstractions emerge from multiple specific conclusions

---

## Out of Scope (Future Slices)

- Confidence scoring from graph topology
- Privacy layers / sharing
- Conflict resolution between conclusions
