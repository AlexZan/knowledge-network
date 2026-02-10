"""Effort management - opening, updating, and concluding efforts."""

import yaml
from .models import Artifact


# --- TDD Stubs (auto-generated, implement these) ---

def open_new_effort(session_dir, effort_id, user_message):
    """Open a new effort by creating its log file.
    
    Args:
        session_dir: Path to session directory
        effort_id: Unique identifier for the effort
        user_message: User message that opened the effort
    """
    efforts_dir = session_dir / "efforts"
    efforts_dir.mkdir(parents=True, exist_ok=True)
    
    effort_file = efforts_dir / f"{effort_id}.jsonl"
    
    # Save the opening message to the effort log
    from datetime import datetime
    import json
    
    entry = {
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(effort_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Update manifest.yaml
    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text())
    else:
        manifest = {"efforts": []}
    
    now = datetime.now().isoformat()
    
    # Check if effort already exists in manifest
    effort_found = False
    for effort in manifest["efforts"]:
        if effort["id"] == effort_id:
            effort["status"] = "open"
            effort["updated"] = now
            effort_found = True
            break
    
    if not effort_found:
        # Add new effort entry
        manifest["efforts"].append({
            "id": effort_id,
            "status": "open",
            "created": now,
            "updated": now
        })
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f)

def add_assistant_confirmation_to_effort(session_dir, effort_id, confirmation_message):
    """Add assistant confirmation message to an effort log.
    
    Args:
        session_dir: Path to session directory
        effort_id: Unique identifier for the effort
        confirmation_message: Assistant message confirming effort opening
    """
    efforts_dir = session_dir / "efforts"
    effort_file = efforts_dir / f"{effort_id}.jsonl"
    
    if not effort_file.exists():
        return
    
    from datetime import datetime
    import json
    
    entry = {
        "role": "assistant",
        "content": confirmation_message,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(effort_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# --- TDD Stubs (auto-generated, implement these) ---

def conclude_effort(arg0, session_dir, summary):
    raise NotImplementedError('conclude_effort')


# --- TDD Stubs (auto-generated, implement these) ---

def start_new_effort(state, session_dir, user_message, assistant_response):
    """Start a new effort by creating an effort file and logging the initial exchange.
    
    Args:
        state: ConversationState to update with the new effort artifact
        session_dir: Path to session directory
        user_message: User message that opened the effort
        assistant_response: Assistant response confirming the effort opening
        
    Returns:
        The effort_id of the newly created effort.
    """
    # Extract effort_id from assistant_response (assuming format "Opening effort: <effort_id>")
    if assistant_response.startswith("Opening effort: "):
        effort_id = assistant_response[len("Opening effort: "):].strip()
    else:
        # Fallback: generate a kebab-case effort_id from the first few words of user_message
        import re
        words = user_message.split()[:3]
        effort_id = "-".join(re.sub(r'[^a-z0-9]', '', word.lower()) for word in words if word)
    
    # Open the effort with the user message
    open_new_effort(session_dir, effort_id, user_message)
    
    # Add the assistant confirmation
    add_assistant_confirmation_to_effort(session_dir, effort_id, assistant_response)
    
    # Update manifest with raw_file path
    import yaml
    from datetime import datetime
    
    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text())
    else:
        manifest = {"efforts": []}
    
    now = datetime.now().isoformat()
    
    # Check if effort already exists in manifest
    effort_found = False
    for effort in manifest["efforts"]:
        if effort["id"] == effort_id:
            effort["status"] = "open"
            effort["updated"] = now
            effort["raw_file"] = f"efforts/{effort_id}.jsonl"
            effort_found = True
            break
    
    if not effort_found:
        # Add new effort entry
        manifest["efforts"].append({
            "id": effort_id,
            "status": "open",
            "raw_file": f"efforts/{effort_id}.jsonl",
            "created": now,
            "updated": now
        })
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f)
    
    # Create a new artifact for the effort and add it to the state
    artifact = Artifact(
        id=effort_id,
        artifact_type="effort",
        summary=user_message,
        status="open"
    )
    state.artifacts.append(artifact)
    
    return effort_id
