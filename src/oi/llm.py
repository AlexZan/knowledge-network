"""LLM interaction layer using litellm."""

import json
import os
from litellm import completion

from .schemas import get_extractable_types, build_extraction_type_list


# Default to Cerebras for fast testing (falls back to DeepSeek)
DEFAULT_MODEL = os.environ.get("OI_MODEL", "cerebras/gpt-oss-120b")


def chat(messages: list[dict], model: str = DEFAULT_MODEL, temperature: float = None) -> str:
    """Send messages to LLM and get response text."""
    kwargs = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    response = completion(**kwargs)
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


def extract_knowledge(effort_content: str, effort_id: str, model: str = DEFAULT_MODEL) -> list[dict]:
    """Extract knowledge nodes from a concluded effort's raw log.

    Returns list of dicts: [{"node_type": ..., "summary": ...}, ...]
    Returns empty list on failure (best-effort).
    """
    messages = [
        {"role": "system", "content": (
            "You extract permanent knowledge from conversation logs. "
            "Respond ONLY with a JSON array. No explanation, no markdown, no prose."
        )},
        {"role": "user", "content": (
            "Extract 0-5 knowledge nodes from this effort log worth remembering permanently.\n\n"
            "Rules:\n"
            "- Only extract facts, preferences, or decisions that are general and reusable\n"
            "- Skip transient details, in-progress discussion, and effort-specific mechanics\n"
            "- Each summary must be self-contained (no pronouns like 'it', 'this')\n"
            f"- {build_extraction_type_list()}\n\n"
            "Respond with ONLY a JSON array:\n"
            '[{"node_type": "fact", "summary": "..."}, {"node_type": "decision", "summary": "..."}]\n'
            "If nothing is worth extracting, respond with: []\n\n"
            f"Effort: {effort_id}\n\n"
            f"{effort_content}"
        )}
    ]
    try:
        raw = chat(messages, model)
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        nodes = json.loads(text)
        if not isinstance(nodes, list):
            return []
        valid = []
        for n in nodes:
            if (isinstance(n, dict)
                    and n.get("node_type") in get_extractable_types()
                    and isinstance(n.get("summary"), str)
                    and n["summary"].strip()):
                valid.append({"node_type": n["node_type"], "summary": n["summary"].strip()})
        return valid
    except Exception:
        return []


