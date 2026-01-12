"""Agentic interpretation - LLM decides what artifacts to create."""

import json
from typing import Literal

from pydantic import BaseModel, Field

from .llm import chat


class ArtifactInterpretation(BaseModel):
    """LLM's interpretation of what artifact to create from an exchange."""

    should_capture: bool = Field(
        description="Whether this exchange warrants creating an artifact"
    )
    artifact_type: Literal["effort", "fact", "event"] | None = Field(
        default=None,
        description="Type of artifact to create"
    )
    summary: str | None = Field(
        default=None,
        description="What the user is trying to do (for efforts) or the fact/event"
    )
    status: Literal["open", "resolved"] | None = Field(
        default=None,
        description="For efforts: open if ongoing, resolved if concluded"
    )
    resolution: str | None = Field(
        default=None,
        description="For resolved efforts: what was decided/concluded"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for searchability"
    )
    reasoning: str = Field(
        description="Why the LLM made this decision"
    )


INTERPRETATION_PROMPT = """You are analyzing a conversation exchange to determine if it should be captured as a knowledge artifact.

## Artifact Types

| Type | When to Use | Expires? |
|------|-------------|----------|
| effort | Goal-oriented work - user trying to accomplish something | No |
| fact | Simple Q&A, specific knowledge | Yes (if unreferenced) |
| event | Casual exchange, context that might matter later | Yes (fast) |

## Effort Status

- **open**: User is still working on this, no decision yet
- **resolved**: User made a decision or completed the goal - MUST include resolution

## Guidelines

**Create an effort when:**
- User is trying to accomplish something (find information, make a decision, solve a problem)
- Mark as "resolved" with a resolution when the user indicates a decision ("I'll do that", "that sounds good", "I'll buy that one")

**Create a fact when:**
- Simple Q&A that establishes specific knowledge
- Something the user might reference later

**Don't create an artifact when:**
- Simple greeting or acknowledgment
- No lasting value

## IMPORTANT for resolved efforts

When a user says things like "I'll buy that one", "okay I'll do that", "sounds good":
- This is a RESOLVED effort
- The resolution must capture WHAT they decided, not just that they decided
- If they said "that one", infer from context (usually the first/recommended option)

## Your Task

Analyze this exchange and respond ONLY with a JSON object (no markdown):

{{
  "should_capture": true or false,
  "artifact_type": "effort" or "fact" or "event" or null,
  "summary": "What the user is trying to do",
  "status": "open" or "resolved" (for efforts only),
  "resolution": "What was decided (for resolved efforts only)",
  "tags": ["tag1", "tag2"],
  "reasoning": "Why you made this decision"
}}

## Exchange to Analyze

{context}User: {user_message}
Assistant: {assistant_message}
"""


def interpret_exchange(
    user_message: str,
    assistant_message: str,
    model: str,
    recent_context: list[dict] | None = None
) -> ArtifactInterpretation:
    """Have the LLM interpret what artifact (if any) to create from an exchange.

    Args:
        user_message: The user's message
        assistant_message: The assistant's response
        model: LLM model to use for interpretation
        recent_context: Recent exchanges for context (to resolve "that one", etc.)

    Returns:
        ArtifactInterpretation with the LLM's decision
    """
    # Build context string from recent exchanges
    context_str = ""
    if recent_context:
        context_str = "Recent conversation context:\n"
        for exchange in recent_context[-3:]:  # Last 3 exchanges
            context_str += f"User: {exchange['user']}\n"
            context_str += f"Assistant: {exchange['assistant']}\n\n"
        context_str += "Current exchange:\n"

    prompt = INTERPRETATION_PROMPT.format(
        user_message=user_message,
        assistant_message=assistant_message,
        context=context_str
    )

    messages = [{"role": "user", "content": prompt}]
    response = chat(messages, model)

    # Parse the JSON response
    try:
        # Strip any markdown code blocks if present
        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.split("\n")
            clean_response = "\n".join(lines[1:-1])

        data = json.loads(clean_response)
        return ArtifactInterpretation(**data)
    except (json.JSONDecodeError, Exception) as e:
        # Fallback: don't capture if we can't parse
        return ArtifactInterpretation(
            should_capture=False,
            reasoning=f"Failed to parse LLM response: {e}"
        )
