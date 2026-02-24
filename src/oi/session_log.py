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
