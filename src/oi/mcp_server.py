"""MCP server exposing knowledge graph tools for Claude Code.

Thin wrapper — each tool delegates to existing functions in tools.py / knowledge.py.
Uses stdio transport (Claude Code spawns as subprocess).
"""

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from .knowledge import add_knowledge, query_knowledge
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


# --- Formatting helpers ---

def _fmt_add(raw: str) -> str:
    d = json.loads(raw)
    if "error" in d:
        return f"Error: {d['error']}"
    lines = [f"Added {d['node_id']} [{d['node_type']}]: {d['summary']}"]
    conf = d.get("confidence", {})
    if conf:
        lines.append(f"Confidence: {conf.get('level', '?')}")
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
) -> str:
    """Add a fact, preference, or decision to the knowledge graph.

    Args:
        node_type: Type of knowledge node (e.g. fact, preference, decision)
        summary: Concise summary of the knowledge
        source: Where this knowledge came from (effort name, conversation context)
        related_to: Comma-separated IDs of related existing nodes
        edge_type: Relationship type to related_to nodes (e.g. supports, contradicts)
        supersedes: Comma-separated node IDs to mark as superseded by this new node
    """
    related_list = [r.strip() for r in related_to.split(",") if r.strip()] or None
    supersedes_list = [s.strip() for s in supersedes.split(",") if s.strip()] or None

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
    )
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
    return _fmt_query(raw)


@mcp.tool()
def mcp_open_effort(name: str) -> str:
    """Start tracking focused work on a topic.

    Args:
        name: Short kebab-case name for the effort (e.g. 'auth-bug', 'guild-feature')
    """
    raw = open_effort(session_dir=_get_session_dir(), name=name)
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
    return _fmt_simple(raw)


@mcp.tool()
def mcp_effort_status() -> str:
    """List all efforts with their status, summaries, and token counts."""
    raw = effort_status(session_dir=_get_session_dir())
    return _fmt_effort_status(raw)


@mcp.tool()
def mcp_search_efforts(query: str) -> str:
    """Search past efforts by keyword.

    Args:
        query: What to search for (topic, keywords, effort name)
    """
    raw = search_efforts(session_dir=_get_session_dir(), query=query)
    return _fmt_simple(raw)


@mcp.tool()
def mcp_reopen_effort(id: str) -> str:
    """Resume a concluded effort to continue working on it.

    Args:
        id: The concluded effort ID to reopen
    """
    raw = reopen_effort(session_dir=_get_session_dir(), effort_id=id)
    return _fmt_simple(raw)


@mcp.tool()
def mcp_switch_effort(id: str) -> str:
    """Change which open effort is active.

    Args:
        id: The open effort ID to switch to
    """
    raw = switch_effort(session_dir=_get_session_dir(), effort_id=id)
    return _fmt_simple(raw)


def main():
    """Entry point for oi-mcp command."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
