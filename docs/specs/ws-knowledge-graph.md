# Knowledge Graph — WebSocket Contract

> Interface for the knowledge graph data layer.
> Any client (CLI, VS Code extension, web UI, future Rust CLI) can connect.
> Concerns: nodes, edges, confidence, patterns. Nothing session-specific.

## Connection

- Default port: `localhost:9600`
- Configurable via `--kg-port` or config file
- Multiple clients can connect simultaneously
- Each client receives a snapshot on connect, then live events

## Message Envelope

```json
{
  "type": "event_name",
  "ts": "2025-02-25T10:30:00.000Z",
  "data": { ... }
}
```

## Server → Client Events

### `snapshot` — Full Graph (sent on connect)

```json
{
  "type": "snapshot",
  "ts": "...",
  "data": {
    "nodes": [
      {
        "id": "fact-001",
        "type": "fact",
        "summary": "Users prefer dark mode by default",
        "status": "active",
        "source": "auth-bug",
        "created": "2025-02-25T10:00:00Z",
        "updated": "2025-02-25T10:00:00Z",
        "has_contradiction": false,
        "confidence": {
          "level": "medium",
          "inbound_supports": 1,
          "inbound_contradicts": 0,
          "independent_sources": 2
        }
      }
    ],
    "edges": [
      {
        "source": "fact-001",
        "target": "fact-002",
        "type": "supports",
        "created": "2025-02-25T10:01:00Z",
        "reasoning": "Both confirm user preference for dark themes"
      }
    ]
  }
}
```

### `node_created`

```json
{
  "type": "node_created",
  "ts": "...",
  "data": {
    "node": {
      "id": "fact-003",
      "type": "fact",
      "summary": "Redis outperforms Memcached for structured data",
      "status": "active",
      "source": "caching-research",
      "created": "2025-02-25T10:35:00Z",
      "updated": "2025-02-25T10:35:00Z",
      "has_contradiction": false,
      "confidence": { "level": "low", "inbound_supports": 0, "inbound_contradicts": 0, "independent_sources": 1 }
    }
  }
}
```

### `node_updated`

Partial update — only changed fields.

```json
{
  "type": "node_updated",
  "ts": "...",
  "data": {
    "node_id": "fact-001",
    "changes": {
      "status": "superseded",
      "superseded_by": "fact-003",
      "has_contradiction": true
    }
  }
}
```

### `edge_created`

```json
{
  "type": "edge_created",
  "ts": "...",
  "data": {
    "edge": {
      "source": "fact-003",
      "target": "fact-001",
      "type": "contradicts",
      "created": "2025-02-25T10:36:00Z",
      "reasoning": "Updated benchmark data supersedes original finding"
    },
    "affected_confidences": [
      { "node_id": "fact-001", "confidence": { "level": "contested", "inbound_supports": 1, "inbound_contradicts": 1, "independent_sources": 2 } },
      { "node_id": "fact-003", "confidence": { "level": "low", "inbound_supports": 0, "inbound_contradicts": 0, "independent_sources": 1 } }
    ]
  }
}
```

### `pattern_detected`

A principle node was created from recurring facts.

```json
{
  "type": "pattern_detected",
  "ts": "...",
  "data": {
    "principle": {
      "id": "principle-001",
      "type": "principle",
      "summary": "Structured caches outperform key-value caches for relational data",
      "status": "active",
      "source": "pattern-detection",
      "abstraction_level": 2,
      "instance_count": 3,
      "confidence": { "level": "high", "inbound_supports": 3, "inbound_contradicts": 0, "independent_sources": 3 }
    },
    "exemplifying_edges": [
      { "source": "fact-003", "target": "principle-001", "type": "exemplifies" },
      { "source": "fact-007", "target": "principle-001", "type": "exemplifies" },
      { "source": "fact-012", "target": "principle-001", "type": "exemplifies" }
    ]
  }
}
```

## Client → Server Events

### `request_snapshot`

```json
{ "type": "request_snapshot", "ts": "..." }
```

### `request_node_detail`

Fetch full node with all connected edges and neighbors.

```json
{
  "type": "request_node_detail",
  "ts": "...",
  "data": { "node_id": "fact-001" }
}
```

**Response:**

```json
{
  "type": "node_detail",
  "ts": "...",
  "data": {
    "node": { "id": "fact-001", "type": "fact", "summary": "...", "..." : "..." },
    "edges": [
      { "source": "fact-001", "target": "fact-002", "type": "supports", "..." : "..." }
    ],
    "neighbors": [
      { "id": "fact-002", "type": "fact", "summary": "...", "..." : "..." }
    ]
  }
}
```

## Data Reference

### Node Types

| Type | Description |
|------|-------------|
| `fact` | Specific knowledge learned |
| `preference` | User preference |
| `decision` | A decision made in context |
| `principle` | Generalization from 3+ facts (via pattern detection) |

### Edge Types

| Type | Meaning | Effect on Target |
|------|---------|-----------------|
| `supports` | Source strengthens target | Increases confidence |
| `contradicts` | Source disagrees with target | Can make "contested" |
| `exemplifies` | Source is instance of target principle | Links fact → principle |
| `supersedes` | Source replaces target | Target becomes "superseded" |

### Confidence (precomputed by server)

| Level | Rule (first match) |
|-------|-------------------|
| `contested` | ≥1 contradicts AND contradicts ≥ supports |
| `high` | ≥3 independent sources AND ≥2 supports |
| `medium` | ≥1 supports OR ≥2 independent sources |
| `low` | Default |
