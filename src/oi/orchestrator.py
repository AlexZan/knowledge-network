"""Orchestrator: handles each conversation turn with tool-calling flow.

Flow per turn:
1. Build working context (system prompt + ambient + effort summaries + expanded raw + open effort raw)
2. Add user message
3. Send to LLM with tool definitions
4. If tool call: execute tool, send result back, get next response (loop)
5. Log messages to appropriate log (active effort or ambient)
6. Return assistant response
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Callable

from .llm import chat_with_tools, DEFAULT_MODEL
from .prompts import load_prompt
from .state import (
    _load_expanded, _load_knowledge, _load_expanded_knowledge,
    _load_expanded_state, _load_efforts, increment_turn,
)
from .confidence import compute_confidence, confidence_annotation
from .tools import (
    TOOL_DEFINITIONS, execute_tool,
    get_active_effort, get_all_open_efforts,
)
from .decay import (
    check_decay, check_knowledge_decay, DECAY_THRESHOLD,
    update_summary_references, get_evicted_summary_ids,
    update_knowledge_references, get_evicted_knowledge_ids, AMBIENT_WINDOW,
)
from .session_log import log_event, extract_node_context


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


def _read_jsonl_messages(filepath: Path, max_messages: int | None = None) -> list[dict]:
    """Read a JSONL file and return list of {role, content} message dicts.

    Skips malformed lines rather than crashing the whole session.
    If max_messages is set, returns only the last N messages.
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
    if max_messages and len(messages) > max_messages:
        messages = messages[-max_messages:]
    return messages




