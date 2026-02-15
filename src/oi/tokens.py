"""Token counting and statistics utilities."""

import tiktoken


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in a text string.

    Args:
        text: Text to count tokens in
        model: Model to use for tokenization (default: gpt-4)

    Returns:
        Number of tokens
    """
    if not text:
        return 0

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base (GPT-4 encoding)
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def count_tokens_in_messages(messages: list[dict], model: str = "gpt-4") -> int:
    """Count tokens in a list of messages.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model to use for tokenization

    Returns:
        Total token count across all messages
    """
    total = 0
    for msg in messages:
        # Count tokens in content
        content = msg.get("content", "")
        total += count_tokens(content, model)

        # Add overhead for message structure (role, formatting)
        # OpenAI API adds ~4 tokens per message for formatting
        total += 4

    # Add 3 tokens for message separator
    total += 3

    return total


