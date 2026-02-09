"""Stub module: oi.effort_log (auto-generated for TDD)."""

def append_to_effort_log(session_dir, effort_id, user_message):
    raise NotImplementedError('append_to_effort_log')



# --- TDD Stubs (auto-generated, implement these) ---

def save_message_to_effort_log(session_dir, effort_id, role, content):
    """Save a message to an effort's raw log.
    
    Args:
        session_dir: Path to session directory
        effort_id: Unique identifier for the effort
        role: "user" or "assistant"
        content: Message content
    """
    efforts_dir = session_dir / "efforts"
    efforts_dir.mkdir(parents=True, exist_ok=True)
    
    effort_file = efforts_dir / f"{effort_id}.jsonl"
    
    import json
    from datetime import datetime
    
    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(effort_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
