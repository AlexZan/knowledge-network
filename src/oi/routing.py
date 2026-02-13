"""Stub module: oi.routing (auto-generated for TDD)."""

def route_message(state, message):
    """Route a message to appropriate handling.
    
    Args:
        state: ConversationState with artifacts
        message: User message to route
        
    Returns:
        "ambient" if no open efforts or message doesn't relate to any open effort, 
        otherwise the effort ID of the first open effort
    """
    # If there are no open efforts, route to ambient
    open_efforts = state.get_open_efforts()
    if not open_efforts:
        return "ambient"
    
    # Check if the message relates to the open effort
    # For now, simple check: if message contains effort-related terms
    for effort in open_efforts:
        # Simple keyword matching - in real implementation would be more sophisticated
        effort_terms = set(effort.summary.lower().split())
        message_terms = set(message.lower().split())
        common_terms = effort_terms.intersection(message_terms)
        
        # If there are common terms, assume it's related
        if common_terms and len(common_terms) > 0:
            return effort.id
    
    # If no relation found, treat as ambient interruption
    return "ambient"



# --- TDD Stubs (auto-generated, implement these) ---

def route_message_to_effort(state, arg1):
    raise NotImplementedError('route_message_to_effort')

def save_message_appropriately(session_dir, message, current_effort):
    raise NotImplementedError('save_message_appropriately')
