"""Context building for LLM prompts."""

from .models import ConversationState, Thread, Conclusion


SYSTEM_PROMPT = """You are a helpful AI assistant. Be concise and direct in your responses.

When the user asks a question, provide a clear answer. When they confirm understanding or thank you, the conversation on that topic is complete."""


def build_conclusions_context(conclusions: list[Conclusion]) -> str:
    """Build the conclusions section of the context."""
    if not conclusions:
        return ""

    lines = ["Previous conclusions from this conversation:"]
    for c in conclusions:
        lines.append(f"- {c.content}")
    return "\n".join(lines)


def build_thread_messages(thread: Thread) -> list[dict]:
    """Convert thread messages to LLM format."""
    return [
        {"role": msg.role, "content": msg.content}
        for msg in thread.messages
    ]


def build_context(state: ConversationState) -> list[dict]:
    """Build the full context for an LLM call.

    Structure:
    1. System prompt
    2. Conclusions (if any) as a system/context message
    3. Active thread messages
    """
    messages = []

    # System prompt with conclusions embedded
    conclusions_text = build_conclusions_context(state.get_active_conclusions())
    if conclusions_text:
        system_content = f"{SYSTEM_PROMPT}\n\n---\n{conclusions_text}\n---"
    else:
        system_content = SYSTEM_PROMPT

    messages.append({"role": "system", "content": system_content})

    # Active thread messages
    active_thread = state.get_active_thread()
    if active_thread:
        messages.extend(build_thread_messages(active_thread))

    return messages


def count_tokens(text: str) -> int:
    """Estimate token count. Rough approximation: ~4 chars per token."""
    # TODO: Use tiktoken for accurate counting if needed
    return len(text) // 4


def count_messages_tokens(messages: list[dict]) -> int:
    """Count tokens in a list of messages."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""))
    return total
