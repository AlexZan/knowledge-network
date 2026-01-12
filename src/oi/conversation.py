"""Main conversation loop."""

import uuid
from datetime import datetime

from .models import ConversationState, Artifact
from .storage import load_state, save_state
from .chatlog import append_exchange, read_recent
from .interpret import interpret_exchange, ArtifactInterpretation
from .llm import chat


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())[:8]


def create_artifact_from_interpretation(
    state: ConversationState,
    interpretation: ArtifactInterpretation
) -> Artifact | None:
    """Create an artifact from an LLM interpretation.

    Args:
        state: Current conversation state
        interpretation: The LLM's interpretation of what to capture

    Returns:
        Created artifact, or None if nothing should be captured
    """
    if not interpretation.should_capture or not interpretation.artifact_type:
        return None

    artifact = Artifact(
        id=generate_id(),
        artifact_type=interpretation.artifact_type,
        summary=interpretation.summary or "",
        status=interpretation.status,
        resolution=interpretation.resolution,
        tags=interpretation.tags,
        expires=interpretation.artifact_type in ("fact", "event"),
    )

    state.artifacts.append(artifact)
    return artifact


def build_context(state: ConversationState) -> list[dict]:
    """Build context for LLM from artifacts and recent chat history.

    Includes:
    - System prompt with artifacts summary
    - Recent chat history (for conversation continuity)
    """
    system_parts = [
        "You are a helpful AI assistant. Be concise and direct.",
        ""
    ]

    # Add open efforts
    open_efforts = state.get_open_efforts()
    if open_efforts:
        system_parts.append("Current open efforts (work in progress):")
        for e in open_efforts:
            system_parts.append(f"- {e.summary}")
        system_parts.append("")

    # Add recent resolved efforts
    resolved = state.get_resolved_efforts()[-5:]  # Last 5
    if resolved:
        system_parts.append("Recent decisions/conclusions:")
        for e in resolved:
            system_parts.append(f"- {e.summary}: {e.resolution}")
        system_parts.append("")

    # Add facts
    facts = state.get_facts()[-10:]  # Last 10
    if facts:
        system_parts.append("Known facts:")
        for f in facts:
            system_parts.append(f"- {f.summary}")
        system_parts.append("")

    messages = [{"role": "system", "content": "\n".join(system_parts)}]

    # Add recent chat history for continuity
    recent = read_recent(limit=5)
    for exchange in recent:
        messages.append({"role": "user", "content": exchange["user"]})
        messages.append({"role": "assistant", "content": exchange["assistant"]})

    return messages


def process_turn(
    state: ConversationState,
    user_input: str,
    model: str
) -> tuple[str, Artifact | None]:
    """Process a single conversation turn.

    Args:
        state: Current conversation state
        user_input: User's message
        model: LLM model to use

    Returns:
        Tuple of (ai_response, artifact_if_created)
    """
    # Build context from artifacts
    context = build_context(state)
    context.append({"role": "user", "content": user_input})

    # Get AI response
    ai_response = chat(context, model)

    # Always append to raw chat log (permanent record)
    append_exchange(user_input, ai_response)

    # Agentic interpretation: LLM decides what artifact to create
    # Pass recent context so interpreter can resolve references like "that one"
    recent = read_recent(limit=5)
    interpretation = interpret_exchange(user_input, ai_response, model, recent_context=recent)
    artifact = create_artifact_from_interpretation(state, interpretation)

    # Save state
    save_state(state)

    return ai_response, artifact
