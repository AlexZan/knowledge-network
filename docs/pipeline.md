# Development Pipeline

How we go from idea to implementation.

---

## The Pipeline

```
Thesis → Slice Spec → Scenario → User Stories → Implementation
```

| Stage | What It Is | Who/What Creates It |
|-------|------------|---------------------|
| **Thesis** | Overall vision, the "why" | Human brainstorming |
| **Slice Spec** | Scope, features, architecture for one slice | Human + Claude |
| **Scenario** | Narrative walkthrough of user experience | scenario-agent |
| **User Stories** | Testable pieces with acceptance criteria | story-agent |
| **Implementation** | Code | dev work |

---

## Why This Order

1. **Thesis** grounds everything in the vision
2. **Slice Spec** carves off a minimal, buildable piece
3. **Scenario** locks in the experience before fragmenting it
4. **User Stories** break the scenario into testable pieces
5. **Implementation** builds what the stories describe

Without the scenario step, stories become fragmented and leak implementation details. The scenario absorbs the "context" so stories stay clean.

---

## Agents

| Agent | Input | Output |
|-------|-------|--------|
| **scenario-agent** | thesis + slice spec | `docs/scenarios/{slice}.md` |
| **story-agent** | thesis + slice + scenario | `docs/stories/{slice}.md` |

---

## File Naming Convention

**Rule: Include the step name in the filename to avoid confusion.**

Files for the same slice exist in different folders. Without step names in filenames,
they all look identical and cause confusion.

| Step | Naming Pattern | Example |
|------|----------------|---------|
| Slice Spec | `{slice-id}.md` | `1a-minimal.md` |
| Scenario | `{slice-id}-scenario.md` | `1a-minimal-scenario.md` |
| Stories | `{slice-id}-stories.md` | `1a-minimal-stories.md` |

## Document Locations

```
docs/
├── thesis.md              # Overall vision
├── tech-stack.md          # Technology decisions
├── pipeline.md            # This document
├── slices/
│   ├── README.md          # Slice overview
│   ├── 1a-minimal.md      # Slice spec
│   └── ...
├── scenarios/
│   └── 1a-minimal-scenario.md   # Narrative walkthrough
├── stories/
│   ├── INDEX.md           # Story index
│   └── 1a-minimal-stories.md    # User stories
└── decisions/
    └── 001-*.md           # Architecture decisions
```

---

## Adding a New Slice

1. **Write the slice spec** in `docs/slices/{N}-{name}.md`
2. **Run scenario-agent** → generates `docs/scenarios/{N}-{name}-scenario.md`
3. **Run story-agent** → generates `docs/stories/{N}-{name}-stories.md`
4. **Review and refine** all artifacts
5. **Implement** based on stories
