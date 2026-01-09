# Slice 4: Conflict Resolution

Handle contradictions between conclusions gracefully.

---

## Goal

Detect and resolve conflicts between conclusions without catastrophic forgetting.

---

## Prerequisites

- Slice 3 complete (abstraction layers exist)

---

## Key Features

### 1. Conflict Detection

When new conclusion contradicts existing:

```
Existing: C001 - "Use connection pooling for database performance"
New:      C042 - "Connection pooling caused memory leaks, use single connections"

CONFLICT DETECTED
Type: Truth conflict (factual disagreement)
```

### 2. Conflict Classification

**Truth Conflicts**: Factual disagreements where one is correct
- Resolution: Evidence weighing, newer context may supersede

**Preference Conflicts**: Subjective choices, both valid
- Resolution: Explicit user choice, or coexistence with context tags

### 3. Resolution Workflow

```
Conflict: C001 vs C042

Options:
1. C042 supersedes C001 (new evidence)
2. C001 remains, C042 rejected (C042 was wrong)
3. Both valid in different contexts (add context tags)
4. Merge into nuanced conclusion

Choice: 1

Result:
- C001 status: superseded_by C042
- C042 gains confidence (defeated alternative)
- C001 preserved in history (not deleted)
```

### 4. Context-Dependent Validity

Some conflicts aren't conflicts - they're context-dependent:

```
C001: "Use pooling" [context: high-throughput services]
C042: "Use single connections" [context: memory-constrained environments]

Resolution: Both valid, different contexts
```

---

## Data Structures

### Conflict Record

```
{
  id: string,
  conclusions: [conclusion_id, conclusion_id],
  type: "truth" | "preference",
  status: "pending" | "resolved",
  resolution: {
    type: "supersede" | "reject" | "coexist" | "merge",
    winner_id: string | null,
    context_tags: [string] | null,
    merged_conclusion_id: string | null
  },
  resolved_at: timestamp
}
```

### Extended Conclusion

```
{
  ...slice3_conclusion,
  superseded_by: conclusion_id | null,
  supersedes: [conclusion_id],
  conflicts: [conflict_id],
  context_tags: [string]  // when valid
}
```

---

## Technical Considerations

- **Contradiction detection**: Semantic similarity + opposing sentiment
- **Evidence weighing**: Recency, source count, user trust
- **History preservation**: Never delete, only mark relationships

---

## Success Criteria

1. [ ] Contradictions are automatically detected
2. [ ] Conflicts are classified (truth vs preference)
3. [ ] User can resolve conflicts with multiple options
4. [ ] Superseded conclusions remain accessible
5. [ ] Context tags allow coexistence of situational truths

---

## Out of Scope (Future Slices)

- Emergent confidence from resolution patterns
- Community voting on conflicts
