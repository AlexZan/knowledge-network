"""MCP server exposing knowledge graph tools for Claude Code.

Thin wrapper — each tool delegates to existing functions in tools.py / knowledge.py.
Uses stdio transport (Claude Code spawns as subprocess).
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from .knowledge import add_knowledge, query_knowledge, remove_edge
from .provenance import discover_claude_code_chatlog
from .tools import (
    open_effort,
    close_effort,
    effort_status,
    search_efforts,
    reopen_effort,
    switch_effort,
)

mcp = FastMCP("knowledge-network")

# --- Internals ---

_session_id: str | None = None


def _get_session_dir() -> Path:
    """Session directory from OI_SESSION_DIR env var, defaults to ~/.oi/."""
    return Path(os.environ.get("OI_SESSION_DIR", Path.home() / ".oi"))


def _get_model() -> str:
    """Reuse the project's default model setting."""
    from .llm import DEFAULT_MODEL
    return DEFAULT_MODEL


def _get_session_id() -> str:
    """Created once per process, enables audit logging."""
    global _session_id
    if _session_id is None:
        _session_id = str(uuid.uuid4())
    return _session_id


def _or_none(val: str) -> str | None:
    """Convert empty strings to None (more robust across MCP clients)."""
    return val if val else None


def _log_tool_call(tool_name: str, inputs: dict, result_summary: str = "") -> None:
    """Log an MCP tool invocation to {session_dir}/mcp_sessions/{session_id}.jsonl."""
    try:
        session_dir = _get_session_dir()
        log_dir = session_dir / "mcp_sessions"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{_get_session_id()}.jsonl"
        entry = {
            "ts": datetime.now().isoformat(),
            "tool": tool_name,
            "input": inputs,
        }
        if result_summary:
            entry["result"] = result_summary
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Best-effort: logging failure never blocks tool execution


# --- Formatting helpers ---

def _fmt_add(raw: str) -> str:
    d = json.loads(raw)
    if "error" in d:
        return f"Error: {d['error']}"
    lines = [f"Added {d['node_id']} [{d['node_type']}]: {d['summary']}"]
    conf = d.get("confidence", {})
    if conf:
        lines.append(f"Confidence: {conf.get('level', '?')}")
    if d.get("reasoning"):
        lines.append(f"Reasoning: {d['reasoning']}")
    if d.get("provenance_uri"):
        lines.append(f"Provenance: {d['provenance_uri']}")
    for e in d.get("edges_created", []):
        lines.append(f"  -> {e['edge_type']} {e['target_id']}: {e.get('reasoning', '')}")
    return "\n".join(lines)


def _fmt_query(raw: str) -> str:
    d = json.loads(raw)
    results = d.get("results", [])
    if not results:
        return f"No matches ({d.get('total_active', 0)} active nodes in graph)"
    lines = [f"{len(results)} match(es) of {d.get('total_active', '?')} active nodes:\n"]
    for r in results:
        conf = r.get("confidence", {}).get("level", "?")
        lines.append(f"  {r['node_id']} [{r.get('type')}] ({conf}): {r.get('summary')}")
        if r.get("source"):
            lines.append(f"    source: {r['source']}")
        if r.get("reasoning"):
            lines.append(f"    reasoning: {r['reasoning']}")
        if r.get("provenance_uri"):
            lines.append(f"    provenance: {r['provenance_uri']}")
        if r.get("edges"):
            for e in r["edges"]:
                lines.append(f"    {e['type']}: {e['source']} -> {e['target']}")
    return "\n".join(lines)


def _fmt_effort_status(raw: str) -> str:
    d = json.loads(raw)
    efforts = d.get("efforts", [])
    if not efforts:
        return "No efforts yet."
    lines = []
    for e in efforts:
        status = e["status"]
        if e.get("active"):
            status += " *active*"
        if e.get("expanded"):
            status += " [expanded]"
        line = f"  {e['id']} ({status})"
        if e.get("raw_tokens"):
            line += f" — {e['raw_tokens']} tokens"
        lines.append(line)
        if e.get("summary"):
            lines.append(f"    {e['summary'][:120]}")
    return "\n".join(lines)


