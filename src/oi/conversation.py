"""Main conversation loop."""

import uuid
from datetime import datetime

from .models import ConversationState, Thread, Message, Conclusion
from .storage import load_state, save_state
from .context import build_context, count_messages_tokens
from .detection import is_disagreement
from .llm import chat, extract_conclusion


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())[:8]


def create_thread() -> Thread:
    """Create a new thread."""
    return Thread(id=generate_id())


def add_message(thread: Thread, role: str, content: str) -> Message:
    """Add a message to a thread."""
    msg = Message(role=role, content=content)
    thread.messages.append(msg)
    return msg


def conclude_thread(
    state: ConversationState,
    thread: Thread,
    model: str
) -> tuple[Conclusion, int, int]:
    """Conclude a thread and extract a summary.

    Returns:
        Tuple of (conclusion, raw_tokens, compacted_tokens)
    """
    # Get thread messages for extraction
    thread_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in thread.messages
    ]

    # Count raw tokens (what we would have used)
    raw_tokens = count_messages_tokens(thread_messages)

    # Extract conclusion
    summary = extract_conclusion(thread_messages, model)

    # Create conclusion
    conclusion = Conclusion(
        id=generate_id(),
        content=summary,
        source_thread_id=thread.id,
        created=datetime.now()
    )

    # Update thread status
    thread.status = "concluded"
    thread.conclusion_id = conclusion.id

    # Add to state
    state.conclusions.append(conclusion)

    # Count compacted tokens
    compacted_tokens = count_messages_tokens([{"role": "system", "content": summary}])

    # Update stats
    state.token_stats.total_raw += raw_tokens
    state.token_stats.total_compacted += compacted_tokens

    return conclusion, raw_tokens, compacted_tokens


def process_turn(
    state: ConversationState,
    user_input: str,
    model: str,
    use_llm_detection: bool = False
) -> tuple[str, Conclusion | None, tuple[int, int] | None]:
    """Process a single conversation turn.

    Args:
        state: Current conversation state
        user_input: User's message
        model: LLM model to use
        use_llm_detection: Whether to use LLM for disagreement detection

    Returns:
        Tuple of (ai_response, conclusion_if_extracted, token_stats_if_concluded)
    """
    conclusion = None
    token_stats = None

    # Get or create active thread
    active_thread = state.get_active_thread()

    # Check if this is a response that might conclude previous thread
    if active_thread and len(active_thread.messages) >= 2:
        # There's an existing exchange - check for conclusion
        if not is_disagreement(user_input, use_llm=use_llm_detection, model=model):
            # User accepted - conclude and start new thread
            conclusion, raw, compacted = conclude_thread(state, active_thread, model)
            token_stats = (raw, compacted)
            active_thread = None

    # Create new thread if needed
    if active_thread is None:
        active_thread = create_thread()
        state.threads.append(active_thread)
        state.active_thread_id = active_thread.id

    # Add user message
    add_message(active_thread, "user", user_input)

    # Build context and get response
    context = build_context(state)
    ai_response = chat(context, model)

    # Add AI response
    add_message(active_thread, "assistant", ai_response)

    # Save state
    save_state(state)

    return ai_response, conclusion, token_stats
