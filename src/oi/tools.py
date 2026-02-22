"""Tool definitions and handlers for effort management and environment interaction.

Ten LLM-callable tools:
- open_effort(name): Start tracking focused work (multiple can be open)
- close_effort(id?): Conclude an effort with summary
- effort_status(): Get status of all efforts
- expand_effort(id): Temporarily load concluded effort's raw log into context
- collapse_effort(id): Remove expanded effort from context
- switch_effort(id): Change which open effort is active
- reopen_effort(id): Reopen a concluded effort to continue working on it
- search_efforts(query): Search past efforts by keyword
- read_file(path): Read a file's contents from the local filesystem
- run_command(command): Execute a shell command (requires user confirmation)
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Callable

from .state import (
    _load_manifest, _save_manifest,
    _load_expanded, _load_expanded_state, _save_expanded,
    _load_session_state, _save_session_state, increment_turn,
)


# Tool definitions in OpenAI function calling format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_effort",
            "description": (
                "Start tracking focused work on a topic. Creates an effort log "
                "and manifest entry. The new effort becomes the active effort."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short kebab-case name for the effort (e.g. 'auth-bug', 'guild-feature')"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_effort",
            "description": (
                "Conclude an effort. Summarizes the conversation and removes raw log from working context. "
                "Concluded efforts can be reopened later with reopen_effort if the user returns to the topic. "
                "Only call when the user explicitly says the work is DONE or COMPLETE. "
                "Never call for 'pause', 'hold', or 'switch' — those mean keep it open. "
                "If id is omitted, closes the active effort."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Effort ID to close. If omitted, closes the active effort."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "effort_status",
            "description": "Get the status of all efforts (open, concluded, expanded) with summaries, token counts, and active indicator.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "expand_effort",
            "description": (
                "Temporarily load a concluded effort's full raw log back into working context. "
                "Use when the user asks about details that the summary alone can't answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The concluded effort ID to expand."
                    }
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "collapse_effort",
            "description": (
                "Remove an expanded effort's raw log from working context, returning to summary only. "
                "Call when the user is done reviewing, or moves to a different topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The expanded effort ID to collapse."
                    }
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "switch_effort",
            "description": (
                "Change which open effort is active (receives new messages). "
                "Call when the user wants to work on a different open effort."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The open effort ID to switch to."
                    }
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reopen_effort",
            "description": (
                "Reopen a concluded effort to continue working on it. "
                "The original conversation history is preserved — new messages append to the existing log. "
                "Use when the user wants to return to a past topic. If the user names a specific effort, "
                "call directly. If ambiguous, use search_efforts first and ask the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The concluded effort ID to reopen."
                    }
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_efforts",
            "description": (
                "Search past efforts by topic. Use when the user asks about something "
                "not shown in the concluded efforts list. Returns matching effort summaries "
                "from the full manifest."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (topic, keywords, effort name)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a file's contents from the local filesystem. "
                "Use when the user asks about a file or you need to examine code/documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read (absolute or relative to CWD)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a shell command. Use when the user asks you to run something, "
                "check status, or perform system operations. The user will be asked to "
                "confirm before execution."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
]


# Tool registry: metadata not sent to LLM (e.g. confirmation requirements)
TOOL_REGISTRY = {
    "read_file": {"requires_confirmation": False},
    "run_command": {"requires_confirmation": True},
}

READ_FILE_MAX_CHARS = 10_000
RUN_COMMAND_TIMEOUT = 30
RUN_COMMAND_MAX_CHARS = 10_000


def get_open_effort(session_dir: Path) -> dict | None:
    """Get the currently open effort from manifest, or None.

    For backwards compatibility, returns the first open effort found.
    Prefer get_active_effort() for multi-effort scenarios.
    """
    manifest = _load_manifest(session_dir)
    for effort in manifest.get("efforts", []):
        if effort.get("status") == "open":
            return effort
    return None


def get_active_effort(session_dir: Path) -> dict | None:
    """Get the active effort (open + active: true), or None."""
    manifest = _load_manifest(session_dir)
    for effort in manifest.get("efforts", []):
        if effort.get("status") == "open" and effort.get("active"):
            return effort
    # Fallback: if exactly one open effort exists without active flag, treat it as active
    open_efforts = [e for e in manifest.get("efforts", []) if e.get("status") == "open"]
    if len(open_efforts) == 1:
        return open_efforts[0]
    return None


def get_all_open_efforts(session_dir: Path) -> list[dict]:
    """Get all open efforts from manifest."""
    manifest = _load_manifest(session_dir)
    return [e for e in manifest.get("efforts", []) if e.get("status") == "open"]


def open_effort(session_dir: Path, name: str) -> str:
    """Open a new effort. Sets it as active, deactivates others. Returns JSON result."""
    manifest = _load_manifest(session_dir)
    now = datetime.now().isoformat()

    # Deactivate all currently open efforts
    for effort in manifest.get("efforts", []):
        if effort.get("status") == "open":
            effort["active"] = False

    manifest["efforts"].append({
        "id": name,
        "status": "open",
        "active": True,
        "summary": None,
        "raw_file": f"efforts/{name}.jsonl",
        "created": now,
        "updated": now
    })

    _save_manifest(session_dir, manifest)
    return json.dumps({"status": "opened", "effort_id": name})


def close_effort(session_dir: Path, model: str = None, effort_id: str = None) -> str:
    """Close an effort. If effort_id is None, close the active effort. Returns JSON result."""
    from .llm import summarize_effort as llm_summarize, DEFAULT_MODEL

    if effort_id:
        # Close specific effort by ID
        manifest = _load_manifest(session_dir)
        target = None
        for e in manifest.get("efforts", []):
            if e["id"] == effort_id and e.get("status") == "open":
                target = e
                break
        if not target:
            return json.dumps({"error": f"No open effort with id '{effort_id}'."})
    else:
        # Close the active effort
        target = get_active_effort(session_dir)
        if not target:
            return json.dumps({"error": "No active effort to close."})
        effort_id = target["id"]

    effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"

    # Read the effort's raw log for summarization
    effort_content = ""
    if effort_file.exists():
        effort_content = effort_file.read_text(encoding="utf-8")

    # Summarize via LLM
    if len(effort_content.strip()) < 50:
        summary = f"Brief effort: {effort_id} (too short to summarize)"
    else:
        summary = llm_summarize(effort_content, model or DEFAULT_MODEL)

    # Update manifest
    manifest = _load_manifest(session_dir)
    now = datetime.now().isoformat()
    was_active = False
    for e in manifest["efforts"]:
        if e["id"] == effort_id:
            was_active = e.get("active", False)
            e["status"] = "concluded"
            e["summary"] = summary
            e["updated"] = now
            e.pop("active", None)
            break

    # If the closed effort was active and other efforts are still open, activate the next one
    if was_active:
        open_efforts = [e for e in manifest["efforts"] if e.get("status") == "open"]
        if open_efforts:
            open_efforts[0]["active"] = True

    _save_manifest(session_dir, manifest)

    return json.dumps({
        "status": "concluded",
        "effort_id": effort_id,
        "summary": summary
    })


def expand_effort(session_dir: Path, effort_id: str) -> str:
    """Expand a concluded effort — load its raw log into working context temporarily."""
    from .tokens import count_tokens

    manifest = _load_manifest(session_dir)
    target = None
    for e in manifest.get("efforts", []):
        if e["id"] == effort_id:
            target = e
            break

    if not target:
        return json.dumps({"error": f"No effort with id '{effort_id}'."})

    if target["status"] != "concluded":
        return json.dumps({"error": f"Cannot expand '{effort_id}': status is '{target['status']}', must be 'concluded'."})

    expanded_state = _load_expanded_state(session_dir)
    expanded = set(expanded_state.get("expanded", []))
    if effort_id in expanded:
        return json.dumps({"error": f"Effort '{effort_id}' is already expanded."})

    # Calculate token cost
    effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"
    tokens_loaded = 0
    if effort_file.exists():
        tokens_loaded = count_tokens(effort_file.read_text(encoding="utf-8"))

    # Record expansion with current turn count
    expanded.add(effort_id)
    current_turn = _load_session_state(session_dir).get("turn_count", 0)
    lrt = expanded_state.get("last_referenced_turn", {})
    lrt[effort_id] = current_turn
    _save_expanded(session_dir, expanded, last_referenced_turn=lrt)

    return json.dumps({
        "status": "expanded",
        "effort_id": effort_id,
        "tokens_loaded": tokens_loaded
    })


def collapse_effort(session_dir: Path, effort_id: str) -> str:
    """Collapse an expanded effort — remove its raw log from working context."""
    expanded = _load_expanded(session_dir)

    if effort_id not in expanded:
        return json.dumps({"error": f"Effort '{effort_id}' is not currently expanded."})

    expanded.discard(effort_id)
    _save_expanded(session_dir, expanded)

    return json.dumps({
        "status": "collapsed",
        "effort_id": effort_id
    })


def switch_effort(session_dir: Path, effort_id: str) -> str:
    """Switch which open effort is active."""
    manifest = _load_manifest(session_dir)
    target = None
    for e in manifest.get("efforts", []):
        if e["id"] == effort_id:
            target = e
            break

    if not target:
        return json.dumps({"error": f"No effort with id '{effort_id}'."})

    if target["status"] != "open":
        return json.dumps({"error": f"Cannot switch to '{effort_id}': status is '{target['status']}', must be 'open'."})

    # Deactivate all, activate target
    for e in manifest["efforts"]:
        if e.get("status") == "open":
            e["active"] = (e["id"] == effort_id)

    _save_manifest(session_dir, manifest)

    return json.dumps({
        "status": "switched",
        "effort_id": effort_id
    })


def effort_status(session_dir: Path) -> str:
    """Get status of all efforts. Returns JSON result."""
    from .tokens import count_tokens

    manifest = _load_manifest(session_dir)
    efforts = manifest.get("efforts", [])
    expanded = _load_expanded(session_dir)

    if not efforts:
        return json.dumps({"efforts": [], "message": "No efforts yet."})

    result = []
    for effort in efforts:
        entry = {
            "id": effort["id"],
            "status": effort["status"],
            "summary": effort.get("summary"),
        }

        if effort.get("status") == "open":
            entry["active"] = effort.get("active", False)

        if effort["id"] in expanded:
            entry["expanded"] = True

        effort_file = session_dir / "efforts" / f"{effort['id']}.jsonl"
        if effort_file.exists():
            raw_content = effort_file.read_text(encoding="utf-8")
            entry["raw_tokens"] = count_tokens(raw_content)

        if effort.get("summary"):
            entry["summary_tokens"] = count_tokens(effort["summary"])

        result.append(entry)

    return json.dumps({"efforts": result})


def reopen_effort(session_dir: Path, effort_id: str) -> str:
    """Reopen a concluded effort to continue working on it.

    Flips status back to open, sets as active, deactivates other open efforts,
    removes from expanded set if present, and appends a separator to the raw log.
    """
    manifest = _load_manifest(session_dir)
    target = None
    for e in manifest.get("efforts", []):
        if e["id"] == effort_id:
            target = e
            break

    if not target:
        return json.dumps({"error": f"No effort with id '{effort_id}'."})

    if target["status"] != "concluded":
        return json.dumps({"error": f"Cannot reopen '{effort_id}': status is '{target['status']}', must be 'concluded'."})

    prior_summary = target.get("summary", "")

    # Deactivate all currently open efforts
    for e in manifest["efforts"]:
        if e.get("status") == "open":
            e["active"] = False

    # Flip to open and active
    now = datetime.now().isoformat()
    target["status"] = "open"
    target["active"] = True
    target["updated"] = now
    # Keep summary around for reference but it's no longer the "current" representation

    _save_manifest(session_dir, manifest)

    # Remove from expanded set if it was expanded
    expanded = _load_expanded(session_dir)
    if effort_id in expanded:
        expanded.discard(effort_id)
        _save_expanded(session_dir, expanded)

    # Append separator line to raw log
    effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"
    effort_file.parent.mkdir(parents=True, exist_ok=True)
    separator = {"role": "system", "content": "--- Effort reopened ---", "ts": now}
    with open(effort_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(separator) + "\n")

    return json.dumps({
        "status": "reopened",
        "effort_id": effort_id,
        "prior_summary": prior_summary
    })


def search_efforts(session_dir: Path, query: str) -> str:
    """Search all concluded efforts by keyword. Returns JSON with matches."""
    from .decay import extract_keywords, is_referenced

    manifest = _load_manifest(session_dir)
    concluded = [e for e in manifest.get("efforts", []) if e.get("status") == "concluded"]

    results = []
    for effort in concluded:
        eid = effort["id"]
        summary = effort.get("summary", "") or ""
        keywords = extract_keywords(summary)

        if is_referenced(query, eid, keywords):
            results.append({"id": eid, "summary": summary, "status": "concluded"})

    return json.dumps({"results": results, "query": query})


def read_file(path: str) -> str:
    """Read a file's contents. Returns JSON with content, path, and size."""
    try:
        filepath = Path(path).resolve()
        if not filepath.is_file():
            return json.dumps({"error": f"File not found: {path}"})

        content = filepath.read_text(encoding="utf-8")
        size = len(content)
        truncated = False

        if size > READ_FILE_MAX_CHARS:
            content = content[:READ_FILE_MAX_CHARS]
            truncated = True

        result = {"content": content, "path": str(filepath), "size": size}
        if truncated:
            result["truncated"] = True
        return json.dumps(result)
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {path}"})
    except UnicodeDecodeError:
        return json.dumps({"error": f"Cannot read binary file: {path}"})
    except Exception as e:
        return json.dumps({"error": f"Error reading file: {e}"})


