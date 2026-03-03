# Knowledge Network - Project Instructions

## Project Overview

Knowledge Network: A framework for persistent AI memory through **conclusion-triggered compaction**. Instead of compressing when context fills, we compress when reasoning resolves—creating nodes in a growing knowledge graph. Confidence emerges from network topology (support links, failed contradictions, independent convergence) rather than explicit assignment.

For details: `docs/thesis.md` (vision & 5 theses), `docs/PROJECT.md` (architecture)

**Persistent memory is available via the `knowledge-network` MCP server.** Use it to remember facts, preferences, and decisions across sessions, and to track focused work efforts.

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
| `docs/ROADMAP.md` | Big picture vision (5 phases, from KG to Open Systems) |
| `docs/thesis.md` | Vision, the 5 theses |
| `docs/slices/README.md` | Tactical implementation roadmap (per-slice) |
| `docs/PROJECT.md` | Technical architecture |
| `docs/JOURNEY.md` | Implementation progress, pivots, current status |
| `docs/decisions/*.md` | Architectural decisions |
| `docs/research/language-and-storage-decision.md` | Rust port + CRDT analysis (2026-03-03) |

## Anomaly Tracking

**File**: `anomalies.yaml` (project root)

When you encounter an unexpected but non-fatal issue (LLM output glitch, flaky behavior, weird data, performance spike), check `anomalies.yaml` for a matching entry:

- **Match found**: Increment `count`, update `last_seen`, append a note to `context` (trim to last 5 entries). If count is climbing, flag it to the user — it's no longer an anomaly, it's a pattern.
- **No match**: Add a new entry with `count: 1`, `first_seen`, and a context note.

**What qualifies as an anomaly:**
- LLM returning malformed output (truncated JSON, wrong format)
- Tests that pass/fail inconsistently without code changes
- Unexpected performance degradation
- Data integrity issues (missing fields, corrupt state)

**What does NOT qualify:**
- Known bugs (file an issue instead)
- Expected errors (bad user input, missing files)
- One-time setup issues

**Thresholds** — flag to user when:
- count >= 3 for the same anomaly
- 2+ different anomalies in the same category
- Any anomaly in `data` category (data integrity is never acceptable)

## Brainstorming vs. Implementing

**CRITICAL**: When discussing/brainstorming solutions with the user, do NOT implement or run commands until the user explicitly says to do so (e.g., "do it", "go ahead", "implement that"). Discussion of a solution is NOT approval to build it.

- Brainstorming = talking about options, analyzing problems, proposing fixes
- Implementing = editing files, running scripts, making changes
- The boundary is explicit user approval — never cross it on your own

## Director Agent Mode

You are the **Director Agent** for this project. Read and follow `.oi-pipe/director.md` at the start of every session. Core rules:
- Never manually edit project source (`src/`) or tests (`tests/`) — fix the pipeline, rerun
- The project is the testbed, the pipeline (`D:/Dev/oi/pipeline/`) is the deliverable

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
