# Decision 001: Scenario Document Before User Stories

**Date:** 2025-01-11
**Status:** Adopted

---

## Context

While writing user stories for Slice 1a, we discovered a gap in the workflow:

1. **Slice spec** defined features and scope
2. **User stories** broke those into testable pieces

But the story agent kept adding implementation details ("Context:" blocks) into stories, and stories felt disconnected from the actual user experience.

## Problem

Without a cohesive narrative, user stories become:
- Fragmented - each story exists in isolation
- Ambiguous - unclear how features connect
- Implementation-leaky - writers fill gaps with technical details

The spec says WHAT we're building. Stories say HOW to test it. But neither captures the **full experience** of using the feature.

## Decision

Add a **Scenario** step between slice spec and user stories:

```
Slice Spec → Scenario → User Stories
(what)       (experience)  (testable)
```

The scenario is a narrative walkthrough - a "day in the life" story that shows the complete experience from start to finish.

## Format

A scenario document contains:
1. **The Session** - narrative prose describing a realistic usage session
2. **What I Observed** - summary of observable behaviors
3. **What I Didn't Have To Do** - implicit expectations made explicit

## Benefits

1. **Locks in expectations** before breaking into stories
2. **Catches gaps** - if you can't narrate it, something's missing
3. **Grounds stories** - story writers have a reference for the experience
4. **Prevents implementation leak** - stories can focus on observable behavior because the scenario already established context

## Example

**Without scenario:**
Story agent writes: "Context: There is ONE continuous conversation. When a conclusion is extracted, it replaces the verbose thread..."

**With scenario:**
Story agent reads narrative of user exiting and restarting, writes: "Acceptance: I restart the CLI, my previous conclusions are still there"

The scenario absorbed the context, so stories stay clean.

## Future

We may create a dedicated scenario agent for this step, but will learn from manual creation first.