def _build_messages(session_dir: Path, current_turn: int | None = None) -> list[dict]:
    """Build the LLM message list from working context.

    Working Context = system_prompt + ambient (windowed) + effort_summaries (non-expanded, non-evicted)
                    + expanded_effort_raw + all_open_effort_raw (active last)

    If current_turn is provided, summary eviction is applied.
    """
    # System prompt
    system_prompt = load_prompt("system")

    # Read efforts from unified knowledge store
    effort_section = ""
    memory_section = ""
    efforts = _load_efforts(session_dir)
    expanded = _load_expanded(session_dir)

    concluded = [e for e in efforts if e.get("status") == "concluded"]

    if concluded:
        # Filter out expanded and evicted summaries
        evicted = get_evicted_summary_ids(session_dir, current_turn) if current_turn is not None else set()
        summary_efforts = [e for e in concluded if e["id"] not in expanded and e["id"] not in evicted]

        if summary_efforts:
            parts = ["\nConcluded efforts (summaries only):"]
            for e in summary_efforts:
                parts.append(f"- {e['id']}: {e.get('summary', '(no summary)')}")
            effort_section = "\n".join(parts)

        # Add memory section if there are any concluded efforts (evicted or not)
        memory_section = (
            "\n\n## Memory\n"
            "Concluded effort summaries shown above are only the recently-referenced ones.\n"
            "Older summaries are still stored — use search_efforts(query) to find past efforts\n"
            "not shown in working memory. You can then expand_effort(id) for full details."
        )

    # Knowledge graph nodes with confidence annotations (filtered by eviction)
    # Only show non-effort active nodes in the knowledge section
    knowledge_section = ""
    knowledge = _load_knowledge(session_dir)
    active_nodes = [n for n in knowledge.get("nodes", []) if n.get("status") == "active" and n.get("type") != "effort"]
    evicted_knowledge = get_evicted_knowledge_ids(session_dir, current_turn) if current_turn is not None else set()
    visible_nodes = [n for n in active_nodes if n["id"] not in evicted_knowledge]
    evicted_count = len(active_nodes) - len(visible_nodes)
    if visible_nodes:
        kg_parts = ["\nKnowledge graph:"]
        for n in visible_nodes:
            conf = compute_confidence(n["id"], knowledge)
            annotation = confidence_annotation(conf)
            prefix = f"[{n['type']}]"
            if n.get("type") == "principle" and n.get("instance_count"):
                prefix = f"[principle, {n['instance_count']} instances]"
            if annotation:
                kg_parts.append(f"- {prefix} {n['summary']} {annotation}")
            else:
                kg_parts.append(f"- {prefix} {n['summary']}")
        if evicted_count > 0:
            kg_parts.append(f"({evicted_count} older knowledge node(s) not shown — use query_knowledge to find them)")
        knowledge_section = "\n".join(kg_parts)
    elif evicted_count > 0:
        knowledge_section = f"\nKnowledge graph:\n({evicted_count} older knowledge node(s) not shown — use query_knowledge to find them)"

    full_system = system_prompt
    if effort_section:
        full_system += "\n" + effort_section
    if knowledge_section:
        full_system += "\n" + knowledge_section
    if memory_section:
        full_system += memory_section

    messages = [{"role": "system", "content": full_system}]

    # Ambient messages from raw.jsonl (windowed to last AMBIENT_WINDOW exchanges)
    messages.extend(_read_jsonl_messages(session_dir / "raw.jsonl", max_messages=AMBIENT_WINDOW * 2))

    # Expanded effort raw logs (concluded but temporarily loaded)
    for effort_id in sorted(expanded):
        effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"
        messages.extend(_read_jsonl_messages(effort_file))

    # Expanded knowledge fragments (session-sourced nodes with context loaded)
    expanded_knowledge = _load_expanded_knowledge(session_dir)
    if expanded_knowledge:
        knowledge = _load_knowledge(session_dir)
        expanded_state = _load_expanded_state(session_dir)
        for node_id in sorted(expanded_knowledge):
            # Find node to get session_id
            node = None
            for n in knowledge.get("nodes", []):
                if n["id"] == node_id:
                    node = n
                    break
            if not node:
                continue
            session_id = node.get("created_in_session")
            if not session_id:
                continue
            fragment = extract_node_context(session_dir, session_id, node_id)
            if fragment:
                # Inject as system message banner + conversation fragment
                messages.append({
                    "role": "system",
                    "content": f"--- Expanded knowledge: {node_id} ({node.get('summary', '')}) ---",
                })
                messages.extend(fragment)

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
            knowledge = result.get("knowledge_extracted", [])
            banner_lines = [
                f"--- Concluded effort: {result['effort_id']} ---",
                f"Summary: {summary}",
            ]
            if knowledge:
                banner_lines.append("")
                banner_lines.append("Knowledge nodes extracted:")
                for node in knowledge:
                    banner_lines.append(f"  [{node['node_type']}] {node['summary']}")
            patterns = result.get("patterns_detected", [])
            if patterns:
                banner_lines.append("")
                for p in patterns:
                    if p["action"] == "created":
                        banner_lines.append(f"  Pattern detected ({p['instance_count']} instances): {p['summary']}")
                    elif p["action"] == "updated":
                        banner_lines.append(f"  Pattern reinforced ({p['instance_count']} instances): {p['summary']}")
            parts.append("\n".join(banner_lines))
        elif tool_name == "expand_effort":
            tokens = result.get("tokens_loaded", 0)
            parts.append(f"--- Expanded effort: {result['effort_id']} ({tokens} tokens loaded) ---")
        elif tool_name == "collapse_effort":
            parts.append(f"--- Collapsed effort: {result['effort_id']} (back to summary) ---")
        elif tool_name == "switch_effort":
            parts.append(f"--- Switched to effort: {result['effort_id']} ---")
        elif tool_name == "reopen_effort":
            parts.append(f"--- Reopened effort: {result['effort_id']} ---")
        elif tool_name == "read_file":
            path = result.get("path", "")
            size = result.get("size", 0)
            truncated = " (truncated)" if result.get("truncated") else ""
            parts.append(f"--- Read file: {path} ({size} chars{truncated}) ---")
        elif tool_name == "run_command":
            exit_code = result.get("exit_code", "?")
            parts.append(f"--- Command exited: {exit_code} ---")
        elif tool_name == "write_file":
            path = result.get("path", "")
            size = result.get("size", 0)
            parts.append(f"--- Wrote file: {path} ({size} chars) ---")
        elif tool_name == "append_file":
            path = result.get("path", "")
            size = result.get("size", 0)
            parts.append(f"--- Appended to file: {path} ({size} chars total) ---")
        elif tool_name == "add_knowledge":
            node_id = result.get("node_id", "")
            node_type = result.get("node_type", "")
            summary = result.get("summary", "")
            conf = result.get("confidence", {})
            conf_level = conf.get("level", "low")
            banner_lines = [f"--- Knowledge added: [{node_type}] {summary} (confidence: {conf_level}) ---"]
            for edge in result.get("edges_created", []):
                if edge["edge_type"] == "contradicts":
                    banner_lines.append(f"  !! Contradicts: {edge['target_id']}")
                else:
                    banner_lines.append(f"  Supports: {edge['target_id']}")
            parts.append("\n".join(banner_lines))
        elif tool_name == "expand_knowledge":
            node_id = result.get("node_id", "")
            if result.get("via_effort"):
                tokens = result.get("tokens_loaded", 0)
                parts.append(f"--- Expanded knowledge: {node_id} via effort '{result['via_effort']}' ({tokens} tokens loaded) ---")
            else:
                msgs = result.get("messages_loaded", 0)
                parts.append(f"--- Expanded knowledge: {node_id} ({msgs} messages loaded from session) ---")
        elif tool_name == "collapse_knowledge":
            node_id = result.get("node_id", "")
            parts.append(f"--- Collapsed knowledge: {node_id} ---")

    return "\n".join(parts)


