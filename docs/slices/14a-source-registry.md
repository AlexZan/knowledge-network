# Slice 14a: Source Registry + Logical Provenance URIs

## Problem

Two related gaps discovered while planning ChatGPT export ingestion:

**1. Absolute / implicit paths in provenance URIs**

Every node's `provenance_uri` encodes a physical location. When the source file moves, the URI is dead. Currently `parse_file()` uses `base_dir` defaulting to `path.parent`, so `doc://conflict-resolution-findings.md` has no declared root — it's meaningless without knowing what machine and directory it was ingested from.

**2. No source identity**

If you ingest 5,000 claims from a ChatGPT export, those nodes have no declared relationship to *where they came from*. There is no "this source lives here" record. If the source moves — or if you want to re-ingest after the source updates — you have no way to find it.

**3. Verbosity**

A long absolute path repeated across thousands of nodes wastes space and makes diffs noisy. The Rust phase gets string interning for free; YAML does not.

---

## Design

### `sources.yaml` — source registry

New file in `session_dir/sources.yaml`. Each entry registers a named source:

```yaml
sources:
  - id: physics-chatgpt
    type: chatgpt_export
    path: /mnt/windows/Users/Lex/Downloads/818c0ef...-2026-02-05.zip
    label: "Physics Theory — ChatGPT export Feb 2026"
    registered: "2026-03-03T19:00:00"

  - id: knowledge-network-docs
    type: doc_root
    path: /mnt/storage/Dev/knowledge-network/docs
    label: "knowledge-network project docs"
    registered: "2026-03-03T19:00:00"
```

**Source types:**
- `doc_root` — a directory tree; URIs are relative paths within it
- `chatgpt_export` — a `conversations.json` or zip; URIs are conversation IDs
- `claude_chatlog` — Claude Code session files; URIs are session IDs (already logical)
- `pdf` — single PDF file; URIs are page/section references

### Logical URI format

| Scheme | Format | Example |
|--------|--------|---------|
| `doc://` | `doc://{source_id}/{rel_path}#{section}` | `doc://knowledge-network-docs/decisions/016-rust-wasm-port.md#rationale` |
| `chatgpt://` | `chatgpt://{source_id}/{conversation_id}` | `chatgpt://physics-chatgpt/6966425b-18fc-8332-aef9-ba73d13742bd` |
| `chatlog://` | `chatlog://claude-code/{session_id}:L{line}` | already logical — no change |

Key invariant: **no physical paths in URIs**. The path lives only in `sources.yaml`.

### Resolution

```python
def resolve_uri(uri: str, session_dir: Path) -> dict | None:
    """Resolve a logical URI to its physical location.

    Returns:
        {"source_id": ..., "source_type": ..., "physical_path": Path(...),
         "relative_ref": ..., "fragment": ...}
        or None if source not registered.
    """
```

Resolution is best-effort: if a source isn't registered or the path has moved, resolution fails gracefully. The URI itself remains valid in the graph — it's the registry entry that tracks physical location.

### MCP tool: `mcp_add_source`

```
mcp_add_source(id, type, path, label="")
```

Registers a source before ingestion. Returns error if `id` already registered with different path.

### `mcp_list_sources`

Lists registered sources with path existence check (warns if path no longer valid).

---

## Changes Required

### `sources.py` (new)
- `load_sources(session_dir)` / `save_sources(session_dir, sources)`
- `register_source(session_dir, id, type, path, label)` — errors on conflict
- `resolve_uri(uri, session_dir)` — logical → physical
- `build_doc_uri(source_id, rel_path, fragment=None)` → `doc://{source_id}/{rel_path}#{fragment}`
- `build_chatgpt_uri(source_id, conv_id)` → `chatgpt://{source_id}/{conv_id}`

### `parser.py`
- `parse_file()` gains `source_id: str` parameter (required when ingesting into registry)
- `_build_provenance_uri()` replaced by `build_doc_uri(source_id, rel_path, fragment)`
- `base_dir` is derived from the registered source path, not inferred from file location
- Backwards compat: if no `source_id` provided, fall back to current behavior (`doc://{filename}`)

### `ingest.py`
- `ingest_pipeline()` gains `source_id: str = None` parameter
- If provided, auto-registers source (or verifies existing registration) before parsing
- Passes `source_id` down to `parse_file()`

### `mcp_server.py`
- Add `mcp_add_source` and `mcp_list_sources` tools
- `mcp_ingest_document()` gains optional `source_id` parameter

---

## Scope Boundaries

**In scope:**
- `sources.yaml` schema and CRUD
- Logical URI construction and resolution
- `parse_file()` updated to accept `source_id`
- `ingest_pipeline()` updated to accept `source_id`
- `mcp_add_source`, `mcp_list_sources`
- Backwards compat (no `source_id` = old behavior)

**Out of scope:**
- Migrating existing nodes to new URI format (they keep old URIs)
- Re-ingestion / source update tracking
- Source-level deduplication of nodes

---

## Dependency

```
14a: Source Registry + Logical URIs
 ↓
13f: ChatGPT Export Parser  (uses chatgpt:// URIs + source registry)
 ↓
Physics Theory Ingestion (real test)
```

---

## Acceptance Criteria

1. `sources.yaml` created in session_dir on first `register_source()` call
2. `parse_file(path, source_id="my-source")` emits `doc://my-source/rel-path#section` URIs
3. `resolve_uri("doc://my-source/file.md", session_dir)` returns physical path
4. `resolve_uri("doc://my-source/file.md", session_dir)` returns `None` if source not registered
5. `ingest_pipeline(file_path, source_id="my-source")` auto-registers and passes through
6. Backwards compat: `parse_file(path)` (no source_id) still works with `doc://filename` URIs
7. All existing tests pass
