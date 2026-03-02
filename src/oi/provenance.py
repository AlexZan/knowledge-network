"""Chatlog provenance discovery and URI construction.

Discovers active conversation logs from AI clients (Claude Code, etc.)
and constructs chatlog:// URIs for linking KG nodes to their source conversations.
"""

import os
from pathlib import Path


def discover_claude_code_chatlog() -> str | None:
    """Find the active Claude Code conversation file. Return chatlog:// URI or None.

    Scans ~/.claude/projects/ for the most recently modified .jsonl file.
    Returns URI in format: chatlog://claude-code/{session-id}:L{line_count}
    """
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return None

    # Find the most recently modified .jsonl file across all project dirs
    best_file = None
    best_mtime = 0.0

    for project_dir in claude_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            # Skip subagent files (they're in subdirectories, not direct children)
            mtime = jsonl_file.stat().st_mtime
            if mtime > best_mtime:
                best_mtime = mtime
                best_file = jsonl_file

    if best_file is None:
        return None

    # Session ID is the filename without extension
    session_id = best_file.stem

    # Count lines (append-only, so line count = current position)
    try:
        with open(best_file, "r", encoding="utf-8") as f:
            line_count = sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        line_count = 0

    return f"chatlog://claude-code/{session_id}:L{line_count}"


def resolve_chatlog_uri(uri: str) -> dict | None:
    """Parse a chatlog:// URI into components. Returns dict or None if invalid.

    Returns:
        {"client": "claude-code", "session_id": "abc123", "line": 2280, "path": Path(...)}
        or None if the URI is not a valid chatlog:// URI or the file doesn't exist.
    """
    if not uri.startswith("chatlog://"):
        return None

    rest = uri[len("chatlog://"):]

    # Parse client/session:Lline
    parts = rest.split("/", 1)
    if len(parts) != 2:
        return None

    client = parts[0]
    session_part = parts[1]

    # Parse session_id and optional line reference
    line = None
    if ":L" in session_part:
        session_id, line_str = session_part.rsplit(":L", 1)
        try:
            line = int(line_str)
        except ValueError:
            line = None
    else:
        session_id = session_part

    result = {"client": client, "session_id": session_id, "line": line}

    # Try to resolve to actual file path
    if client == "claude-code":
        claude_dir = Path.home() / ".claude" / "projects"
        if claude_dir.exists():
            for project_dir in claude_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                candidate = project_dir / f"{session_id}.jsonl"
                if candidate.exists():
                    result["path"] = candidate
                    break

    return result
