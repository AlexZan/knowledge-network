# OI Session — WebSocket Contract

> Interface for a running OI CLI session.
> Concerns: efforts, turns, context window, decay, tool usage.
> Ephemeral — connection exists only while a CLI session is active.

## Connection

- Default port: `localhost:9601`
- One session = one WS server (if you run two CLI sessions, they're on different ports)
- When CLI exits, connection closes — UI shows "session disconnected"

## Message Envelope

```json
{
  "type": "event_name",
  "ts": "2025-02-25T10:30:00.000Z",
  "data": { ... }
}
```

## Server → Client Events

### `session_started` — Sent on connect

```json
{
  "type": "session_started",
  "ts": "...",
  "data": {
    "session_id": "ses-20250225-103000",
    "session_count": 42,
    "turn_count": 0,
    "efforts": [
      {
        "id": "auth-bug",
        "status": "open",
        "active": true,
        "summary": null,
        "created": "2025-02-25T09:00:00Z",
        "updated": "2025-02-25T10:30:00Z"
      },
      {
        "id": "previous-work",
        "status": "concluded",
        "active": false,
        "summary": "Investigated caching strategies...",
        "created": "2025-02-20T...",
        "updated": "2025-02-24T..."
      }
    ],
    "context": {
      "expanded_efforts": ["auth-bug"],
      "expanded_knowledge": ["fact-001", "fact-002"],
      "context_usage_pct": 12.5
    }
  }
}
```

### `turn_started`

User sent a message, CLI is processing.

```json
{
  "type": "turn_started",
  "ts": "...",
  "data": {
    "turn_number": 16,
    "effort_id": "auth-bug"
  }
}
```

### `turn_completed`

```json
{
  "type": "turn_completed",
  "ts": "...",
  "data": {
    "turn_number": 16,
    "effort_id": "auth-bug",
    "tools_called": ["search_knowledge", "add_knowledge"],
    "context_usage_pct": 45.2
  }
}
```

### `effort_opened`

```json
{
  "type": "effort_opened",
  "ts": "...",
  "data": {
    "effort": {
      "id": "caching-research",
      "status": "open",
      "active": true,
      "summary": null,
      "created": "2025-02-25T10:30:00Z",
      "updated": "2025-02-25T10:30:00Z"
    }
  }
}
```

### `effort_closed`

```json
{
  "type": "effort_closed",
  "ts": "...",
  "data": {
    "effort_id": "caching-research",
    "summary": "Evaluated Redis vs Memcached for session storage.",
    "nodes_created": ["fact-003", "decision-002"],
    "edges_created": [
      { "source": "fact-003", "target": "fact-001", "type": "contradicts" }
    ]
  }
}
```

### `effort_switched`

```json
{
  "type": "effort_switched",
  "ts": "...",
  "data": {
    "active_effort_id": "auth-bug",
    "previous_effort_id": "caching-research"
  }
}
```

### `context_changed`

Something was expanded or collapsed in the working context.

```json
{
  "type": "context_changed",
  "ts": "...",
  "data": {
    "action": "expanded",
    "item_type": "effort",
    "item_id": "auth-bug",
    "context_usage_pct": 48.1,
    "expanded_efforts": ["auth-bug", "caching-research"],
    "expanded_knowledge": ["fact-001", "fact-002", "fact-003"]
  }
}
```

### `decay_collapsed`

Auto-collapse due to salience decay.

```json
{
  "type": "decay_collapsed",
  "ts": "...",
  "data": {
    "item_type": "knowledge",
    "item_id": "fact-001",
    "reason": "not_referenced_for_5_turns",
    "context_usage_pct": 42.0,
    "expanded_knowledge": ["fact-002", "fact-003"]
  }
}
```

### `tool_called`

Real-time tool usage (for a live activity feed).

```json
{
  "type": "tool_called",
  "ts": "...",
  "data": {
    "turn_number": 16,
    "tool_name": "search_knowledge",
    "args_summary": "query='caching strategies'"
  }
}
```

## Client → Server Events (Future)

### `request_effort_log`

Fetch conversation history for an effort.

```json
{
  "type": "request_effort_log",
  "ts": "...",
  "data": {
    "effort_id": "auth-bug",
    "limit": 50,
    "offset": 0
  }
}
```

**Response:**

```json
{
  "type": "effort_log",
  "ts": "...",
  "data": {
    "effort_id": "auth-bug",
    "messages": [
      { "role": "user", "content": "...", "ts": "2025-02-25T09:00:00Z" },
      { "role": "assistant", "content": "...", "ts": "2025-02-25T09:00:01Z" }
    ],
    "total": 120,
    "offset": 0,
    "limit": 50
  }
}
```

### `send_command` (Future)

Send a command from the UI back to the CLI.

```json
{
  "type": "send_command",
  "ts": "...",
  "data": {
    "command": "open_effort",
    "args": { "effort_id": "new-feature" }
  }
}
```
