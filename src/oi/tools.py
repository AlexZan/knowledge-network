"""Stub module: oi.tools (auto-generated for TDD)."""

def generate_effort_opening_response(effort_id):
    return f"Opened effort: {effort_id}"

def handle_open_effort_tool(effort_id, user_message, session_dir):
    from oi.storage import create_new_effort_file, update_manifest_for_new_effort
    from oi.effort_log import save_message_to_effort_log
    
    # Create effort file with user message
    create_new_effort_file(session_dir, effort_id, user_message)
    
    # Update manifest
    update_manifest_for_new_effort(session_dir, effort_id, f"Effort: {effort_id}")
    
    # Save assistant confirmation to effort log
    confirmation = generate_effort_opening_response(effort_id)
    save_message_to_effort_log(session_dir, effort_id, "assistant", confirmation)
    
    return {"status": "opened", "effort_id": effort_id}

