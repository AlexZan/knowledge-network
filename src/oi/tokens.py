"""Token counting and statistics utilities."""

import tiktoken
from oi.models import TokenStats


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


def format_token_stats(stats: TokenStats) -> str:
    """Format token statistics for display.

    Expected format: [Tokens: 1,247 raw → 68 compacted | Savings: 95%]

    Args:
        stats: TokenStats object with total_raw and total_compacted

    Returns:
        Formatted string
    """
    raw = f"{stats.total_raw:,}"
    compacted = f"{stats.total_compacted:,}"
    savings = round(stats.savings_percent)

    return f"[Tokens: {raw} raw → {compacted} compacted | Savings: {savings}%]"


def calculate_effort_stats(messages: list[dict], artifact_text: str, model: str = "gpt-4") -> TokenStats:
    """Calculate token statistics for a single effort.

    Args:
        messages: List of messages in this effort
        artifact_text: The compacted artifact text
        model: Model to use for tokenization

    Returns:
        TokenStats with raw and compacted counts
    """
    raw_count = count_tokens_in_messages(messages, model)
    compacted_count = count_tokens(artifact_text, model)

    return TokenStats(
        total_raw=raw_count,
        total_compacted=compacted_count
    )
