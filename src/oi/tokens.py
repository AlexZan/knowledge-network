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


# --- TDD Stubs (auto-generated, implement these) ---

def measure_context_size(session_dir, arg1):
    raise NotImplementedError('measure_context_size')

def calculate_effort_savings(effort_id, session_dir, model="gpt-4"):
    """Calculate token savings percentage for a concluded effort.
    
    Args:
        effort_id: Unique identifier for the effort
        session_dir: Path to session directory
        model: Model to use for tokenization
        
    Returns:
        Float percentage savings (0-100)
    """
    from .llm import summarize_effort
    
    # Read effort log
    effort_log_path = session_dir / "efforts" / f"{effort_id}.jsonl"
    if not effort_log_path.exists():
        return 0.0
    
    with open(effort_log_path, 'r', encoding='utf-8') as f:
        effort_content = f.read()
    
    # Count raw tokens in effort log
    raw_tokens = count_tokens(effort_content, model)
    
    # Get summary from manifest
    import yaml
    manifest_path = session_dir / "manifest.yaml"
    if not manifest_path.exists():
        return 0.0
    
    manifest = yaml.safe_load(manifest_path.read_text())
    summary = ""
    for effort in manifest.get("efforts", []):
        if effort.get("id") == effort_id:
            summary = effort.get("summary", "")
            break
    
    if not summary:
        # Fallback to generating summary
        summary = summarize_effort(effort_content)
    
    # Count summary tokens
    summary_tokens = count_tokens(summary, model)
    
    if raw_tokens == 0:
        return 0.0
    
    savings = ((raw_tokens - summary_tokens) / raw_tokens) * 100
    return savings

def compare_effort_to_summary(arg0, session_dir, arg2):
    raise NotImplementedError('compare_effort_to_summary')
