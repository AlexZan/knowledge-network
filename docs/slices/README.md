# Implementation Roadmap

Building a general-purpose AI system with persistent memory, tool use, and knowledge accumulation.

CCM whitepaper published (Slices 1-4). Now focused on product development.

---

## Completed (CCM Foundation)

| Slice | Name | What it does | Spec |
|-------|------|-------------|------|
| 1 | Core Compaction | Open efforts = raw context, concluded = summary. ~97% token savings. | [01-core-compaction-proof.md](01-core-compaction-proof.md) |
| 2 | Expansion & Multi-Effort | Concluded efforts recallable on demand. Multiple simultaneous efforts. | [02-expansion-multi-effort.md](02-expansion-multi-effort.md) |
| 3 | Salience Decay | Expanded efforts auto-collapse when no longer referenced. | [03-salience-decay.md](03-salience-decay.md) |
| 4 | Bounded Working Context | Summary eviction, ambient windowing, `search_efforts`. O(1) working memory. | [04-bounded-working-context.md](04-bounded-working-context.md) |

---

## Next: Slice 5 — Effort Reopening

Completes the effort lifecycle. Concluded efforts can be reopened and extended, not just viewed.

- `reopen_effort` tool: flip concluded → open, preserve raw log, append new messages
- Ambiguous match detection: search concluded efforts when user starts a related topic
- LLM asks user: reopen or start new? (only when ambiguous)
- Re-conclusion updates summary to cover full extended conversation

**Spec**: [05-effort-reopening.md](05-effort-reopening.md)

---

## Future Slices

### Slice 6: Cross-Session Persistence

Efforts and summaries survive between sessions. The bridge from single-session CCM to persistent knowledge.

- Manifest and raw logs persist across CLI launches
- Session linking: resume efforts from previous sessions
- Manifest merging when sessions overlap

### Slice 7: Tool Use

The system becomes an agent — can act on the world, not just talk. Likely multiple sub-slices.

- Bash execution, file system access
- RAG / document ingestion
- Search (web, codebase, knowledge base)
- Error recovery, permissions, output capture

**Phase boundary**: Slices 1-6 are a memory system. Slice 7 makes it an agent. Different architectural concerns.

### Slice 8: Knowledge Graph

Cross-session knowledge accumulation. The core of the Knowledge Network vision. Future KN whitepaper.

- Conclusion nodes with typed connections (support, contradiction, generalization)
- Cross-session link detection
- Confidence from network topology
- Abstraction hierarchy and privacy gradient

See [thesis.md](../thesis.md) for the full KN vision (Theses 2-5).

### Slice 9: Workflow Integration

Workflows (like TDD pipeline) become tools the system can invoke. Future workflow whitepaper.

- oi-pipe as a subsystem, not a separate project
- Workflow orchestration through tool calls
- Reassess priority after Slice 7 (tool use)

---

## Dependencies

```
Slices 1-4: CCM Foundation (done)
    ↓
Slice 5: Effort Reopening (completes lifecycle)
    ↓
Slice 6: Cross-Session Persistence (memory survives)
    ↓
Slice 7: Tool Use (system becomes agent)
    ↓
  ┌─────┴─────┐
  ↓           ↓
Slice 8     Slice 9
Knowledge   Workflow
Graph       Integration
(KN paper)  (WF paper)
```

---

## Related Documents

- [CCM Whitepaper](../ccm-whitepaper.md) — Published
- [Thesis](../thesis.md) — Knowledge Network vision (Theses 2-5)
- [Technical Reference](../PROJECT.md) — Architecture (needs update)