def process_turn(session_dir: Path, user_message: str, model: str = DEFAULT_MODEL, confirmation_callback: Callable[[str], bool] | None = None, session_id: str = None) -> str:
    """Process a single conversation turn.

    Returns the assistant's final response text.
    """
    # 1. Increment turn counter
    current_turn = increment_turn(session_dir)

    # 2. Build working context
    messages = _build_messages(session_dir, current_turn=current_turn)

    # 3. Snapshot effort state before the turn
    active_before = get_active_effort(session_dir)

    # 4. Add user message
    messages.append({"role": "user", "content": user_message})

    # Log user message to session
    if session_id:
        log_event(session_dir, session_id, "user-message", {"content": user_message})

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

            tool_result = execute_tool(session_dir, tool_name, tool_args, model, confirmation_callback=confirmation_callback, session_id=session_id)
            tools_fired.append((tool_name, tool_args, tool_result))

            # Log tool call to session
            if session_id:
                log_event(session_dir, session_id, "tool-call", {
                    "tool": tool_name,
                    "args": tool_args,
                    "result_summary": tool_result[:200] if len(tool_result) > 200 else tool_result,
                })
                # Log node events from add_knowledge
                if tool_name == "add_knowledge":
                    try:
                        r = json.loads(tool_result)
                        if r.get("status") == "added":
                            log_event(session_dir, session_id, "node-created", {
                                "node_id": r["node_id"],
                                "node_type": r["node_type"],
                            })
                            # Log supersession events
                            for edge in r.get("edges_created", []):
                                if edge.get("edge_type") == "contradicts":
                                    pass  # contradiction noted in edges_created
                        # Check if supersedes was used
                        if tool_args.get("supersedes"):
                            for sid in tool_args["supersedes"]:
                                log_event(session_dir, session_id, "node-superseded", {
                                    "old_node_id": sid,
                                    "new_node_id": r.get("node_id"),
                                })
                    except (json.JSONDecodeError, KeyError):
                        pass

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

    # 8. Log assistant message to session
    if session_id:
        log_event(session_dir, session_id, "assistant-message", {"content": assistant_content})

    # 9. Log messages to appropriate file (active effort or ambient)
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

    # 10. Check decay for all expanded efforts
    decayed_ids = check_decay(session_dir, current_turn, user_message, final_response)

    # 11. Check decay for expanded knowledge nodes
    decayed_knowledge_ids = check_knowledge_decay(session_dir, current_turn, user_message, final_response)

    # 12. Update summary reference tracking for eviction
    update_summary_references(session_dir, current_turn, user_message, final_response)

    # 13. Update knowledge reference tracking for eviction
    update_knowledge_references(session_dir, current_turn, user_message, final_response)

    # 14. Append decay banners to response if any
    decay_parts = []
    for eid in decayed_ids:
        decay_parts.append(f"--- Auto-collapsed effort: {eid} (inactive for {DECAY_THRESHOLD} turns) ---")
    for nid in decayed_knowledge_ids:
        decay_parts.append(f"--- Auto-collapsed knowledge: {nid} (inactive for {DECAY_THRESHOLD} turns) ---")
    if decay_parts:
        final_response = final_response + "\n\n" + "\n".join(decay_parts)

    return final_response
