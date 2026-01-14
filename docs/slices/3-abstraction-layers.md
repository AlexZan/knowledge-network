# Slice 3: Abstraction Hierarchy & Privacy Gradient

Add layers of abstraction with privacy implications.

---

## Goal

Transform specific conclusions into shareable general knowledge while preserving privacy.

---

## Prerequisites

- Slice 2 complete (knowledge graph exists)

---

## Key Features

### 1. Automatic Generalization

```
Layer 0 (Private):   "Fixed auth bug in my-company's user.rs line 47"
Layer 1 (Team):      "Rust services need token validation before DB queries"
Layer 2 (Community): "Validate inputs at trust boundaries"
Layer 3 (Universal): "Defense in depth"
```

### 2. Privacy Classification

Each conclusion tagged with sharing level:

| Level | Contains | Shareable With |
|-------|----------|----------------|
| 0 - Raw | File paths, company names, specific code | Only self |
| 1 - Contextual | Technology stack, patterns, domain | Team/org |
| 2 - Principle | General programming principles | Community |
| 3 - Universal | Fundamental concepts | Everyone |

### 3. Export Controls

```
> /export --level 2

Exporting community-shareable conclusions:
- "Validate inputs at trust boundaries"
- "Connection pools need size limits"
- "Cache invalidation should be event-driven"

Excluded (private):
- 12 conclusions with specific project details
```

### 4. Abstraction Detection

System identifies when multiple specific conclusions share a pattern:

```
Detected pattern across 3 conclusions:
- C001: Token validation before DB
- C007: Input sanitization before SQL
- C012: Request validation before API calls

Proposed abstraction: "Validate at trust boundaries"
Accept? (y/n)
```

---

## Data Structures

### Extended Conclusion

```
{
  ...slice2_conclusion,
  privacy_level: 0 | 1 | 2 | 3,
  generalizations: [conclusion_id],  // more abstract versions
  specifications: [conclusion_id],   // more specific instances
  pii_detected: boolean,
  pii_scrubbed_version: string | null
}
```

---

## Technical Considerations

- **PII detection**: Identify company names, file paths, personal info
- **Generalization quality**: Ensure abstractions preserve meaning
- **User control**: Override privacy levels manually

---

## Success Criteria

1. [ ] Conclusions are automatically assigned privacy levels
2. [ ] PII is detected and flagged
3. [ ] Can export at specific privacy levels
4. [ ] Abstractions are generated from patterns
5. [ ] User can override privacy classifications

---

## Out of Scope (Future Slices)

- Community knowledge sharing
- Confidence from independent convergence
- Conflict resolution
