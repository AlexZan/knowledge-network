"""Effort management - opening, updating, and concluding efforts."""


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

def add_assistant_confirmation_to_effort(session_dir, effort_id, confirmation_message):
    raise NotImplementedError('add_assistant_confirmation_to_effort')
