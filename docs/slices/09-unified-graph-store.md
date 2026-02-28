# Slice 9: Unified Graph Store

**Status**: Complete
**Depends on**: 8h (Reactive Knowledge)

## Summary

Merges the effort store (`manifest.yaml`) into the knowledge graph (`knowledge.yaml`). Efforts become `type: "effort"` nodes alongside facts, preferences, decisions, and principles. One store, one schema, one set of I/O functions.

## Motivation

- **Architectural simplicity**: Two separate stores with overlapping concerns (efforts reference knowledge, knowledge references efforts) created unnecessary complexity.
- **Prerequisite for schema system**: A unified store with consistent node types is needed before introducing JSON Schema validation.
- **Decision 011** (Efforts Are KG Nodes) and **Decision 013** (Unified KG Architecture) both called for this unification.

## What Changed

### Storage

- Efforts are now `type: "effort"` nodes in `knowledge.yaml`
- `manifest.yaml` is no longer written by any code path
- Existing `manifest.yaml` files are auto-migrated on first access and renamed to `.bak`
- `expanded.json` stays split (effort and knowledge expand tracking remain separate — different rendering logic)

### Effort Node Shape

```yaml
- id: auth-bug          # User-chosen name (unchanged)
  type: effort           # New: node type discriminator
  status: open           # open/concluded (unchanged)
  active: true           # Effort-specific field
  summary: null          # Set on conclusion
  raw_file: efforts/auth-bug.jsonl
  created: 2024-01-15T...
  updated: 2024-01-15T...
```

### API (Internal)

| Old | New | Notes |
|-----|-----|-------|
| `_load_manifest()` | `_load_efforts()` | Returns `list[dict]` instead of `{"efforts": [...]}` |
| `_save_manifest()` | `_save_efforts()` | Preserves non-effort nodes |
| — | `_migrate_manifest_to_knowledge()` | One-time migration, kept for backward compat |

### Files Modified

| File | Change |
|------|--------|
| `src/oi/state.py` | Added migration fn, `_load_efforts`/`_save_efforts`, removed `_load_manifest`/`_save_manifest` |
| `src/oi/tools.py` | All 17 manifest refs → `_load_efforts`/`_save_efforts` |
| `src/oi/orchestrator.py` | Reads efforts from `_load_efforts()` instead of manifest.yaml |
| `src/oi/decay.py` | 3 refs → `_load_efforts` |
| `src/oi/cli.py` | Startup display reads from `_load_efforts()` |
| `src/oi/prompts/system.md` | Updated "manifest" → "knowledge store" in tool descriptions |
| `tests/helpers.py` | `setup_concluded_effort()` writes to knowledge.yaml |
| `tests/test_tools.py` | All direct manifest reads/writes updated |
| `tests/test_orchestrator.py` | All direct manifest reads/writes updated |
| `tests/test_proof_run.py` | `_setup_concluded_efforts` methods updated |
| `tests/test_e2e_real_llm.py` | Manifest verification updated |
| `tests/test_migration.py` | **New**: migration and coexistence tests |

## Design Decisions

- **Effort IDs stay as-is**: User-chosen names like `"auth-bug"`, not auto-IDs like `"effort-001"`. This means effort IDs and knowledge auto-IDs (`fact-001`) coexist in the same namespace.
- **`active` field is effort-specific**: Like `instance_count` is principle-specific. Not all node types use all fields.
- **Status values unchanged**: Efforts use `open/concluded`, knowledge uses `active/superseded`. The type field disambiguates.
- **`expanded.json` stays split**: Effort and knowledge expand tracking remain separate because they have different rendering logic (effort expands load raw JSONL, knowledge expands load session fragments).
- **`source` field unchanged**: Knowledge nodes still reference effort IDs as strings. Now those strings are also node IDs in the same store.

## Migration

`_migrate_manifest_to_knowledge()` runs automatically when `_load_efforts()` detects a `manifest.yaml`:

1. Read `manifest.yaml`
2. Convert each effort to a `type: "effort"` node
3. Merge into `knowledge.yaml` (skip duplicates by ID)
4. Rename `manifest.yaml` → `manifest.yaml.bak`

The function is idempotent and handles edge cases (empty manifest, pre-existing knowledge nodes, already-migrated efforts).

## Verification

- 332 tests pass (322 existing + 10 new migration/coexistence tests)
- Zero `manifest.yaml` references in src/ (except migration function)
- Migration tested: basic, idempotent, empty, preserves existing knowledge, auto-migration on load
- Coexistence tested: open effort alongside knowledge, close preserves knowledge, round-trip lifecycle, save_efforts preserves non-effort nodes
