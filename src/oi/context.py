"""Build context strings for LLM from conversation state and messages."""

import json
from pathlib import Path
from oi.models import ConversationState


def build_context(state: ConversationState, recent_messages: list) -> str:
    """Build context string for LLM from state and recent messages.

    Args:
        state: ConversationState with artifacts
        recent_messages: List of recent message dicts with 'role' and 'content'

    Returns:
        String containing formatted context for LLM
    """
    sections = []

    # Section 1: Open Efforts (current work) - highest priority
    open_efforts = state.get_open_efforts()
    if open_efforts:
        sections.append("# Open Efforts (Current Work)")
        for effort in open_efforts:
            sections.append(f"- {effort.summary}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 2: Resolved Artifacts (past work with conclusions)
    resolved_efforts = state.get_resolved_efforts()
    if resolved_efforts:
        sections.append("# Resolved Efforts (Past Work)")
        for effort in resolved_efforts:
            sections.append(f"- {effort.summary}")
            if effort.resolution:
                sections.append(f"  Resolution: {effort.resolution}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 3: Recent Messages
    if recent_messages:
        sections.append("# Recent Conversation")
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            sections.append(f"{role.capitalize()}: {content}")
        sections.append("")

    return "\n".join(sections)


# --- TDD Stubs (auto-generated, implement these) ---

def build_ambient_context(session_dir, user_message):
    """Build context for ambient (non-effort) response.
    
    Args:
        session_dir: Path to session directory
        user_message: User message that triggered ambient response
        
    Returns:
        String containing formatted context for LLM
    """
    sections = []
    
    # Add the interruption message itself
    sections.append("# Recent Chat")
    sections.append(f"user: {user_message}")
    sections.append("")
    
    # Add recent ambient chat history from raw.jsonl
    raw_log = session_dir / "raw.jsonl"
    if raw_log.exists():
        try:
            with open(raw_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Read lines in reverse order to show most recent first
            for line in reversed(lines):
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    role = entry.get('role', 'unknown')
                    content = entry.get('content', '')
                    sections.append(f"{role.capitalize()}: {content}")
        except (json.JSONDecodeError, IOError):
            pass
    
    return "\n".join(sections)


# --- TDD Stubs (auto-generated, implement these) ---

def format_conclusion_confirmation(effort_id, summary):
    """Format a confirmation message when concluding an effort.
    
    Args:
        effort_id: Unique identifier for the effort
        summary: Summary of the effort
        
    Returns:
        String containing confirmation message
    """
    return f"I've concluded the effort '{effort_id}' ({summary})."


# --- TDD Stubs (auto-generated, implement these) ---

def build_turn_context(state, session_dir):
    """Build context for a turn, including open effort logs.
    
    Args:
        state: ConversationState with artifacts
        session_dir: Path to session directory
        
    Returns:
        String containing formatted context for LLM
    """
    sections = []

    # Read manifest for effort summaries
    manifest_path = session_dir / "manifest.yaml"
    manifest_efforts = []
    if manifest_path.exists():
        import yaml
        manifest = yaml.safe_load(manifest_path.read_text())
        manifest_efforts = manifest.get("efforts", [])

    # Section 1: Open Efforts (current work) - highest priority
    # Get open efforts from manifest and state
    open_in_manifest = {e["id"]: e for e in manifest_efforts if e.get("status") == "open"}
    open_in_state = {effort.id: effort for effort in state.get_open_efforts()}
    
    # Combine: all effort ids that are open in either manifest or state
    all_open_ids = set(open_in_manifest.keys()) | set(open_in_state.keys())
    
    if all_open_ids:
        sections.append("# Open Efforts (Current Work)")
        for effort_id in all_open_ids:
            # Prefer summary from manifest, then state
            summary = ""
            if effort_id in open_in_manifest:
                summary = open_in_manifest[effort_id].get("summary", "")
            elif effort_id in open_in_state:
                summary = open_in_state[effort_id].summary
            else:
                continue
            
            sections.append(f"- {summary}")
            
            # Include the effort's raw log content if the file exists
            effort_log_path = session_dir / "efforts" / f"{effort_id}.jsonl"
            if effort_log_path.exists():
                sections.append("  Recent messages in this effort:")
                try:
                    with open(effort_log_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for line in lines:
                        entry = json.loads(line.strip())
                        role = entry.get('role', 'unknown')
                        content = entry.get('content', '')
                        sections.append(f"    {role.capitalize()}: {content}")
                except (json.JSONDecodeError, IOError):
                    pass
            sections.append("")
        sections.append("")

    # Section 2: Concluded Efforts from manifest (past work)
    concluded_from_manifest = [e for e in manifest_efforts if e.get("status") == "concluded"]
    # Also include concluded efforts from state that might not be in manifest
    concluded_from_state = []
    for artifact in state.artifacts:
        if artifact.artifact_type == "effort" and artifact.status == "resolved":
            concluded_from_state.append({
                "id": artifact.id,
                "summary": artifact.summary
            })
    
    # Combine manifest and state concluded efforts, avoiding duplicates
    all_concluded = concluded_from_manifest.copy()
    for state_effort in concluded_from_state:
        if not any(e.get("id") == state_effort["id"] for e in concluded_from_manifest):
            all_concluded.append(state_effort)
    
    if all_concluded:
        sections.append("# Resolved Efforts (Past Work)")
        for effort in all_concluded:
            sections.append(f"- {effort['id']}: {effort.get('summary', '')}")
        sections.append("")

    # Section 3: Recent Conversation (ambient messages from raw.jsonl)
    raw_log = session_dir / "raw.jsonl"
    if raw_log.exists():
        sections.append("# Recent Conversation")
        try:
            with open(raw_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Read lines in reverse order to show most recent first
            for line in reversed(lines):
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    role = entry.get('role', 'unknown')
                    content = entry.get('content', '')
                    sections.append(f"{role.capitalize()}: {content}")
        except (json.JSONDecodeError, IOError):
            pass
        sections.append("")

    return "\n".join(sections)


# --- TDD Stubs (auto-generated, implement these) ---

def build_conversation_context(state, raw_log):
    """Build conversation context from state and raw chat log.

    Args:
        state: ConversationState with artifacts
        raw_log: Path to raw.jsonl file with ambient exchanges

    Returns:
        String containing formatted context for LLM
    """
    sections = []

    # Section 1: Open Efforts (current work) - highest priority
    open_efforts = state.get_open_efforts()
    if open_efforts:
        sections.append("# Open Efforts (Current Work)")
        for effort in open_efforts:
            sections.append(f"- {effort.summary}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 2: Resolved Artifacts (past work with conclusions)
    resolved_efforts = state.get_resolved_efforts()
    if resolved_efforts:
        sections.append("# Resolved Efforts (Past Work)")
        for effort in resolved_efforts:
            sections.append(f"- {effort.summary}")
            if effort.resolution:
                sections.append(f"  Resolution: {effort.resolution}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 3: Ambient Chat (from raw log)
    if raw_log and isinstance(raw_log, Path) and raw_log.exists():
        sections.append("# Recent Chat")
        try:
            with open(raw_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Read lines in reverse order to show most recent first
            for line in reversed(lines):
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    role = entry.get('role', 'unknown')
                    content = entry.get('content', '')
                    sections.append(f"{role.capitalize()}: {content}")
        except (json.JSONDecodeError, IOError):
            pass
        sections.append("")

    return "\n".join(sections)