def _fmt_simple(raw: str) -> str:
    """Format simple status responses (open, close, switch, reopen, search)."""
    d = json.loads(raw)
    if "error" in d:
        return f"Error: {d['error']}"
    parts = []
    if "status" in d:
        parts.append(d["status"])
    if "effort_id" in d:
        parts.append(d["effort_id"])
    if "summary" in d and d["summary"]:
        parts.append(f"\n{d['summary'][:200]}")
    if "knowledge_extracted" in d and d["knowledge_extracted"]:
        parts.append(f"\nExtracted {len(d['knowledge_extracted'])} knowledge node(s):")
        for n in d["knowledge_extracted"]:
            parts.append(f"  {n['node_id']} [{n['node_type']}]: {n['summary']}")
    if "prior_summary" in d and d["prior_summary"]:
        parts.append(f"\nPrior summary: {d['prior_summary'][:200]}")
    if "results" in d:
        results = d["results"]
        if not results:
            return f"No matches for '{d.get('query', '?')}'"
        lines = [f"{len(results)} match(es):"]
        for r in results:
            lines.append(f"  {r['id']}: {r.get('summary', '')[:120]}")
        return "\n".join(lines)
    return " — ".join(parts) if parts else raw


# --- MCP Tools ---


@mcp.tool()
def mcp_add_knowledge(
    node_type: str,
    summary: str,
    source: str = "",
    related_to: str = "",
    edge_type: str = "",
    supersedes: str = "",
    reasoning: str = "",
) -> str:
    """Add a fact, preference, or decision to the knowledge graph.

    Args:
        node_type: Type of knowledge node (e.g. fact, preference, decision)
        summary: Concise summary of the knowledge
        source: Where this knowledge came from (effort name, conversation context)
        related_to: Comma-separated IDs of related existing nodes
        edge_type: Relationship type to related_to nodes (e.g. supports, contradicts)
        supersedes: Comma-separated node IDs to mark as superseded by this new node
        reasoning: Why this knowledge is being recorded (conversation context, evidence)
    """
    related_list = [r.strip() for r in related_to.split(",") if r.strip()] or None
    supersedes_list = [s.strip() for s in supersedes.split(",") if s.strip()] or None

    # Auto-discover chatlog URI for provenance
    provenance_uri = discover_claude_code_chatlog()

    raw = add_knowledge(
        session_dir=_get_session_dir(),
        node_type=node_type,
        summary=summary,
        source=_or_none(source),
        related_to=related_list,
        edge_type=_or_none(edge_type) or "supports",
        model=_get_model(),
        supersedes=supersedes_list,
        session_id=_get_session_id(),
        reasoning=_or_none(reasoning),
        provenance_uri=provenance_uri,
    )

    # Parse result to get node_id for log
    result_data = json.loads(raw)
    result_id = result_data.get("node_id", "")

    _log_tool_call("mcp_add_knowledge", {
        "node_type": node_type, "summary": summary,
    }, result_id)

    return _fmt_add(raw)


@mcp.tool()
def mcp_query_knowledge(
    query: str,
    node_type: str = "",
    min_confidence: str = "",
) -> str:
    """Search the knowledge graph by topic. Returns matching nodes with confidence.

    Args:
        query: Keyword search string (topic, concept, or node ID)
        node_type: Filter results by node type
        min_confidence: Minimum confidence level (low, medium, high)
    """
    raw = query_knowledge(
        session_dir=_get_session_dir(),
        query=query,
        node_type=_or_none(node_type),
        min_confidence=_or_none(min_confidence),
    )
    result_data = json.loads(raw)
    _log_tool_call("mcp_query_knowledge", {"query": query},
                   f"{len(result_data.get('results', []))} matches")
    return _fmt_query(raw)


@mcp.tool()
def mcp_remove_edge(
    source_id: str,
    target_id: str,
    edge_type: str = "",
) -> str:
    """Remove an edge from the knowledge graph (e.g. to correct a false positive link).

    Args:
        source_id: The source node ID of the edge to remove
        target_id: The target node ID of the edge to remove
        edge_type: Optional edge type filter (supports, contradicts, etc). If empty, removes all edges between the two nodes.
    """
    raw = remove_edge(
        session_dir=_get_session_dir(),
        source_id=source_id,
        target_id=target_id,
        edge_type=_or_none(edge_type),
    )
    result_data = json.loads(raw)
    _log_tool_call("mcp_remove_edge", {
        "source_id": source_id, "target_id": target_id, "edge_type": edge_type,
    }, result_data.get("status", ""))

    if "error" in result_data:
        return f"Error: {result_data['error']}"
    lines = [f"Removed {result_data['removed_count']} edge(s):"]
    for e in result_data.get("edges_removed", []):
        lines.append(f"  {e['source']} --{e['type']}--> {e['target']}")
    return "\n".join(lines)


@mcp.tool()
def mcp_open_effort(name: str) -> str:
    """Start tracking focused work on a topic.

    Args:
        name: Short kebab-case name for the effort (e.g. 'auth-bug', 'guild-feature')
    """
    raw = open_effort(session_dir=_get_session_dir(), name=name)
    _log_tool_call("mcp_open_effort", {"name": name})
    return _fmt_simple(raw)


