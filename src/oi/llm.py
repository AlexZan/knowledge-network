"""LLM interaction layer using litellm."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from litellm import completion

from .schemas import get_extractable_types, build_extraction_type_list


# Default to Cerebras for fast testing (falls back to DeepSeek)
DEFAULT_MODEL = os.environ.get("OI_MODEL", "cerebras/gpt-oss-120b")


def _log_llm_call(phase: str, model: str, messages: list[dict], response: str, meta: dict | None = None) -> None:
    """Append one JSONL line to {OI_SESSION_DIR}/llm_log.jsonl. Silently fails on error."""
    session_dir = os.environ.get("OI_SESSION_DIR") or str(Path.home() / ".oi")
    if not session_dir:
        return
    try:
        path = Path(session_dir) / "llm_log.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "model": model,
            "prompt": messages,
            "response": response,
        }
        if meta:
            entry["meta"] = meta
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = None,
    phase: str = None,
    log_meta: dict = None,
) -> str:
    """Send messages to LLM and get response text."""
    kwargs = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    response = completion(**kwargs)
    text = response.choices[0].message.content
    if phase:
        _log_llm_call(phase, model, messages, text, log_meta)
    return text


def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    model: str = DEFAULT_MODEL,
    phase: str = None,
    log_meta: dict = None,
):
    """Send messages to LLM with tool definitions.

    Returns the full response message object (may contain tool_calls).
    """
    response = completion(model=model, messages=messages, tools=tools)
    msg = response.choices[0].message
    if phase:
        _log_llm_call(phase, model, messages, str(msg.content), log_meta)
    return msg


def summarize_effort(effort_content: str, effort_id: str = "", model: str = DEFAULT_MODEL) -> str:
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
    return chat(messages, model, phase="effort_summarize", log_meta={"effort_id": effort_id})


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
        raw = chat(messages, model, phase="effort_extract", log_meta={"effort_id": effort_id})
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
