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


# --- TDD Stubs (auto-generated, implement these) ---

def save_exchange_and_update_state(session_dir, target, user_message, assistant_response, state):
    """Save an exchange and update state accordingly.
    
    Args:
        session_dir: Path to session directory
        target: "ambient" or effort ID
        user_message: User message content
        assistant_response: Assistant response content
        state: ConversationState to update
    """
    from .chatlog import log_exchange
    
    # Log the exchange to appropriate log file
    log_exchange(session_dir, target, "user", user_message, "assistant", assistant_response)
    
    # For ambient exchanges, no state update needed
    # For effort exchanges, the effort should already be in state
    # (This function doesn't modify the manifest - that's done by other functions)


# --- TDD Stubs (auto-generated, implement these) ---

def conclude_effort(effort_id, session_dir, resolution):
    """Conclude an effort by updating its status in the manifest.
    
    Args:
        effort_id: Unique identifier for the effort
        session_dir: Path to session directory
        resolution: Resolution text describing what was concluded
    """
    import yaml
    from datetime import datetime
    
    manifest_path = session_dir / "manifest.yaml"
    if not manifest_path.exists():
        return
    
    manifest = yaml.safe_load(manifest_path.read_text())
    if "efforts" not in manifest:
        return
    
    now = datetime.now().isoformat()
    
    for effort in manifest["efforts"]:
        if effort["id"] == effort_id:
            effort["status"] = "concluded"
            effort["updated"] = now
            if resolution:
                effort["resolution"] = resolution
            break
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f)

def save_to_effort_log(arg0, efforts_dir, arg2, user_message):
    raise NotImplementedError('save_to_effort_log')


# --- TDD Stubs (auto-generated, implement these) ---

def create_new_effort_file(session_dir, effort_id, arg2):
    raise NotImplementedError('create_new_effort_file')

def update_manifest_for_new_effort(session_dir, effort_id, effort_summary):
    raise NotImplementedError('update_manifest_for_new_effort')


# --- TDD Stubs (auto-generated, implement these) ---

def save_message_to_effort_log(session_dir, arg1, user_message):
    raise NotImplementedError('save_message_to_effort_log')

def add_effort_to_manifest(session_dir, arg1, arg2):
    raise NotImplementedError('add_effort_to_manifest')

def create_effort_file(session_dir, arg1):
    raise NotImplementedError('create_effort_file')
