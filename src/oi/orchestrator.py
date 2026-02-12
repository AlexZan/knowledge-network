"""Stub module: oi.orchestrator (auto-generated for TDD)."""

from .llm import chat
from .chatlog import log_exchange

def process_turn(session_dir, user_message):
    """Process a single turn: get LLM response and log the exchange."""
    # Get LLM response
    messages = [{"role": "user", "content": user_message}]
    assistant_response = chat(messages)
    
    # Log the exchange as ambient
    log_exchange(session_dir, "ambient", "user", user_message, "assistant", assistant_response)
    
    return assistant_response

