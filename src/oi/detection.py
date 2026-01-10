"""Conclusion detection - determines if user response indicates resolution."""

import os
from litellm import completion


DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")

# Patterns that indicate disagreement (keep thread open)
DISAGREEMENT_PATTERNS = [
    "no,", "no ", "nope", "not quite", "not really",
    "that's wrong", "that's not", "that doesn't",
    "i don't think", "i disagree",
    "but what about", "what about", "what if",
    "are you sure", "actually,", "actually ",
    "i already tried", "doesn't work", "didn't work",
    "that's incorrect", "incorrect",
]


def is_disagreement_simple(user_message: str) -> bool:
    """Simple pattern-based disagreement detection.

    Returns True if the message looks like disagreement.
    """
    lower = user_message.lower().strip()

    for pattern in DISAGREEMENT_PATTERNS:
        if pattern in lower:
            return True

    return False


def is_disagreement_llm(user_message: str, context: str = "", model: str = DEFAULT_MODEL) -> bool:
    """LLM-based disagreement detection for ambiguous cases.

    Args:
        user_message: The user's response to check
        context: Recent conversation context for better understanding
        model: Model to use for detection

    Returns:
        True if the message indicates disagreement/pushback
    """
    prompt = f"""Analyze this user message and determine if they are DISAGREEING with or PUSHING BACK on a previous answer.

User message: "{user_message}"

Respond with only "DISAGREE" or "ACCEPT".
- DISAGREE: User is questioning, challenging, or rejecting the answer
- ACCEPT: User is accepting, thanking, moving on, or asking something new"""

    messages = [
        {"role": "system", "content": "You classify user responses. Respond with only DISAGREE or ACCEPT."},
        {"role": "user", "content": prompt}
    ]

    response = completion(model=model, messages=messages)
    result = response.choices[0].message.content.strip().upper()

    return "DISAGREE" in result


def is_disagreement(user_message: str, use_llm: bool = False, model: str = DEFAULT_MODEL) -> bool:
    """Detect if user message indicates disagreement.

    Args:
        user_message: The user's response
        use_llm: Whether to use LLM for ambiguous cases
        model: Model to use if LLM detection is enabled

    Returns:
        True if user is disagreeing (thread should stay open)
    """
    # First try simple pattern matching
    if is_disagreement_simple(user_message):
        return True

    # For short accepting messages, don't bother with LLM
    lower = user_message.lower().strip()
    accepting_phrases = ["thanks", "thank you", "got it", "makes sense", "ok", "okay", "perfect", "great"]
    if any(phrase in lower for phrase in accepting_phrases):
        return False

    # Use LLM for ambiguous cases if enabled
    if use_llm:
        return is_disagreement_llm(user_message, model=model)

    # Default: not disagreement (will trigger conclusion)
    return False
