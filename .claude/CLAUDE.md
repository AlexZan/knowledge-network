# Knowledge Network - Project Instructions

## Project Overview

Knowledge Network: A framework for persistent AI memory through **conclusion-triggered compaction**. Instead of compressing when context fills, we compress when reasoning resolves—creating nodes in a growing knowledge graph. Confidence emerges from network topology (support links, failed contradictions, independent convergence) rather than explicit assignment.

For details: `docs/thesis.md` (vision & 5 theses), `docs/PROJECT.md` (architecture)

## Documentation Rules

### No Duplicate Sources of Truth

Never recreate content that already exists in another markdown file. Always use backlinks.

- If information exists in `docs/thesis.md`, link to it: `See [thesis.md](../docs/thesis.md)`
- If you need to reference a concept, link to where it's defined
- Each piece of information should have ONE authoritative location

**Why**: Duplicate content drifts out of sync. Single source + backlinks keeps docs maintainable.

## Key Documentation

| Doc | Source of Truth For |
|-----|---------------------|
| `docs/thesis.md` | Vision, the 5 theses |
| `docs/slices/README.md` | Implementation roadmap |
| `docs/PROJECT.md` | Technical architecture |
| `docs/JOURNEY.md` | Implementation progress, pivots, current status |
| `docs/decisions/*.md` | Architectural decisions |

## Brainstorming vs. Implementing

**CRITICAL**: When discussing/brainstorming solutions with the user, do NOT implement or run commands until the user explicitly says to do so (e.g., "do it", "go ahead", "implement that"). Discussion of a solution is NOT approval to build it.

- Brainstorming = talking about options, analyzing problems, proposing fixes
- Implementing = editing files, running scripts, making changes
- The boundary is explicit user approval — never cross it on your own

## Development Approach

### TDD Pipeline Tool (oi-pipe)

This project uses **oi-pipe** (`D:/Dev/oi/pipeline/`) for TDD-driven development. Oi-pipe runs artifacts through a pipeline: brainstorm → scenarios → stories → tests → dev → qa.

See: `D:/Dev/oi/pipeline/docs/slice-1-mvp.md` for oi-pipe spec.

### Current Effort: Chat CLI

Testing oi-pipe by building the first real feature of this project:

```
efforts/chat-cli/
├── ideas/           ← refined-chat-model.md, 01-core-capture.md
├── scenarios/       ← oi next generates these
├── stories/
├── tests/
├── src/
└── qa/
```

**Spec**: `docs/brainstorm/refined-chat-model.md` (two-log model, artifact extraction)

**Scope**: `docs/slices/01-core-capture.md` (Slice 1: effort artifacts, conclusion-triggered compaction)

### To Resume Work

```bash
cd D:/Dev/knowledge-network/efforts/chat-cli
cat .oi-pipe/state.yaml   # see current stage
oi next                    # run next pipeline stage
```

### Feedback Loop

Developing chat-cli tests oi-pipe. When oi-pipe has issues:
1. Note the issue
2. Fix in `D:/Dev/oi/pipeline/`
3. Resume chat-cli development
