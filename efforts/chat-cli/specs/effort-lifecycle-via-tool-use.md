# Tech Spec: Effort Lifecycle via LLM Tool Use

## Applies To
Stories: 2, 3, 4, 5, 8

## Mechanism

Effort lifecycle events (open, conclude, route) are managed through LLM tool use, not string parsing or regex detection.

The orchestrator passes tool definitions to `litellm.completion()`:

- `open_effort(name: str)` — LLM calls this when the user wants to start a focused effort
- `conclude_effort(effort_id: str, summary: str)` — LLM calls this when the user indicates the effort is done

The LLM decides when to call these tools based on conversational context. The orchestrator inspects `response.choices[0].message.tool_calls` and dispatches accordingly. The assistant's text response is separate from the tool call — the LLM can say "Sure, opening an effort for that" while simultaneously calling `open_effort("auth-bug")`.

Message routing (effort vs ambient) also uses the LLM's judgment: if an effort is open, the system prompt tells the LLM about it, and the LLM either continues the effort conversation or responds as ambient. The orchestrator routes based on whether the response includes effort-related tool calls, not based on keyword matching in the user's message.

## What This Replaces

The current implementation uses:
- `assistant_response.startswith("Opening effort: ")` — string prefix parsing
- `assistant_response.startswith("Concluding effort: ")` — string prefix parsing
- Hardcoded `["quick question", "weather", "unrelated"]` — keyword matching for interruption detection

None of these work in production because the LLM doesn't know about these conventions.

## Test Implications

- Mock `litellm.completion()` to return response objects with `tool_calls`, not plain string content
- Use `unittest.mock.MagicMock` to construct response objects matching litellm's return structure: `response.choices[0].message.tool_calls[0].function.name` and `.arguments`
- Assert that the orchestrator processes tool calls and invokes the correct storage functions
- Do NOT mock `chat()` to return `"Opening effort: ..."` strings — that mechanism does not exist
- Interruption detection is implicit: LLM sees open effort in system prompt, decides whether to engage with it or respond as ambient. Tests should verify routing by checking which log file gets written to, not by asserting on keyword detection
- The `detection.py` module's regex patterns are NOT used for effort lifecycle — the LLM handles detection via tools
