"""Stub module: oi.orchestrator (auto-generated for TDD)."""

from .llm import chat
from .chatlog import log_exchange
from .efforts import open_new_effort, add_assistant_confirmation_to_effort

def process_turn(session_dir, user_message):
    """Process a single turn: get LLM response and log the exchange."""
    # Get LLM response
    messages = [{"role": "user", "content": user_message}]
    assistant_response = chat(messages)
    
    # Check if this is an effort opening
    if assistant_response.startswith("Opening effort: "):
        # Extract effort ID from the assistant response
        effort_id = assistant_response.split("Opening effort: ")[1].split("\n")[0].strip()
        # Open the effort and log the exchange to the effort log
        open_new_effort(session_dir, effort_id, user_message)
        add_assistant_confirmation_to_effort(session_dir, effort_id, assistant_response)
        # Do not log to ambient
        return assistant_response
    else:
        # Log the exchange as ambient
        log_exchange(session_dir, "ambient", "user", user_message, "assistant", assistant_response)
        return assistant_response

