# WebSocket Event Contracts — Overview

## Dashboard Architecture

The web app is a **panel-based dashboard**. Each panel is an independent UI component with its own WebSocket connection, its own state, and its own concern. Panels can be added incrementally.

```
┌─────────────────────────────────────────────────────────┐
│  Dashboard Shell (layout, panel registry, chrome)        │
│                                                          │
│  ┌─────────────────────────┐  ┌───────────────────────┐  │
│  │  Knowledge Graph Panel   │  │  [Future Panel]       │  │
│  │  ┌───────────────────┐   │  │                       │  │
│  │  │    ○───○           │   │  │  CLI Session          │  │
│  │  │   / \   \          │   │  │  Effort Timeline      │  │
│  │  │  ○   ○───○         │   │  │  ...                  │  │
│  │  │                    │   │  │                       │  │
│  │  └───────────────────┘   │  │                       │  │
│  │  ws :9600                │  │  ws :9601              │  │
│  └─────────────────────────┘  └───────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
         │                              │
  ┌──────┴────────┐              ┌──────┴────────┐
  │  Knowledge     │              │  OI CLI        │
  │  Graph Store   │              │  (session)     │
  └───────────────┘              └───────────────┘
```

### Panel Contract

Each panel is a self-contained Svelte component that:
- Manages its own WebSocket connection
- Handles its own connect/disconnect/reconnect
- Renders independently (one panel failing doesn't break others)
- Receives a layout slot from the dashboard shell

### Slices

| Slice | Panel | Spec | Port |
|-------|-------|------|------|
| 1 | Knowledge Graph | [ws-knowledge-graph.md](ws-knowledge-graph.md) | `localhost:9600` |
| 2+ | OI Session | [ws-oi-session.md](ws-oi-session.md) | `localhost:9601` |

## Interfaces

| Interface | Port | Lifecycle | Concern |
|-----------|------|-----------|---------|
| [Knowledge Graph](ws-knowledge-graph.md) | `localhost:9600` | Always available (runs independently) | Nodes, edges, confidence, patterns |
| [OI Session](ws-oi-session.md) | `localhost:9601` | Exists only during a CLI session | Efforts, turns, context, decay, tools |

## Shared Conventions

- **Message envelope**: `{ "type": "...", "ts": "ISO8601", "data": { ... } }`
- **Transport**: JSON over WebSocket, localhost only
- **Snapshot on connect**: servers send full state on new connection
- **Incremental updates**: events stream as state changes occur
- **No auth**: localhost-only for v1
- **Language-agnostic**: works with Python now, Rust later — same JSON contract

## Design Decisions

1. **Panel-based dashboard** — each panel is independent. Add panels without touching existing ones. A panel's WebSocket being down only affects that panel.

2. **Two ports, not one multiplexed connection** — simpler implementation, independent lifecycles. The graph server can run as a daemon; the session server is tied to a CLI process.

3. **Server computes confidence** — UI receives precomputed confidence levels. No algorithm duplication across clients.

4. **Effort lifecycle on session side, not graph side** — the graph only knows `source: "effort-id"` as a string. It doesn't model effort open/close/switch. That's session semantics.

5. **Effort log is request/response** — chat history can be large. Fetched on demand from the session server, not pushed.
