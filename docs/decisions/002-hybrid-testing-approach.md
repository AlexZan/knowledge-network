# Decision 002: Hybrid Testing Approach

**Date:** 2025-01-11
**Status:** Adopted

---

## Context

Before starting implementation of Slice 1a, we considered two approaches:

1. **TDD (Test-Driven Development)** - Write tests first based on user stories, then implement
2. **Dev First** - Build the prototype, add tests later

## Problem

This system has two types of behavior:

**Deterministic:**
- Persistence (save/load state)
- Token counting
- Data structures (Thread, Conclusion, ConversationState)
- Context building (assembling prompt from conclusions + active thread)

**Non-deterministic (LLM-dependent):**
- Conclusion detection (did user disagree?)
- Conclusion extraction (summarize the resolution)
- Topic change detection

TDD works well for deterministic code. But testing LLM behavior upfront is problematic:
- Outputs vary between runs
- Detection thresholds need tuning through experimentation
- We don't know the exact patterns until we see real conversations

## Decision

**Hybrid approach:**

1. **Dev with inline tests for deterministic parts**
   - Persistence: test save/load roundtrip
   - Token counting: test calculation accuracy
   - Data structures: test serialization/deserialization
   - Context building: test prompt assembly

2. **Manual validation for LLM-dependent parts**
   - Run real conversations
   - Observe detection behavior
   - Tune prompts and thresholds
   - Add integration tests once patterns stabilize

## Rationale

1. **Speed matters** - This is a research prototype to prove a thesis
2. **LLM behavior needs iteration** - We'll learn what works through experimentation
3. **Deterministic code should be tested** - No excuse for bugs in save/load or token counting
4. **Premature tests create friction** - Testing LLM outputs before we understand them leads to flaky tests

## What Gets Tested (During Dev)

| Component | Testable? | Approach |
|-----------|-----------|----------|
| State persistence | Yes | Unit tests |
| Token counting | Yes | Unit tests |
| Data structures | Yes | Unit tests |
| Context builder | Yes | Unit tests |
| Disagreement detection | Later | Manual first, then integration tests |
| Conclusion extraction | Later | Manual first, then integration tests |

## What Gets Validated Manually

- Conclusion triggers at the right moments
- Extracted conclusions are accurate summaries
- Context building produces coherent prompts
- The overall flow feels natural

## Future

Once the LLM-dependent behavior stabilizes:
1. Capture example conversations as fixtures
2. Write integration tests against those fixtures
3. Use snapshot testing for prompt construction
