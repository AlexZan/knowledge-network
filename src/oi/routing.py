"""Stub module: oi.routing (auto-generated for TDD)."""

def route_message(state, message):
    """Route a message to appropriate handling.
    
    Args:
        state: ConversationState with artifacts
        message: User message to route
        
    Returns:
        "ambient" if no open efforts, otherwise "effort"
    """
    # If there are no open efforts, route to ambient
    if not state.get_open_efforts():
        return "ambient"
    
    # For now, default to effort if there are open efforts
    # (more sophisticated routing could be added later)
    return "effort"



# --- TDD Stubs (auto-generated, implement these) ---

def route_message_to_effort(state, arg1):
    raise NotImplementedError('route_message_to_effort')

def save_message_appropriately(session_dir, message, current_effort):
    raise NotImplementedError('save_message_appropriately')
