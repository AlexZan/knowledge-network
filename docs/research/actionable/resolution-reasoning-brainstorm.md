# Problem: Auto-resolutions have no reasoning

**Date**: 2026-03-14
**Context**: Auto-resolution sample review

## The problem

Auto-resolved conflicts record only the outcome ("fact-X supersedes fact-Y") and a generic reason string ("Auto-resolved: overwhelming topological support"). There is no explanation of *why* these claims conflict or *why* one side won.

## Two separate reasoning gaps

1. **Why do these conflict?** — The LLM already determines this at linking time when it creates the `contradicts` edge. It has both claims in context and understands the nature of the disagreement. But it doesn't store detailed reasoning about the conflict — just the edge type. This reasoning could be captured at construction time without any change to the resolution phase.

2. **Why did this side win?** — The topology decides this via support ratio. The reasoning is the supporter subgraph — it's already captured structurally but nothing walks it to produce a human-readable explanation.

Neither gap requires introducing LLM into the resolution phase. #1 is a construction-phase improvement (store richer reasoning on `contradicts` edges at linking time). #2 is already in the graph, just not surfaced.
