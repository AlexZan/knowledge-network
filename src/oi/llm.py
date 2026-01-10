"""LLM interaction layer using litellm."""

import os
from litellm import completion


# Default to DeepSeek for free testing
DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")


def chat(messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """Send messages to LLM and get response.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model identifier (litellm format)

    Returns:
        The assistant's response text
    """
    response = completion(model=model, messages=messages)
    return response.choices[0].message.content


def extract_conclusion(thread_messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """Ask LLM to extract a conclusion from a resolved thread.

    Args:
        thread_messages: The messages from the concluded thread
        model: Model identifier

    Returns:
        A concise summary of the resolution
    """
    extraction_prompt = """Summarize the resolution of this conversation in one concise sentence.
Focus on: what was the problem/question and what was the solution/answer.
Be brief - this summary will be used as context for future conversations.

Conversation:
"""

    # Format the thread for the prompt
    thread_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in thread_messages
        if msg['role'] != 'system'
    ])

    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely."},
        {"role": "user", "content": extraction_prompt + thread_text}
    ]

    return chat(messages, model)
