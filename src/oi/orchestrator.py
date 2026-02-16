"""Orchestrator: handles each conversation turn with tool-calling flow.

Flow per turn:
1. Build working context (system prompt + ambient + manifest summaries + expanded raw + open effort raw)
2. Add user message
3. Send to LLM with tool definitions
4. If tool call: execute tool, send result back, get next response (loop)
5. Log messages to appropriate log (active effort or ambient)
6. Return assistant response
"""

import json
import yaml
from pathlib import Path
from datetime import datetime

from .llm import chat_with_tools, DEFAULT_MODEL
from .prompts import load_prompt
from .state import _load_expanded, increment_turn
from .tools import (
    TOOL_DEFINITIONS, execute_tool,
    get_active_effort, get_all_open_efforts,
)
from .decay import check_decay, DECAY_THRESHOLD


MAX_TOOL_ROUNDS = 3


def _log_message(session_dir: Path, effort_id: str | None, role: str, content: str):
    """Append a single message to the appropriate log file."""
    now = datetime.now().isoformat()
    entry = {"role": role, "content": content, "ts": now}

    if effort_id:
        log_file = session_dir / "efforts" / f"{effort_id}.jsonl"
    else:
        log_file = session_dir / "raw.jsonl"

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _read_jsonl_messages(filepath: Path) -> list[dict]:
    """Read a JSONL file and return list of {role, content} message dicts.

    Skips malformed lines rather than crashing the whole session.
    """
    messages = []
    if filepath.exists():
        text = filepath.read_text(encoding="utf-8").strip()
        if text:
            for line in text.split("\n"):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        messages.append({"role": entry["role"], "content": entry["content"]})
                    except (json.JSONDecodeError, KeyError):
                        continue
    return messages


def _build_messages(session_dir: Path) -> list[dict]:
    """Build the LLM message list from working context.

    Working Context = system_prompt + ambient + manifest_summaries (non-expanded)
                    + expanded_effort_raw + all_open_effort_raw (active last)
    """
    # System prompt
    system_prompt = load_prompt("system")

    # Read manifest for concluded effort summaries
    manifest_section = ""
    manifest_path = session_dir / "manifest.yaml"
    expanded = _load_expanded(session_dir)

    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        concluded = [e for e in manifest.get("efforts", []) if e.get("status") == "concluded"]
        # Only show summaries for non-expanded concluded efforts
        summary_efforts = [e for e in concluded if e["id"] not in expanded]
        if summary_efforts:
            parts = ["\nConcluded efforts (summaries only):"]
            for e in summary_efforts:
                parts.append(f"- {e['id']}: {e.get('summary', '(no summary)')}")
            manifest_section = "\n".join(parts)

    full_system = system_prompt
    if manifest_section:
        full_system += "\n" + manifest_section

    messages = [{"role": "system", "content": full_system}]

    # Ambient messages from raw.jsonl
    messages.extend(_read_jsonl_messages(session_dir / "raw.jsonl"))

    # Expanded effort raw logs (concluded but temporarily loaded)
    for effort_id in sorted(expanded):
        effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"
        messages.extend(_read_jsonl_messages(effort_file))

    # All open effort raw logs, with active effort last
    open_efforts = get_all_open_efforts(session_dir)
    active = get_active_effort(session_dir)
    active_id = active["id"] if active else None

    # Non-active open efforts first
    for effort in open_efforts:
        if effort["id"] != active_id:
            effort_file = session_dir / "efforts" / f"{effort['id']}.jsonl"
            messages.extend(_read_jsonl_messages(effort_file))

    # Active effort last
    if active_id:
        effort_file = session_dir / "efforts" / f"{active_id}.jsonl"
        messages.extend(_read_jsonl_messages(effort_file))

    return messages


def _build_tool_banners(tools_fired: list[tuple[str, dict, str]]) -> str:
    """Build programmatic notification banners for tool actions."""
    parts = []
    for tool_name, tool_args, tool_result in tools_fired:
        result = json.loads(tool_result)
        if "error" in result:
            continue  # Don't banner failed tool calls

        if tool_name == "open_effort":
            parts.append(f"--- Started effort: {result['effort_id']} ---")
        elif tool_name == "close_effort":
            summary = result.get("summary", "")
            parts.append(f"--- Concluded effort: {result['effort_id']} ---\nSummary: {summary}")
        elif tool_name == "expand_effort":
            tokens = result.get("tokens_loaded", 0)
            parts.append(f"--- Expanded effort: {result['effort_id']} ({tokens} tokens loaded) ---")
        elif tool_name == "collapse_effort":
            parts.append(f"--- Collapsed effort: {result['effort_id']} (back to summary) ---")
        elif tool_name == "switch_effort":
            parts.append(f"--- Switched to effort: {result['effort_id']} ---")

    return "\n".join(parts)


def process_turn(session_dir: Path, user_message: str, model: str = DEFAULT_MODEL) -> str:
    """Process a single conversation turn.

    Returns the assistant's final response text.
    """
    # 1. Increment turn counter
    current_turn = increment_turn(session_dir)

    # 2. Build working context
    messages = _build_messages(session_dir)

    # 3. Snapshot effort state before the turn
    active_before = get_active_effort(session_dir)

    # 4. Add user message
    messages.append({"role": "user", "content": user_message})

    # 5. Tool-calling loop
    assistant_content = ""
    tools_fired = []  # Track (tool_name, tool_args, tool_result) for banners
    for _ in range(MAX_TOOL_ROUNDS):
        response_msg = chat_with_tools(messages, TOOL_DEFINITIONS, model)

        if not response_msg.tool_calls:
            # No tool calls — we have the final response
            assistant_content = response_msg.content or ""
            break

        # Process tool calls
        messages.append(response_msg)
        for tool_call in response_msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}

            tool_result = execute_tool(session_dir, tool_name, tool_args, model)
            tools_fired.append((tool_name, tool_args, tool_result))

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })
    else:
        # Max rounds exhausted — use whatever content we have
        assistant_content = response_msg.content or ""

    # 6. Build programmatic banners for tool actions
    banners = _build_tool_banners(tools_fired)

    # 7. Compose final response: banners + LLM response
    if banners and assistant_content:
        final_response = banners + "\n\n" + assistant_content
    elif banners:
        final_response = banners
    else:
        final_response = assistant_content

    # 8. Log messages to appropriate file (active effort or ambient)
    active_after = get_active_effort(session_dir)

    if active_before:
        _log_message(session_dir, active_before["id"], "user", user_message)
        _log_message(session_dir, active_before["id"], "assistant", final_response)
    elif active_after and not active_before:
        _log_message(session_dir, active_after["id"], "user", user_message)
        _log_message(session_dir, active_after["id"], "assistant", final_response)
    else:
        _log_message(session_dir, None, "user", user_message)
        _log_message(session_dir, None, "assistant", final_response)

    # 9. Check decay for all expanded efforts
    decayed_ids = check_decay(session_dir, current_turn, user_message, final_response)

    # 10. Append decay banners to response if any
    if decayed_ids:
        decay_banners = "\n".join(
            f"--- Auto-collapsed effort: {eid} (inactive for {DECAY_THRESHOLD} turns) ---"
            for eid in decayed_ids
        )
        final_response = final_response + "\n\n" + decay_banners

    return final_response
