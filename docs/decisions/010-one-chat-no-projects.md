# Decision 010: One Chat, No Projects

**Date**: 2026-02-22
**Status**: Implemented

---

## Context

The current CLI requires users to specify a project:

```bash
oi --project myapp    # loads ~/.oi/projects/myapp/
oi                    # loads ~/.oi/projects/default/
```

This creates problems:
- User must remember project names
- User must decide which project a topic belongs to *before* they start talking
- Cross-project knowledge is siloed (an insight from project A can't inform project B)
- The `default` fallback becomes a junk drawer

The `sessions-and-dashboard.md` brainstorm explored sessions as explicit containers but still required users to manage them. This decision goes further.

## Decision

**One global knowledge space. No projects. No sessions to manage.**

The user launches `oi` and either:
1. Sees their recent/open efforts and picks one to continue
2. Just starts talking — the LLM routes to existing efforts or opens new ones

Efforts are the only organizing unit. The knowledge graph is global. The LLM handles context routing using existing tools (`search_efforts`, `effort_status`, and future `query_knowledge`).

## What changes

### UX on launch

Current:
```
[Project: myapp | Session #3]
[2 open effort(s)]
  - auth-bug
  - api-refactor
```

New:
```
[2 open effort(s)]
  - auth-bug
  - api-refactor
[5 concluded efforts searchable]

>
```

No project name. No session number. Just what's active and a prompt.

### Startup flow

1. User types `oi` (no flags)
2. System loads `~/.oi/` (single global directory)
3. Shows open efforts (if any) and concluded count
4. User starts talking
5. LLM uses `effort_status`, `search_efforts`, `query_knowledge` to find relevant context

### Routing

- User says "let's continue the auth bug" → LLM calls `switch_effort` or `reopen_effort`
- User says "remember that caching fix?" → LLM calls `search_efforts`, finds it, asks if user wants to reopen
- User says "help me debug this new thing" → LLM calls `open_effort`
- User says "what do I know about input validation?" → LLM calls `query_knowledge` (Slice 8b)

The LLM already does this routing for efforts. The ONE CHAT model just removes the project layer above it.

### Storage

Current:
```
~/.oi/projects/myapp/manifest.yaml
~/.oi/projects/myapp/efforts/
~/.oi/projects/default/manifest.yaml
~/.oi/projects/default/efforts/
```

New:
```
~/.oi/manifest.yaml
~/.oi/efforts/
~/.oi/raw.jsonl
~/.oi/knowledge/        ← Slice 8: knowledge graph nodes
```

One manifest. One effort directory. One knowledge graph.

### CLI changes

- Remove `--project` flag
- Remove `--session-dir` flag (keep for testing only, e.g. `--data-dir`)
- Remove `DEFAULT_SESSION_DIR` constant
- Change default to `~/.oi/`
- Simplify `_show_startup` (no project name, no session number)

### What about per-project context?

Efforts already carry project context implicitly. An effort named "myapp-auth-bug" or with a summary mentioning "myapp" is findable via `search_efforts`. The knowledge graph (Slice 8) makes this even better — nodes from different domains connect through shared principles.

The user doesn't need to pre-declare project boundaries. Knowledge flows across them.

## Why this matters for Slice 8

The knowledge graph must be global for cross-domain insights to work (Thesis 2). If graphs are per-project:
- "Validate inputs at trust boundaries" learned in Project A can't inform Project B
- Independent convergence (Thesis 5) can't be detected across projects
- Abstraction (Thesis 3) has a smaller pool to generalize from

ONE CHAT + global knowledge graph = the thesis works as designed.

## What we're NOT doing

- No dashboard (yet) — the LLM-driven routing replaces manual navigation
- No session numbering — sessions are an implementation detail, not a user concept
- No project hierarchies — efforts are flat, connections come from the knowledge graph
- No migration — current test data is in `--session-dir` test paths anyway

## Risks

- **Scale**: One flat manifest could get large. Mitigation: eviction already works (Slice 4), and the knowledge graph is the long-term index.
- **Ambiguity**: LLM might struggle to route when many efforts exist. Mitigation: `search_efforts` + `query_knowledge` give it tools to disambiguate.
- **Testing**: Tests use `tmp_path` session dirs, so they're unaffected.

## Implementation

This is a small CLI change (remove `--project`, change default path). Can be done as a standalone commit before or during Slice 8a. The architectural consequence (global knowledge graph) is what matters — and that's the design Slice 8 should assume from the start.
