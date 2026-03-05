# Ingestion Resume: Findings and Cross-Source-ID Bug

**Date**: 2026-03-05
**Status**: Implemented, tested live

## Feature: Document Ingestion Resume

Added `skip_existing` (default `True`) to `ingest_pipeline()`. Before parsing or calling the LLM, the pipeline checks whether the document's provenance URI already exists in the knowledge graph. If so, it returns immediately with zero LLM calls.

This mirrors the existing `_get_ingested_conv_ids()` mechanism for ChatGPT conversations, completing resume/checkpoint support for both ingestion paths.

### How It Works

1. Compute the file's relative path from `base_dir` (e.g. `thesis.md`)
2. Scan all `doc://` provenance URIs in the graph via `_get_ingested_doc_paths()`
3. Match by filename suffix — `thesis.md` matches both `doc://thesis.md#...` and `doc://my-source/thesis.md#...`
4. If matched: skip with `documents_skipped=1`, zero LLM cost
5. Override with `skip_existing=False` to force re-ingestion

### Why Not Filter by source_id?

See bug below. The same physical file can be ingested under different source_ids, producing different provenance prefixes. Filtering by source_id would miss cross-source duplicates.

## Bug: Cross-Source-ID Duplicate (223 nodes)

### What Happened

`thesis.md` was originally ingested with `source_id="knowledge-network-docs"`, producing provenance URIs like:
```
doc://knowledge-network-docs/thesis.md#intro
```

When re-ingested **without** a source_id (via `mcp_ingest_document`), the pipeline looked for:
```
doc://thesis.md#...
```

No match. The pipeline treated it as a new document and created **223 duplicate nodes** before the issue was caught.

### Root Cause

The initial implementation of `_get_ingested_doc_paths()` accepted a `source_id` parameter and filtered URIs to `doc://{source_id}/` prefix only. When called without a source_id, it only matched bare `doc://filename` URIs — missing any source_id-prefixed variants.

### Fix

1. `_get_ingested_doc_paths()` returns **all** `doc://` paths, regardless of source_id
2. The skip check matches by filename suffix: `p == rel_str or p.endswith(f"/{rel_str}")`
3. This catches all variants: `doc://thesis.md`, `doc://my-source/thesis.md`, `doc://other/thesis.md`

### Regression Tests

- `test_skip_cross_source_id`: File ingested with source_id, re-ingested without → must skip
- `test_skip_cross_source_id_reverse`: File ingested without source_id, re-ingested with → must skip

### Cleanup

The 223 duplicate nodes were removed by scanning for `doc://thesis.md#` prefix (created 2026-03-05) and filtering them out of `knowledge.yaml`. No edges existed (ingested with `skip_linking=True`).

## Live Validation

| Test | Document | source_id | Result | Cost |
|------|----------|-----------|--------|------|
| Re-ingest thesis.md | `thesis.md` | none (original: `knowledge-network-docs`) | Skipped (cross-source match) | $0 |
| New doc | `020-salience-confidence-separation.md` | none | 80 nodes, 13/15 chunks | ~$0.05 |
| Re-ingest decision 020 | `020-salience-confidence-separation.md` | none | Skipped | $0 |

## Lesson Learned

When an MCP tool call produces unexpected results (e.g. a skip check doesn't skip), **stop immediately**. Do not proceed with subsequent steps. Investigate the root cause first. Continuing wastes tokens on a broken pipeline.
