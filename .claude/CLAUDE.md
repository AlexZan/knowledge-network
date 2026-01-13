# Knowledge Network - Project Instructions

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
| `docs/JOURNEY.md` | Implementation progress, pivots |
| `docs/decisions/*.md` | Architectural decisions |
