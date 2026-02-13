"""Stub module: oi.tools (auto-generated for TDD)."""

import litellm

def generate_effort_opening_response(effort_id):
    return f"Opened effort: {effort_id}"

def handle_open_effort_tool(effort_id, user_message, session_dir):
    from oi.storage import create_new_effort_file, update_manifest_for_new_effort
    from oi.effort_log import save_message_to_effort_log
    
    # Create effort file with user message
    create_new_effort_file(session_dir, effort_id, user_message)
    
    # Update manifest with summary from user message
    summary = f"Effort: {effort_id}"
    if user_message:
        # Use a more descriptive summary based on user message
        summary = user_message[:50] + "..." if len(user_message) > 50 else user_message
    update_manifest_for_new_effort(session_dir, effort_id, summary)
    
    # Save assistant confirmation to effort log
    confirmation = generate_effort_opening_response(effort_id)
    save_message_to_effort_log(session_dir, effort_id, "assistant", confirmation)
    
    return {"status": "opened", "effort_id": effort_id}



# --- TDD Stubs (auto-generated, implement these) ---

def should_conclude_effort(message, state_artifacts):
    """Check if a message indicates an effort should be concluded.
    
    Args:
        message: User message
        state_artifacts: List of artifact dicts from state
        
    Returns:
        effort_id if message concludes an effort, None otherwise
    """
    message_lower = message.lower()
    
    # Check for patterns like "X is done" or "X looks good"
    for artifact in state_artifacts:
        if artifact.get("artifact_type") == "effort" and artifact.get("status") == "open":
            effort_id = artifact.get("id")
            if effort_id:
                # Check if message contains effort_id followed by conclusion phrase
                if f"{effort_id} is done" in message_lower:
                    return effort_id
                if f"{effort_id} looks good" in message_lower:
                    return effort_id
    
    return None

def generate_conclusion_response(effort_id, summary):
    """Generate a confirmation response for concluding an effort.
    
    Args:
        effort_id: ID of the effort being concluded
        summary: Summary of the effort conclusion
        
    Returns:
        Assistant response text
    """
    return f"Concluding effort '{effort_id}' with summary: {summary}"
