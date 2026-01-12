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
    artifact_type: Literal["effort", "conclusion", "fact", "event"] | None = Field(
        default=None,
        description="Type of artifact to create"
    )
    summary: str | None = Field(
        default=None,
        description="Summary of the artifact content"
    )
    status: Literal["open", "resolved"] | None = Field(
        default=None,
        description="For efforts: whether it's still open or resolved"
    )
    related_to: str | None = Field(
        default=None,
        description="ID of related artifact (e.g., effort this resolves)"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for searchability (e.g., 'frustrating', 'learning')"
    )
    reasoning: str = Field(
        description="Why the LLM made this decision"
    )


INTERPRETATION_PROMPT = """You are analyzing a conversation exchange to determine if it should be captured as a knowledge artifact.

## Artifact Types

| Type | When to Use | Expires? |
|------|-------------|----------|
| effort | Goal-oriented work (open or resolved) | No |
| conclusion | Resolution/knowledge from an effort | No |
| fact | Simple Q&A, public knowledge | Yes (if unreferenced) |
| event | Casual exchange, context that might matter | Yes (fast) |

## Guidelines

**Create an artifact when:**
- User is working toward a goal (effort)
- Knowledge was gained or a decision was made (conclusion)
- A specific fact was established that might be referenced (fact)
- Context was shared that might be relevant later (event)

**Don't create an artifact when:**
- It's a simple greeting or acknowledgment
- It's a lookup query (user asking about past work)
- The exchange has no lasting value

## Your Task

Analyze this exchange and respond ONLY with a JSON object (no markdown, no explanation):

{{
  "should_capture": true or false,
  "artifact_type": "effort" or "conclusion" or "fact" or "event" or null,
  "summary": "One sentence describing the artifact",
  "status": "open" or "resolved" (for efforts only, null otherwise),
  "related_to": null,
  "tags": ["tag1", "tag2"],
  "reasoning": "Why you made this decision"
}}

## Exchange to Analyze

User: {user_message}
Assistant: {assistant_message}
"""


def interpret_exchange(
    user_message: str,
    assistant_message: str,
    model: str
) -> ArtifactInterpretation:
    """Have the LLM interpret what artifact (if any) to create from an exchange.

    Args:
        user_message: The user's message
        assistant_message: The assistant's response
        model: LLM model to use for interpretation

    Returns:
        ArtifactInterpretation with the LLM's decision
    """
    prompt = INTERPRETATION_PROMPT.format(
        user_message=user_message,
        assistant_message=assistant_message
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