@mcp.tool()
def mcp_close_effort(id: str = "") -> str:
    """Conclude an effort with summary and knowledge extraction. If id is omitted, closes the active effort.

    Args:
        id: Effort ID to close. If omitted, closes the active effort.
    """
    raw = close_effort(
        session_dir=_get_session_dir(),
        model=_get_model(),
        effort_id=_or_none(id),
        session_id=_get_session_id(),
    )
    _log_tool_call("mcp_close_effort", {"id": id or "(active)"})
    return _fmt_simple(raw)


@mcp.tool()
def mcp_effort_status() -> str:
    """List all efforts with their status, summaries, and token counts."""
    raw = effort_status(session_dir=_get_session_dir())
    _log_tool_call("mcp_effort_status", {})
    return _fmt_effort_status(raw)


@mcp.tool()
def mcp_search_efforts(query: str) -> str:
    """Search past efforts by keyword.

    Args:
        query: What to search for (topic, keywords, effort name)
    """
    raw = search_efforts(session_dir=_get_session_dir(), query=query)
    _log_tool_call("mcp_search_efforts", {"query": query})
    return _fmt_simple(raw)


@mcp.tool()
def mcp_reopen_effort(id: str) -> str:
    """Resume a concluded effort to continue working on it.

    Args:
        id: The concluded effort ID to reopen
    """
    raw = reopen_effort(session_dir=_get_session_dir(), effort_id=id)
    _log_tool_call("mcp_reopen_effort", {"id": id})
    return _fmt_simple(raw)


@mcp.tool()
def mcp_switch_effort(id: str) -> str:
    """Change which open effort is active.

    Args:
        id: The open effort ID to switch to
    """
    raw = switch_effort(session_dir=_get_session_dir(), effort_id=id)
    _log_tool_call("mcp_switch_effort", {"id": id})
    return _fmt_simple(raw)


def _fmt_ingest(result) -> str:
    """Format a PipelineResult for human-readable output."""
    lines = []

    if result.dry_run:
        lines.append("DRY RUN — no graph changes made")
        lines.append(f"Source: {result.source_path}")
        lines.append(f"Chunks: {result.chunks_processed}/{result.chunks_total} processed")
        lines.append(f"Claims: {result.claims_extracted} would be extracted")
    else:
        lines.append(f"Ingested: {result.source_path}")
        lines.append(f"Nodes created: {len(result.nodes_created)}")
        lines.append(f"Chunks: {result.chunks_processed}/{result.chunks_total} processed")
        lines.append(f"Claims extracted: {result.claims_extracted}")
        if result.edges_created or result.contradictions_found:
            lines.append(
                f"Edges: {result.edges_created} created, "
                f"{result.contradictions_found} contradictions"
            )
        if result.conflicts:
            c = result.conflicts
            lines.append(
                f"Conflicts: {c.get('total', 0)} total "
                f"({c.get('auto_resolvable', 0)} auto, "
                f"{c.get('strong_recommendations', 0)} strong, "
                f"{c.get('ambiguous', 0)} ambiguous)"
            )

    if result.chunks_failed:
        lines.append(f"Chunks failed: {result.chunks_failed}")

    if result.errors:
        lines.append(f"Errors ({len(result.errors)}):")
        for e in result.errors[:5]:
            lines.append(f"  - {e}")
        if len(result.errors) > 5:
            lines.append(f"  ... and {len(result.errors) - 5} more")

    return "\n".join(lines)


@mcp.tool()
def mcp_ingest_document(
    file_path: str,
    dry_run: bool = False,
    skip_linking: bool = False,
) -> str:
    """Ingest a document into the knowledge graph.

    Parses the document, extracts knowledge claims via LLM, writes nodes,
    links them with full graph visibility, and reports conflicts.

    Args:
        file_path: Absolute path to the document file (.md, .pdf, .txt)
        dry_run: If true, parse and extract only — show what would happen without writing
        skip_linking: If true, skip the linking pass (faster, cheaper, no contradiction detection)
    """
    from .ingest import ingest_pipeline

    session_dir = _get_session_dir()
    model = _get_model()

    result = ingest_pipeline(
        file_path=file_path,
        session_dir=session_dir,
        model=model,
        dry_run=dry_run,
        skip_linking=skip_linking,
    )

    _log_tool_call("mcp_ingest_document", {
        "file_path": file_path,
        "dry_run": dry_run,
        "skip_linking": skip_linking,
    }, f"{len(result.nodes_created)} nodes")

    return _fmt_ingest(result)


def main():
    """Entry point for oi-mcp command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
