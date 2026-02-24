"""Session audit logs: chronological record of messages, tool calls, and node events.

Each CLI invocation creates a session log file (JSONL) with timestamped entries.
"""

import json
from pathlib import Path
from datetime import datetime


def create_session_log(session_dir: Path) -> str:
    """Create a new session log file. Returns the session_id (timestamp string)."""
    now = datetime.now()
    session_id = now.strftime("%Y-%m-%dT%H-%M-%S")
    sessions_dir = session_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    log_path = sessions_dir / f"{session_id}.jsonl"
    # Create empty file
    log_path.touch()
    return session_id


def log_event(session_dir: Path, session_id: str, event_type: str, data: dict):
    """Append a typed event to the session log."""
    sessions_dir = session_dir / "sessions"
    log_path = sessions_dir / f"{session_id}.jsonl"
    if not log_path.exists():
        return

    entry = {
        "ts": datetime.now().isoformat(),
        "type": event_type,
        "data": data,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


NODE_CONTEXT_WINDOW = 5


def read_session_log(session_dir: Path, session_id: str) -> list[dict]:
    """Read all events from a session log. Returns list of event dicts."""
    sessions_dir = session_dir / "sessions"
    log_path = sessions_dir / f"{session_id}.jsonl"
    if not log_path.exists():
        return []

    events = []
    text = log_path.read_text(encoding="utf-8").strip()
    if text:
        for line in text.split("\n"):
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def extract_node_context(session_dir: Path, session_id: str, node_id: str, window: int = NODE_CONTEXT_WINDOW) -> list[dict]:
    """Extract conversation context around a node-created event from a session log.

    Finds the node-created event for the given node_id, then collects preceding
    user-message and assistant-message events (up to `window` messages).
    Returns [{role, content}] pairs — same format as effort JSONL messages.

    Returns empty list if session or node event not found.
    """
    events = read_session_log(session_dir, session_id)
    if not events:
        return []

    # Find the index of the node-created event for this node_id
    node_event_idx = None
    for i, event in enumerate(events):
        if (event.get("type") == "node-created"
                and event.get("data", {}).get("node_id") == node_id):
            node_event_idx = i
            break

    if node_event_idx is None:
        return []

    # Collect preceding message events (user-message and assistant-message)
    message_types = {"user-message", "assistant-message"}
    preceding_messages = []
    for i in range(node_event_idx - 1, -1, -1):
        if events[i].get("type") in message_types:
            role = "user" if events[i]["type"] == "user-message" else "assistant"
            preceding_messages.append({
                "role": role,
                "content": events[i]["data"]["content"],
            })
            if len(preceding_messages) >= window:
                break

    # Reverse to chronological order
    preceding_messages.reverse()
    return preceding_messages
