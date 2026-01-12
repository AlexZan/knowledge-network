You are analyzing a conversation exchange to determine if it should be captured as a knowledge artifact.

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
