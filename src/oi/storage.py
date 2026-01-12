"""Simple JSON persistence for rapid prototyping."""

import json
from pathlib import Path
from .models import ConversationState, Artifact


DEFAULT_STATE_DIR = Path.home() / ".oi"


def get_state_path(state_dir: Path = DEFAULT_STATE_DIR) -> Path:
    """Get the path to the state file."""
    return state_dir / "state.json"


def ensure_state_dir(state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Ensure the state directory exists."""
    state_dir.mkdir(parents=True, exist_ok=True)


def save_state(state: ConversationState, state_dir: Path = DEFAULT_STATE_DIR) -> None:
    """Save conversation state to disk."""
    ensure_state_dir(state_dir)
    state_path = get_state_path(state_dir)
    state_path.write_text(state.model_dump_json(indent=2))


def load_state(state_dir: Path = DEFAULT_STATE_DIR) -> ConversationState:
    """Load conversation state from disk, or return empty state if none exists.

    Handles migration from legacy format (threads/conclusions) to new format (artifacts only).
    """
    state_path = get_state_path(state_dir)
    if not state_path.exists():
        return ConversationState()

    data = json.loads(state_path.read_text())

    # Check if this is legacy format (has threads/conclusions)
    if "threads" in data or "conclusions" in data:
        # Migrate: extract artifacts, ignore legacy fields
        artifacts = data.get("artifacts", [])
        return ConversationState(artifacts=[Artifact.model_validate(a) for a in artifacts])

    return ConversationState.model_validate(data)
