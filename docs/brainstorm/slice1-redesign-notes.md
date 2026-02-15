# Slice 1 Redesign Notes

*Captured from session 2026-02-15. These notes informed the Slice 1 scenario/spec updates.*

## The Problem

After building Slice 1 through the full TDD pipeline (scenarios → stories → tests → implementation), the CLI didn't work because:

1. **System prompt was empty** — LLM had no effort protocol instructions
2. **Follow-up messages opened new efforts** — LLM didn't know to keep working in the existing effort
3. **Detection was emergent, not enforced** — `detection.py` had stubs that were NEVER CALLED; orchestrator just parsed LLM response prefixes
4. **Spec was ambiguous** — said "user explicitly opens/closes" but scenario showed LLM auto-detecting from natural language

## Root Cause Analysis

The ambiguity originated in the scenario. It said "User explicitly opens efforts" in implementation notes, but the conversation examples showed natural language detection:

```
"Let's debug the auth bug"  →  LLM responds "Opening effort: auth-bug"
"Bug is fixed, looks good"  →  LLM responds "Concluding effort: auth-bug"
```

This is NOT explicit. It's LLM-interpreted. Every downstream artifact inherited this confusion.

## Decision: Explicit Commands for Slice 1

For Slice 1, use actual explicit commands:
- `/effort [describe]` — open a new effort
- `/effort close` — close the current effort

Push auto-detection to Slice 2+:
- LLM recognizes "let's work on X" as effort opening
- LLM recognizes "looks good" / "that's done" as conclusion triggers

## Why Explicit Commands

1. **Testable without LLM** — command parsing is deterministic
2. **No system prompt dependency** — commands are code, not prompt engineering
3. **Removes ambiguity** — user clearly controls effort lifecycle
4. **Simpler implementation** — no routing heuristics needed
5. **Slice 2 adds intelligence** — LLM detection layers on top of explicit commands

## Three Interdependent Projects

This session revealed three projects that need parallel development:

| Project | Description | Status |
|---------|-------------|--------|
| **A: TDD Workflow** (oi-pipe) | Pipeline for TDD-driven development | ~80% done |
| **B: Context Management** (CCM) | Cognitive Context Management framework | Core proven, gaps found |
| **C: Knowledge Network** | Vision: knowledge graph from compacted artifacts | Vision exists, no implementation |

They're interdependent:
- A builds B and C (pipeline generates code)
- B is used BY A (agents need context management)
- C emerges FROM B (knowledge network from compacted artifacts)

## Generalized Artifact Generation (Future Vision)

Efforts are just one artifact type. The system should support many:

| Artifact Type | Trigger | Example |
|---------------|---------|---------|
| Effort | User works on a task | "Let's debug the auth bug" |
| Preference | User states preference | "I prefer dark mode" / "always use bun" |
| Fact-Answer | Q&A resolves to fact | "What's the capital of France?" → "Paris" |
| Decision | User commits to choice | "Let's go with Stripe" |

The raw log stays the same. Each artifact type has its own extractor. Context assembler pulls in whatever's relevant. For Slice 1, only efforts matter.

## Pipeline Gaps Identified

1. **No system prompt testing** — TDD pipeline tests code (mocks LLM) but never tests LLM integration
2. **Stubs slip through** — dev-agent creates `NotImplementedError` stubs for functions it wasn't asked to implement; no post-implementation sweep
3. **Brainstorm completeness** — scenarios must specify MECHANISMS, not just behaviors; ambiguous specs contaminate everything downstream

## Related Documents

- [refined-chat-model.md](refined-chat-model.md) — Full chat model with artifact architecture
- [01-two-log-proof.md](../slices/01-two-log-proof.md) — Updated Slice 1 spec
- [scenarios.md](../../efforts/chat-cli/scenarios/scenarios.md) — Updated scenario
