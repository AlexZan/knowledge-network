"""LLM interaction layer using litellm."""

import os
from pathlib import Path
from litellm import completion


# Default to DeepSeek for free testing
DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")

# Prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt from the prompts directory.

    Args:
        name: Prompt filename (without .md extension)

    Returns:
        The prompt text
    """
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text(encoding="utf-8").strip()


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
        A concise knowledge statement extracted from the conversation
    """
    extraction_prompt = load_prompt("conclusion_extraction")

    # Format the thread for the prompt
    thread_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in thread_messages
        if msg['role'] != 'system'
    ])

    messages = [
        {"role": "system", "content": "You extract knowledge from conversations."},
        {"role": "user", "content": f"{extraction_prompt}\n\nConversation:\n{thread_text}"}
    ]

    return chat(messages, model)


# --- TDD Stubs (auto-generated, implement these) ---

def create_effort_summary(effort_content, arg1):
    raise NotImplementedError('create_effort_summary')
