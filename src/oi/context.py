"""Build context strings for LLM from conversation state and messages."""

import json
from pathlib import Path
from oi.models import ConversationState


def build_context(state: ConversationState, recent_messages: list) -> str:
    """Build context string for LLM from state and recent messages.

    Args:
        state: ConversationState with artifacts
        recent_messages: List of recent message dicts with 'role' and 'content'

    Returns:
        String containing formatted context for LLM
    """
    sections = []

    # Section 1: Open Efforts (current work) - highest priority
    open_efforts = state.get_open_efforts()
    if open_efforts:
        sections.append("# Open Efforts (Current Work)")
        for effort in open_efforts:
            sections.append(f"- {effort.summary}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 2: Resolved Artifacts (past work with conclusions)
    resolved_efforts = state.get_resolved_efforts()
    if resolved_efforts:
        sections.append("# Resolved Efforts (Past Work)")
        for effort in resolved_efforts:
            sections.append(f"- {effort.summary}")
            if effort.resolution:
                sections.append(f"  Resolution: {effort.resolution}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 3: Recent Messages
    if recent_messages:
        sections.append("# Recent Conversation")
        for msg in recent_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            sections.append(f"{role.capitalize()}: {content}")
        sections.append("")

    return "\n".join(sections)


# --- TDD Stubs (auto-generated, implement these) ---

def build_ambient_context(session_dir, user_message):
    raise NotImplementedError('build_ambient_context')


# --- TDD Stubs (auto-generated, implement these) ---

def format_conclusion_confirmation(effort_id, summary):
    raise NotImplementedError('format_conclusion_confirmation')


# --- TDD Stubs (auto-generated, implement these) ---

def build_turn_context(state, session_dir):
    raise NotImplementedError('build_turn_context')


# --- TDD Stubs (auto-generated, implement these) ---

def build_conversation_context(state, raw_log):
    """Build conversation context from state and raw chat log.

    Args:
        state: ConversationState with artifacts
        raw_log: Path to raw.jsonl file with ambient exchanges

    Returns:
        String containing formatted context for LLM
    """
    sections = []

    # Section 1: Open Efforts (current work) - highest priority
    open_efforts = state.get_open_efforts()
    if open_efforts:
        sections.append("# Open Efforts (Current Work)")
        for effort in open_efforts:
            sections.append(f"- {effort.summary}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 2: Resolved Artifacts (past work with conclusions)
    resolved_efforts = state.get_resolved_efforts()
    if resolved_efforts:
        sections.append("# Resolved Efforts (Past Work)")
        for effort in resolved_efforts:
            sections.append(f"- {effort.summary}")
            if effort.resolution:
                sections.append(f"  Resolution: {effort.resolution}")
            if effort.tags:
                sections.append(f"  Tags: {', '.join(effort.tags)}")
        sections.append("")

    # Section 3: Ambient Chat (from raw log)
    if raw_log and isinstance(raw_log, Path) and raw_log.exists():
        sections.append("# Recent Chat")
        try:
            with open(raw_log, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        role = entry.get('role', 'unknown')
                        content = entry.get('content', '')
                        sections.append(f"{role.capitalize()}: {content}")
        except (json.JSONDecodeError, IOError):
            pass
        sections.append("")

    return "\n".join(sections)
