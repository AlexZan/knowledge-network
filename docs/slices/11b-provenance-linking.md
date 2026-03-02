# Slice 11b: Provenance Linking

**Status**: Spec
**Depends on**: Slice 11 (MCP Server Interface)
**Blocks**: Slice 13 (Bulk Document Ingestion — reuses provenance framework for document sources)

---

## Problem

Every KG node created via the MCP server is an orphan — no link back to the conversation that produced it. The `source` field is a free-text string (often empty), and `created_in_session` is an internal UUID that doesn't map to any client's conversation log.

When the graph has hundreds of nodes, "where did this come from?" and "why do I believe this?" become unanswerable without provenance.

## Solution

Three complementary provenance layers, all implemented in one slice:

### 1. Reasoning field on `add_knowledge`

New optional parameter `reasoning` — the LLM calling the tool includes a brief explanation of *why* it's creating this node. Stored on the node. Human-readable, portable, always available even if the source conversation is deleted.

```
add_knowledge(
  node_type="decision",
  summary="Use temperature=0 for deterministic LLM classification",
  reasoning="During debugging, link_nodes() returned 3/5 'none' and 2/5 'supports'
  for identical inputs. Setting temperature=0 made results 5/5 consistent."
)
```

This is the fallback that always works — no adapter, no file access needed.

### 2. Chatlog URI — automatic deep link

The MCP server auto-discovers the active client conversation log and stamps each node with a URI pointing into it.

**URI scheme:**
```
chatlog://claude-code/{session-id}:L{line}
```

**Discovery logic (Claude Code):**
1. Scan `~/.claude/projects/` for the most recently modified `.jsonl` file
2. Count current lines (append-only, so line count = position)
3. Store as `provenance_uri` on the node

**Schema descriptors** define per-client how to find and parse logs:

```yaml
# schemas/chatlogs/claude-code.yaml
client: claude-code
storage:
  base: "~/.claude/projects/"
  pattern: "**/{session-id}.jsonl"
  format: jsonl-append-only
message_types:
  user: {id: uuid, content: message.content, timestamp: timestamp}
  assistant: {id: uuid, content: message.content, model: message.model}
  compact_boundary: {subtype: compact_boundary, logical_parent: logicalParentUuid}
compaction:
  preserves_raw: true    # pre-compaction messages stay in file
  marker: {type: system, subtype: compact_boundary}
```

Initially only a Claude Code descriptor. Others (Cursor, etc.) added when needed — same pattern, different paths and field names.

### 3. MCP tool call log

The MCP server logs every tool invocation to `{session_dir}/mcp_sessions/{session_id}.jsonl`:

```jsonl
{"ts":"2026-03-02T14:30:00Z","tool":"mcp_add_knowledge","input":{"node_type":"fact","summary":"..."},"result_id":"fact-042","chatlog_uri":"chatlog://claude-code/b0aaa91c:L2280"}
{"ts":"2026-03-02T14:31:00Z","tool":"mcp_query_knowledge","input":{"query":"python"},"result_count":3}
```

Automatic, no client cooperation needed. Provides an audit trail of all KG operations with timestamps that correlate to client conversation logs.

## Changes

### Modified: `src/oi/knowledge.py`

`add_knowledge()` gains two optional parameters:

```python
def add_knowledge(
    ...,
    reasoning: str | None = None,       # NEW: why this node exists
    provenance_uri: str | None = None,   # NEW: chatlog:// deep link
) -> str:
```

Both stored on the node dict if provided.

### Modified: `src/oi/mcp_server.py`

1. **New parameter**: `reasoning` on `mcp_add_knowledge`
2. **Auto-discovery**: `_discover_chatlog_uri()` finds active Claude Code conversation, returns `chatlog://` URI
3. **Tool call logging**: `_log_tool_call()` writes to `{session_dir}/mcp_sessions/{session_id}.jsonl`
4. Every tool wrapper calls `_log_tool_call()` before returning

### New: `src/oi/provenance.py` (~40 lines)

Chatlog discovery and URI construction:

```python
def discover_claude_code_chatlog() -> str | None:
    """Find the active Claude Code conversation file. Return chatlog:// URI or None."""

def resolve_chatlog_uri(uri: str) -> list[dict] | None:
    """Given a chatlog:// URI, return the referenced messages. None if unresolvable."""
```

### New: `schemas/chatlogs/claude-code.yaml`

Schema descriptor for Claude Code's native log format (as documented above).

### Modified: `src/oi/mcp_server.py` formatting

`_fmt_add()` shows provenance info when present:

```
+ fact-042 [fact] (low confidence)
  "Use temperature=0 for deterministic LLM classification"
  Reasoning: During debugging, link_nodes() returned inconsistent results...
  Provenance: chatlog://claude-code/b0aaa91c:L2280
```

### Tests

- Test `_discover_chatlog_uri()` with mock `.claude/projects/` directory
- Test `_log_tool_call()` writes correct JSONL
- Test `reasoning` field stored on node and returned in queries
- Test `provenance_uri` field stored on node
- Test formatting shows provenance info
- Integration: add node via MCP → verify all three provenance layers populated

## Node Schema After This Slice

```yaml
- id: fact-042
  type: fact
  summary: "Use temperature=0 for deterministic LLM classification"
  status: active
  source: "graph-aware-search-design"           # existing field (effort/context)
  reasoning: "link_nodes() returned 3/5 'none'..." # NEW: why this exists
  provenance_uri: "chatlog://claude-code/b0aa:L2280" # NEW: where in conversation
  created_in_session: "mcp-abc123"               # existing field
  created: "2026-03-02T14:30:00"
  updated: "2026-03-02T14:30:00"
```

## Future Extensions (not in this slice)

- **Adapter registry**: Pluggable resolvers for different `chatlog://` schemes
- **Multi-client descriptors**: Cursor, Windsurf, custom clients
- **`expand_provenance` MCP tool**: Resolve a URI and return the surrounding conversation
- **Bidirectional linking**: From chat log → nodes created during that conversation
- **Provenance on effort close**: Auto-extract nodes get provenance from the effort's conversation

## Design Notes

- Schema descriptors are YAML files read at resolve time, not at node creation time. Creating a node is fast; resolving provenance is the slow path.
- The `reasoning` field is intentionally separate from `source`. Source is "which effort/context", reasoning is "what was the thinking." They serve different questions.
- Claude Code's JSONL is append-only, so line numbers are stable addresses. If a client uses a format where line numbers shift, the schema descriptor should indicate `format: mutable` and addressing should prefer UUIDs.
- The MCP tool call log is deliberately minimal — timestamp, tool name, inputs, key result. Not a full conversation log.