def run_command(
    command: str,
    confirmation_callback: Callable[[str], bool] | None = None,
    timeout: int = RUN_COMMAND_TIMEOUT,
) -> str:
    """Execute a shell command. Requires user confirmation via callback.

    Returns JSON with stdout, stderr, and exit_code.
    """
    # Check confirmation
    if confirmation_callback is not None:
        if not confirmation_callback(command):
            return json.dumps({"error": "Command execution denied by user."})

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        stdout = result.stdout
        stderr = result.stderr
        stdout_truncated = False
        stderr_truncated = False

        if len(stdout) > RUN_COMMAND_MAX_CHARS:
            stdout = stdout[:RUN_COMMAND_MAX_CHARS]
            stdout_truncated = True
        if len(stderr) > RUN_COMMAND_MAX_CHARS:
            stderr = stderr[:RUN_COMMAND_MAX_CHARS]
            stderr_truncated = True

        response = {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
        }
        if stdout_truncated:
            response["stdout_truncated"] = True
        if stderr_truncated:
            response["stderr_truncated"] = True
        return json.dumps(response)
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Command timed out after {timeout} seconds."})
    except Exception as e:
        return json.dumps({"error": f"Error executing command: {e}"})


def execute_tool(session_dir: Path, tool_name: str, tool_args: dict, model: str = None, confirmation_callback: Callable[[str], bool] | None = None) -> str:
    """Execute a tool by name. Returns the tool result as a JSON string."""
    if tool_name == "open_effort":
        return open_effort(session_dir, tool_args["name"])
    elif tool_name == "close_effort":
        return close_effort(session_dir, model, effort_id=tool_args.get("id"))
    elif tool_name == "effort_status":
        return effort_status(session_dir)
    elif tool_name == "expand_effort":
        return expand_effort(session_dir, tool_args["id"])
    elif tool_name == "collapse_effort":
        return collapse_effort(session_dir, tool_args["id"])
    elif tool_name == "switch_effort":
        return switch_effort(session_dir, tool_args["id"])
    elif tool_name == "reopen_effort":
        return reopen_effort(session_dir, tool_args["id"])
    elif tool_name == "search_efforts":
        return search_efforts(session_dir, tool_args["query"])
    elif tool_name == "read_file":
        return read_file(tool_args["path"])
    elif tool_name == "run_command":
        return run_command(
            tool_args["command"],
            confirmation_callback=confirmation_callback,
            timeout=tool_args.get("timeout", RUN_COMMAND_TIMEOUT),
        )
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
