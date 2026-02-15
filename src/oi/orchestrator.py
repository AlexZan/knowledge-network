"""Orchestrator: handles each conversation turn with tool-calling flow.

Flow per turn:
1. Build working context (system prompt + ambient + manifest summaries + open effort raw)
2. Add user message
3. Send to LLM with tool definitions
4. If tool call: execute tool, send result back, get next response (loop)
5. Log messages to appropriate log (effort or ambient)
6. Return assistant response
"""

import json
import yaml
from pathlib import Path
from datetime import datetime

from .llm import load_prompt, chat_with_tools, DEFAULT_MODEL
from .tools import TOOL_DEFINITIONS, execute_tool, get_open_effort


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


def _build_messages(session_dir: Path) -> list[dict]:
    """Build the LLM message list from working context.

    Working Context = system_prompt + ambient + manifest_summaries + open_effort_raw
    """
    # System prompt
    system_prompt = load_prompt("system")

    # Read manifest for concluded effort summaries
    manifest_section = ""
    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        concluded = [e for e in manifest.get("efforts", []) if e.get("status") == "concluded"]
        if concluded:
            parts = ["\nConcluded efforts (summaries only):"]
            for e in concluded:
                parts.append(f"- {e['id']}: {e.get('summary', '(no summary)')}")
            manifest_section = "\n".join(parts)

    full_system = system_prompt
    if manifest_section:
        full_system += "\n" + manifest_section

    messages = [{"role": "system", "content": full_system}]

    # Ambient messages from raw.jsonl
    raw_path = session_dir / "raw.jsonl"
    if raw_path.exists():
        raw_text = raw_path.read_text(encoding="utf-8").strip()
        if raw_text:
            for line in raw_text.split("\n"):
                if line.strip():
                    entry = json.loads(line)
                    messages.append({"role": entry["role"], "content": entry["content"]})

    # Open effort raw log
    open_effort = get_open_effort(session_dir)
    if open_effort:
        effort_file = session_dir / "efforts" / f"{open_effort['id']}.jsonl"
        if effort_file.exists():
            effort_text = effort_file.read_text(encoding="utf-8").strip()
            if effort_text:
                for line in effort_text.split("\n"):
                    if line.strip():
                        entry = json.loads(line)
                        messages.append({"role": entry["role"], "content": entry["content"]})

    return messages


def process_turn(session_dir: Path, user_message: str, model: str = DEFAULT_MODEL) -> str:
    """Process a single conversation turn.

    Returns the assistant's final response text.
    """
    # 1. Build working context
    messages = _build_messages(session_dir)

    # 2. Snapshot effort state before the turn
    open_before = get_open_effort(session_dir)

    # 3. Add user message
    messages.append({"role": "user", "content": user_message})

    # 4. Tool-calling loop
    assistant_content = ""
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

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })
    else:
        # Max rounds exhausted — use whatever content we have
        assistant_content = response_msg.content or ""

    # 5. Log messages to appropriate file
    open_after = get_open_effort(session_dir)

    if open_before:
        # Effort was already open — both messages go to effort log
        _log_message(session_dir, open_before["id"], "user", user_message)
        _log_message(session_dir, open_before["id"], "assistant", assistant_content)
    elif open_after and not open_before:
        # Effort was just opened this turn — both messages go to new effort
        _log_message(session_dir, open_after["id"], "user", user_message)
        _log_message(session_dir, open_after["id"], "assistant", assistant_content)
    else:
        # No effort involved — ambient
        _log_message(session_dir, None, "user", user_message)
        _log_message(session_dir, None, "assistant", assistant_content)

    return assistant_content
