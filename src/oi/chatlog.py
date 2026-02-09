"""Raw chat log - append-only permanent record."""

import json
from pathlib import Path
from datetime import datetime
from typing import Any

DEFAULT_STATE_DIR = Path.home() / ".oi"


def get_chatlog_path(state_dir: Path = DEFAULT_STATE_DIR) -> Path:
    """Get the path to the chat log file."""
    return state_dir / "chatlog.jsonl"


def append_exchange(
    user_message: str,
    assistant_message: str,
    metadata: dict[str, Any] | None = None,
    state_dir: Path = DEFAULT_STATE_DIR
) -> None:
    """Append a user/assistant exchange to the raw chat log.

    This is permanent, append-only storage. Never modified or compacted.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    chatlog_path = get_chatlog_path(state_dir)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user_message,
        "assistant": assistant_message,
    }
    if metadata:
        entry["metadata"] = metadata

    with open(chatlog_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_recent(
    limit: int = 10,
    state_dir: Path = DEFAULT_STATE_DIR
) -> list[dict[str, Any]]:
    """Read the most recent exchanges from the chat log.

    Reads from the end of the file for efficiency.
    """
    chatlog_path = get_chatlog_path(state_dir)
    if not chatlog_path.exists():
        return []

    # Read all lines and take last N (simple approach for now)
    # TODO: For large files, read backwards efficiently
    with open(chatlog_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    recent_lines = lines[-limit:] if len(lines) > limit else lines
    return [json.loads(line) for line in recent_lines]


def search(
    query: str,
    state_dir: Path = DEFAULT_STATE_DIR
) -> list[dict[str, Any]]:
    """Search the chat log for matching exchanges.

    Simple text search for now.
    """
    chatlog_path = get_chatlog_path(state_dir)
    if not chatlog_path.exists():
        return []

    results = []
    query_lower = query.lower()

    with open(chatlog_path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if query_lower in entry.get("user", "").lower() or \
               query_lower in entry.get("assistant", "").lower():
                results.append(entry)

    return results


# --- TDD Stubs (auto-generated, implement these) ---

def log_exchange(session_dir, arg1, arg2, arg3, arg4, arg5):
    raise NotImplementedError('log_exchange')


# --- TDD Stubs (auto-generated, implement these) ---

def save_ambient_exchange(role, content, raw_log):
    raise NotImplementedError('save_ambient_exchange')

def save_ambient_message(state, message, raw_log):
    raise NotImplementedError('save_ambient_message')

def save_ambient_response(response, raw_log):
    raise NotImplementedError('save_ambient_response')
