"""Tool definitions and handlers for effort management.

Three LLM-callable tools:
- open_effort(name): Start tracking focused work
- close_effort(): Conclude current effort with summary
- effort_status(): Get status of all efforts
"""

import json
import yaml
from pathlib import Path
from datetime import datetime


# Tool definitions in OpenAI function calling format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_effort",
            "description": (
                "Start tracking focused work on a topic. Creates an effort log "
                "and manifest entry. Fails if an effort is already open."
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
                "Permanently conclude the current open effort. This is irreversible. "
                "Only call when the user explicitly says the work is DONE or COMPLETE. "
                "Never call for 'pause', 'hold', or 'switch' — those mean keep it open. "
                "Summarizes the conversation and removes raw log from working context."
            ),
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
            "name": "effort_status",
            "description": "Get the status of all efforts (open and concluded) with summaries and token counts.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def _load_manifest(session_dir: Path) -> dict:
    """Load manifest.yaml, returning empty structure if missing."""
    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {"efforts": []}
    return {"efforts": []}


def _save_manifest(session_dir: Path, manifest: dict):
    """Write manifest.yaml."""
    manifest_path = session_dir / "manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False)


def get_open_effort(session_dir: Path) -> dict | None:
    """Get the currently open effort from manifest, or None."""
    manifest = _load_manifest(session_dir)
    for effort in manifest.get("efforts", []):
        if effort.get("status") == "open":
            return effort
    return None


def open_effort(session_dir: Path, name: str) -> str:
    """Open a new effort. Returns JSON result for tool response."""
    existing = get_open_effort(session_dir)
    if existing:
        return json.dumps({
            "error": f"Cannot open '{name}': effort '{existing['id']}' is already open. Close it first."
        })

    manifest = _load_manifest(session_dir)
    now = datetime.now().isoformat()

    manifest["efforts"].append({
        "id": name,
        "status": "open",
        "summary": None,
        "raw_file": f"efforts/{name}.jsonl",
        "created": now,
        "updated": now
    })

    _save_manifest(session_dir, manifest)
    return json.dumps({"status": "opened", "effort_id": name})


def close_effort(session_dir: Path, model: str = None) -> str:
    """Close the current open effort. Returns JSON result."""
    from .llm import summarize_effort as llm_summarize, DEFAULT_MODEL

    effort = get_open_effort(session_dir)
    if not effort:
        return json.dumps({"error": "No effort is currently open."})

    effort_id = effort["id"]
    effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"

    # Read the effort's raw log for summarization
    effort_content = ""
    if effort_file.exists():
        effort_content = effort_file.read_text(encoding="utf-8")

    # Summarize via LLM — but only if there's enough content
    # With very little content, the summarizer tends to hallucinate
    if len(effort_content.strip()) < 50:
        summary = f"Brief effort: {effort_id} (too short to summarize)"
    else:
        summary = llm_summarize(effort_content, model or DEFAULT_MODEL)

    # Update manifest
    manifest = _load_manifest(session_dir)
    now = datetime.now().isoformat()
    for e in manifest["efforts"]:
        if e["id"] == effort_id:
            e["status"] = "concluded"
            e["summary"] = summary
            e["updated"] = now
            break

    _save_manifest(session_dir, manifest)

    return json.dumps({
        "status": "concluded",
        "effort_id": effort_id,
        "summary": summary
    })


def effort_status(session_dir: Path) -> str:
    """Get status of all efforts. Returns JSON result."""
    from .tokens import count_tokens

    manifest = _load_manifest(session_dir)
    efforts = manifest.get("efforts", [])

    if not efforts:
        return json.dumps({"efforts": [], "message": "No efforts yet."})

    result = []
    for effort in efforts:
        entry = {
            "id": effort["id"],
            "status": effort["status"],
            "summary": effort.get("summary"),
        }

        effort_file = session_dir / "efforts" / f"{effort['id']}.jsonl"
        if effort_file.exists():
            raw_content = effort_file.read_text(encoding="utf-8")
            entry["raw_tokens"] = count_tokens(raw_content)

        if effort.get("summary"):
            entry["summary_tokens"] = count_tokens(effort["summary"])

        result.append(entry)

    return json.dumps({"efforts": result})


def execute_tool(session_dir: Path, tool_name: str, tool_args: dict, model: str = None) -> str:
    """Execute a tool by name. Returns the tool result as a JSON string."""
    if tool_name == "open_effort":
        return open_effort(session_dir, tool_args["name"])
    elif tool_name == "close_effort":
        return close_effort(session_dir, model)
    elif tool_name == "effort_status":
        return effort_status(session_dir)
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
