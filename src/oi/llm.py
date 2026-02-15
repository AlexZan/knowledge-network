"""LLM interaction layer using litellm."""

import os
from pathlib import Path
from litellm import completion


# Default to DeepSeek for free testing
DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")

# Prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text(encoding="utf-8").strip()


def chat(messages: list[dict], model: str = DEFAULT_MODEL) -> str:
    """Send messages to LLM and get response text."""
    response = completion(model=model, messages=messages)
    return response.choices[0].message.content


def chat_with_tools(messages: list[dict], tools: list[dict], model: str = DEFAULT_MODEL):
    """Send messages to LLM with tool definitions.

    Returns the full response message object (may contain tool_calls).
    """
    response = completion(model=model, messages=messages, tools=tools)
    return response.choices[0].message


def summarize_effort(effort_content: str, model: str = DEFAULT_MODEL) -> str:
    """Summarize an effort's raw log into a concise paragraph."""
    messages = [
        {"role": "system", "content": "You summarize conversations concisely."},
        {"role": "user", "content": (
            "Summarize this conversation into a concise paragraph.\n"
            "Capture: what was worked on, key findings, resolution.\n"
            "Keep it under 100 tokens.\n\n"
            f"{effort_content}"
        )}
    ]
    return chat(messages, model)


