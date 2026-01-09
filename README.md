# Knowledge Network

A conversation system that compacts based on conclusions, not token limits.

## The Problem

Current AI conversation systems truncate or summarize when context windows fill. This treats knowledge as a storage problem. We treat it as a reasoning problem.

## The Approach

**Conclusion-triggered compaction**: Instead of compressing when we run out of space, we compress when we reach understanding. Each conclusion becomes a node in a growing knowledge graph.

Key concepts:
- **Threads stay open** until resolved (like the mind)
- **Conclusions are first-class** - extracted, linked, indexed
- **Full history preserved** - but only conclusions load into context
- **Confidence emerges** from network topology, not explicit scores

## Documentation

- [Thesis Document](docs/thesis.md) - Full framework description

## Project Status

**Phase 1: Single-Session Conclusion Tracking** (in progress)
- [ ] Basic conversation loop with direct API calls
- [ ] Thread storage (full history)
- [ ] Conclusion detection
- [ ] Context builder (conclusions + active thread)
- [ ] Token accounting / savings demonstration

## Architecture

```
User Input
    ↓
Context Builder ←── Thread Store (full history)
    ↓                     ↑
Prompt Assembly ←── Conclusion Index
    ↓
API Call (Claude/GPT/etc)
    ↓
Response Handler
    ↓
Conclusion Detector ──→ triggers compaction
    ↓
Output to User
```

## Related Work

- [Living Knowledge Networks Thesis](docs/thesis.md)
- [Open Systems Project](https://github.com/...) - Governance system with similar principles
