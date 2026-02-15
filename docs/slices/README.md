# Implementation Slices: CCM Proof Roadmap

Progressive implementation proving Cognitive Context Management (CCM) for whitepaper publication.

See [publication-strategy.md](../publication-strategy.md) for why these slices exist.

---

## Philosophy

**The whitepapers are the product. The software is the proof.**

Each slice adds a proof point to the CCM whitepaper. Implementation is the minimum needed to generate publishable data.

---

## CCM Slices (Active Roadmap)

| Slice | Name | Proves | Spec |
|-------|------|--------|------|
| 1 | Core Compaction | Token savings from effort-based compaction (~80% reduction) | [01-core-compaction-proof.md](01-core-compaction-proof.md) |
| 2 | Expansion & Multi-Effort | Quality preservation — concluded effort info is recallable on demand | — |
| 3 | Salience Decay | Self-managing context — expanded info fades when no longer relevant | — |
| 4 | Bounded Working Context | Scales to many efforts without unbounded context growth | — |

### Slice 1: Core Compaction Proof

**Proves**: Open efforts = full raw context. Concluded efforts = summary only. ~80% token savings.

Tool-based effort management (LLM calls tools via natural language). One effort at a time. Two-log model. Token measurement. Quality comparison test.

**Spec**: [01-core-compaction-proof.md](01-core-compaction-proof.md)

### Slice 2: Expansion & Multi-Effort

**Proves**: Nothing is truly lost. Concluded effort details are recallable on demand. Multiple efforts can coexist.

- Expansion on demand: temporarily load concluded effort's raw log into working context
- Multiple simultaneous open efforts with switching
- Recall tracking: record when user references concluded efforts
- Interruption detection: ambient messages during open effort
- `/effort` commands as manual override for power users

### Slice 3: Salience Decay

**Proves**: Context is self-managing. Expanded information naturally fades when no longer referenced.

- Turn-based decay: expanded content removed after N turns without reference
- Working context cache file (avoid re-assembly every turn)
- Decay metrics: how often expansions are needed, how long they persist

### Slice 4: Bounded Working Context

**Proves**: System scales. Many efforts don't mean unbounded context.

- Working context limit (~4 active items)
- Cross-session persistence
- Token budget management
- Oldest/least-relevant items compacted under pressure

---

## Dependencies

```
Slice 1: Core Compaction (foundation)
    ↓
Slice 2: Expansion & Multi-Effort (recall, multiple efforts)
    ↓
Slice 3: Salience Decay (self-managing context)
    ↓
Slice 4: Bounded Working Context (scaling)
```

---

## Future Slices (from original roadmap, unrevised)

These were planned during the dev-first pivot. They'll be revised when CCM slices 1-4 are complete.

| Slice | Name | Summary |
|-------|------|---------|
| 5 | Dev Artifacts | Story, spec, test contract artifact types for dev workflow |
| 6 | Progress Visibility | Past/present/future session state, token stats |
| 7 | Effort Weight | Cost/quality tradeoff dial, compaction thresholds |
| 8 | RAG Retrieval | Cross-artifact context building, vector search |
| 9 | Knowledge Graph | Cross-session connections, topology (KN whitepaper territory) |
| 10 | Abstraction & Confidence | Privacy gradient, emergent confidence scoring |

---

## Related Documents

- [Publication strategy](../publication-strategy.md) — Three whitepapers, what each proves
- [Whitepaper](../whitepaper.md) — CCM whitepaper draft
- [Thesis](../thesis.md) — Knowledge Network vision, 5 theses
