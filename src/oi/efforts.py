"""Effort management - opening, updating, and concluding efforts."""

import yaml


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
    # Create empty file
    effort_file.touch()
    
    # Update manifest.yaml
    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text())
    else:
        manifest = {"efforts": []}
    
    from datetime import datetime
    now = datetime.now().isoformat()
    
    # Check if effort already exists in manifest
    for effort in manifest["efforts"]:
        if effort["id"] == effort_id:
            effort["status"] = "open"
            effort["updated"] = now
            break
    else:
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
    raise NotImplementedError('add_assistant_confirmation_to_effort')
