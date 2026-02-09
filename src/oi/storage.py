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

def conclude_effort(effort_id, state, session_dir):
    """Conclude an effort by updating its status in the manifest.
    
    Args:
        effort_id: Unique identifier for the effort
        state: ConversationState containing the effort artifact
        session_dir: Path to session directory
    """
    import yaml
    from datetime import datetime
    
    # Read the effort log for summarization
    effort_log_path = session_dir / "efforts" / f"{effort_id}.jsonl"
    if effort_log_path.exists():
        with open(effort_log_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ""
    
    from .llm import summarize_effort
    summary = summarize_effort(content)
    
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
            if summary:
                effort["summary"] = summary
            break
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f)
    
    # Update the state to mark the artifact as resolved
    for artifact in state.artifacts:
        if artifact.id == effort_id and artifact.artifact_type == "effort":
            artifact.status = "resolved"
            artifact.updated = datetime.now()
            break

def save_to_effort_log(effort_id, efforts_dir, role, content):
    """Save a message to an effort's raw log.
    
    Args:
        effort_id: Unique identifier for the effort
        efforts_dir: Path to efforts directory
        role: "user" or "assistant"
        content: Message content
    """
    import json
    from datetime import datetime
    
    effort_file = efforts_dir / f"{effort_id}.jsonl"
    effort_file.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(effort_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# --- TDD Stubs (auto-generated, implement these) ---

def create_new_effort_file(session_dir, effort_id, user_message):
    """Create a new effort file with the opening user message.
    
    Args:
        session_dir: Path to session directory
        effort_id: Unique identifier for the effort
        user_message: User message that opened the effort
    """
    import json
    from datetime import datetime
    
    efforts_dir = session_dir / "efforts"
    efforts_dir.mkdir(parents=True, exist_ok=True)
    
    effort_file = efforts_dir / f"{effort_id}.jsonl"
    
    entry = {
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(effort_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def update_manifest_for_new_effort(session_dir, effort_id, effort_summary):
    raise NotImplementedError('update_manifest_for_new_effort')


# --- TDD Stubs (auto-generated, implement these) ---

def save_message_to_effort_log(session_dir, arg1, user_message):
    raise NotImplementedError('save_message_to_effort_log')

def add_effort_to_manifest(session_dir, arg1, arg2):
    raise NotImplementedError('add_effort_to_manifest')

def create_effort_file(session_dir, arg1):
    raise NotImplementedError('create_effort_file')
