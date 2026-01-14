# Slice 5: Emergent Confidence

Confidence scores emerge from network topology, not explicit assignment.

---

## Goal

Conclusions gain confidence through network structure: supports, failed disproofs, independent convergence.

---

## Prerequisites

- Slice 4 complete (conflict resolution exists)

---

## Key Features

### 1. Confidence Calculation

Confidence isn't assigned - it's computed from:

```
Confidence(node) = f(
  inbound_supports,           // conclusions that reference this
  failed_contradictions,      // attempts to disprove that failed
  independent_paths,          // distinct reasoning chains reaching same conclusion
  supporter_confidence        // recursive: confidence of supporting nodes
)
```

### 2. Confidence Signals

| Signal | Effect |
|--------|--------|
| New conclusion supports this | +confidence |
| Attempt to contradict fails | +confidence (failed disproof) |
| Multiple users reach same conclusion | +confidence (independent convergence) |
| Supporting conclusion gains confidence | +confidence (propagation) |
| Successfully contradicted | -confidence (superseded) |
| Isolated (no connections) | low confidence (untested) |

### 3. Propagating Updates

When conclusion A's confidence changes:

```
A gains confidence
    ↓
All conclusions A supports → recalculate
    ↓
Their supporters → recalculate
    ↓
Cascade through network
```

### 4. Confidence Visualization

```
> /confidence C001

Conclusion: "Validate inputs at trust boundaries"
Confidence: 0.87 (high)

Supports:
  - C012: Token validation (+0.15)
  - C023: SQL sanitization (+0.12)
  - C045: API request validation (+0.18)

Failed disproofs:
  - C089: "Validation is overhead" (rejected) (+0.22)

Independent paths: 3 (+0.20)
```

### 5. Confidence-Weighted Context

When building context for new conversations, higher-confidence conclusions are prioritized:

```
Loading context for "security" topic:
- [0.92] Defense in depth
- [0.87] Validate at trust boundaries
- [0.73] Sanitize all user input
- [0.45] Consider rate limiting (lower confidence, fewer supports)
```

---

## Data Structures

### Extended Conclusion

```
{
  ...slice4_conclusion,
  confidence: {
    score: float,           // 0.0 - 1.0
    components: {
      inbound_supports: float,
      failed_contradictions: float,
      independent_paths: float,
      propagated: float
    },
    last_calculated: timestamp
  }
}
```

### Confidence Event Log

```
{
  conclusion_id: string,
  event_type: "support_added" | "contradiction_failed" | "independent_path" | "propagation",
  delta: float,
  source_id: string | null,
  timestamp: string
}
```

---

## Algorithm Considerations

Options for confidence propagation:

1. **PageRank-like**: Iterative propagation until convergence
2. **Bayesian**: Prior + evidence updates
3. **Simple weighted sum**: Direct calculation from immediate neighbors

For MVP: Simple weighted sum, can sophisticate later.

---

## Technical Considerations

- **Cycle detection**: Prevent infinite propagation loops
- **Dampening**: Propagation should decay with distance
- **Recalculation triggers**: On-demand vs batch vs real-time
- **Performance**: Graph traversal efficiency at scale

---

## Success Criteria

1. [ ] Every conclusion has a confidence score
2. [ ] Scores update when network changes
3. [ ] Propagation works correctly (supporting conclusions affect parents)
4. [ ] Failed disproofs increase confidence
5. [ ] High-confidence conclusions prioritized in context loading
6. [ ] Can explain why a conclusion has its confidence score

---

## Future Possibilities (Beyond Slice 5)

- Community-wide confidence (shared knowledge network)
- Confidence decay over time (old untested conclusions fade)
- Domain-specific confidence (high in one area, low in another)
- Confidence-based filtering (only show conclusions above threshold)
