You are analyzing a conversation exchange to determine if it should be captured as a knowledge artifact.

{artifact_types_section}

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
  "artifact_type": "{valid_types}" or null,
  "summary": "What the user is trying to do",
  "status": "open" or "resolved" (for efforts with has_status only),
  "resolution": "What was decided (for resolved efforts only)",
  "tags": ["tag1", "tag2"],
  "reasoning": "Why you made this decision"
}}

## Exchange to Analyze

{context}User: {user_message}
Assistant: {assistant_message}
