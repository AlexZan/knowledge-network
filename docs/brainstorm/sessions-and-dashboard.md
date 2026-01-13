# Sessions and Dashboard: The Knowledge Interface

## The Problem with Traditional Chat Interfaces

**Current AI chat UX:**
1. User needs to remember which chat has the right context
2. Scrolls through chat list looking for "that conversation about X"
3. Hopes the chat history has enough context
4. Can't easily combine context from multiple chats
5. No way to see what's "active" vs "concluded" at a glance

**Users are forced to:**
- Manage context manually through chat history
- Start new chats for new topics (losing cross-topic connections)
- Repeat context when resuming old topics

## The Insight: Context as First-Class Entity

**Instead of**: "Find the right chat with the right history"
**We enable**: "Build/load the right context explicitly"

The context builder becomes the primary interface, not the chat history.

## Sessions: Context Containers

### What is a Session?

A **session** is a named workspace containing:
- **Artifacts** (efforts, facts, events)
- **Recent message history**
- **Metadata** (created, last active, status)

Think: IDE workspaces, tmux sessions, or browser tab groups for conversations.

### Session Lifecycle

```
[new] → [open] → [concluded] → [archived]
           ↓
        [stale] (auto-detected)
```

**Open**: Active work, appears in main dashboard
**Concluded**: Resolved/finished, can be resumed if needed
**Stale**: Inactive for N days, system suggests archiving
**Archived**: Removed from main view, searchable

### Sessions ARE Artifacts!

```javascript
{
  "artifact_type": "session",
  "summary": "Debug authentication bug in work project",
  "status": "open",
  "resolution": null,  // Set when concluded
  "tags": ["work", "debugging", "auth"],
  "created": "2026-01-13T10:00:00Z",
  "last_active": "2026-01-13T15:30:00Z",
  "child_artifacts": [
    // All efforts, facts, events in this session
  ]
}
```

This makes sessions first-class in the knowledge network!

## Context Caching: Build Once, Reuse

### The Observation

**Context changes slowly!**

Artifacts portion: Only changes when new artifacts created (~30% of turns)
Messages portion: Changes every turn (grows by 2 messages)

**Currently**: We rebuild the full context every turn (wasteful!)

### Proposed: Cached Context per Session

```javascript
// session-123.json
{
  "session_id": "work-project-auth-debug",
  "name": "Debug authentication bug",
  "status": "open",

  // Cached context (rebuilt only when artifacts change)
  "artifacts_context": "Open efforts:\n1. Debug auth bug...",
  "artifacts_hash": "abc123def456",  // Detect changes

  // Growing message history (appends each turn)
  "recent_messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],

  "metadata": {
    "created": "2026-01-13T10:00:00Z",
    "last_active": "2026-01-13T15:30:00Z",
    "open_efforts": 2,
    "facts_count": 3,
    "message_count": 24
  }
}
```

### Context Building Algorithm

```python
def build_context(session):
    # Load session file
    session_data = load_session(session.id)

    # Check if artifacts changed
    current_hash = hash_artifacts(session.artifacts)

    if current_hash != session_data["artifacts_hash"]:
        # Rebuild artifacts context
        artifacts_context = render_artifacts(session.artifacts)
        session_data["artifacts_context"] = artifacts_context
        session_data["artifacts_hash"] = current_hash
        save_session(session_data)

    # Always use cached artifacts context
    context = [
        system_prompt,
        session_data["artifacts_context"],
        session_data["recent_messages"][-10:]  # Last 10 messages
    ]

    return context
```

**Benefits:**
- Build artifacts context once, reuse until changed
- Massive performance improvement for long sessions
- Still perfectly accurate (hash detects changes)
- Context file is small (compressed artifacts + recent messages)

## Multiple Sessions: Workspace Switching

Users can have multiple parallel contexts:

```bash
> /session new work-project
Created session: work-project
> /effort debug authentication bug
...

> /session new personal
Created session: personal
> /effort plan Japan trip
...

> /session list
● work-project (2 open efforts, 24 messages) - active
● personal (1 open effort, 12 messages) - 2h ago
○ gaming-research (concluded) - 3 days ago

> /session switch work-project
Switched to: work-project
Open efforts: 2
  • Debug authentication bug
  • Refactor user service
```

**Key benefit**: Context isolation + easy switching

No more "which chat was that in?" - just switch to the named session.

## Dashboard: The Knowledge Interface

### Vision

The dashboard is the primary entry point - a **customizable view over your knowledge network**.

Instead of a list of chats, users see:
- **Open sessions** (active workspaces)
- **Top efforts** (current goals across all sessions)
- **Recent conclusions** (what was resolved)
- **Stale sessions** (suggest conclude/archive)
- **Quick actions** (create session, search, etc.)

### Example: Developer Dashboard

```
╭─ Living Knowledge Dashboard ─────────────────────────────╮
│                                                           │
│ OPEN SESSIONS                                             │
│ ● work-project (2 efforts) - active                      │
│ ● side-project (1 effort) - 2h ago                       │
│                                                           │
│ PRIORITY EFFORTS                                          │
│ [open] Debug authentication bug - work-project           │
│   └─ Last: "Found issue in JWT validation"              │
│ [open] Add dark mode - side-project                      │
│                                                           │
│ RECENT CONCLUSIONS                                        │
│ ✓ Use Postgres over MySQL - work-project (2h ago)       │
│ ✓ API uses /v2/auth endpoint - work-project (yesterday) │
│                                                           │
│ STALE SESSIONS (conclude or archive?)                    │
│ ○ gaming-research (concluded 3 days ago)                 │
│ ○ weekend-idea (no activity, 7 days)                     │
│                                                           │
│ QUICK STATS                                               │
│ 12 open efforts · 45 facts · 3 active sessions           │
│                                                           │
├───────────────────────────────────────────────────────────┤
│ > Start talking or click above to resume context         │
╰───────────────────────────────────────────────────────────╯
```

### Example: Writer Dashboard

```
╭─ Living Knowledge Dashboard ─────────────────────────────╮
│                                                           │
│ ACTIVE DRAFTS (sessions)                                  │
│ ● chapter-3-rewrite (2 efforts) - active                 │
│ ● story-outline (concluded) - yesterday                  │
│                                                           │
│ WRITING TASKS (efforts)                                   │
│ [open] Fix pacing in Act 2 - chapter-3-rewrite          │
│ [open] Research medieval armor - chapter-5               │
│                                                           │
│ CHARACTER NOTES (facts)                                   │
│ • Elena: afraid of heights (backstory TBD)               │
│ • Marcus: former soldier, scar on left arm               │
│                                                           │
│ COMPLETED TODAY                                           │
│ ✓ Finished first draft of chapter 3                      │
│ ✓ Decided on third-person POV                            │
│                                                           │
│ WORD COUNT: 12,450 across 3 active chapters              │
│                                                           │
├───────────────────────────────────────────────────────────┤
│ > Continue writing or click above to resume              │
╰───────────────────────────────────────────────────────────╯
```

Same primitives (sessions, efforts, facts), different dashboard!

## Emergent Personalization

### The Vision

Dashboards **compose from primitives** and **emerge from usage**.

**Primitives:**
- Sessions (context containers)
- Efforts (goals)
- Facts (knowledge points)
- Events (temporal context)
- Artifacts (generic knowledge)

**Dashboard = Views over primitives**

### How It Works

1. **Start with defaults**: All users see generic dashboard
2. **Track usage patterns**: What does this user work on?
3. **Suggest customizations**: "Show open PRs as sessions?"
4. **User refines**: Drag, drop, configure widgets
5. **Dashboard evolves**: Becomes personalized control panel

### Configuration Examples

```yaml
# Developer dashboard config
dashboard:
  widgets:
    - type: sessions
      filter: status=open
      sort: last_active
      limit: 5

    - type: efforts
      filter: tags contains "bug"
      title: "Active Bugs"

    - type: facts
      filter: tags contains "api"
      title: "API Documentation"

    - type: stats
      show: [open_efforts, total_facts, active_sessions]
```

```yaml
# Writer dashboard config
dashboard:
  widgets:
    - type: sessions
      filter: tags contains "writing"
      title: "Active Drafts"

    - type: efforts
      filter: artifact_type=effort AND status=open
      title: "Writing Tasks"

    - type: facts
      filter: tags contains "character"
      title: "Character Notes"

    - type: custom
      query: "count words in all sessions"
      title: "Total Word Count"
```

**Key insight**: Same knowledge network, personalized interface!

## Session Commands

### Creating and Managing

```bash
# Create new session
> /session new work-auth
> /session new work-auth [tags: work, debugging, urgent]

# Switch sessions
> /session switch personal
> /session switch work-auth

# List sessions
> /session list
> /session list --all  # Include concluded/archived

# Rename
> /session rename work-auth → auth-bug-fix

# Conclude (mark as resolved)
> /session conclude
> /session conclude "Fixed JWT validation bug"

# Archive (remove from main view)
> /session archive gaming-research

# Resume archived
> /session resume gaming-research
```

### Context-Aware Commands

Commands are filtered based on current session:

```bash
# In open session with open effort:
Available: /effort /fact /resolve /conclude /switch

# In concluded session:
Available: /resume /archive /switch

# No active session:
Available: /session new /session list
```

## Implementation Considerations

### File Structure

```
~/.oi/
  state.json                    # Global state (all artifacts)
  sessions/
    work-project.json           # Session with cached context
    personal.json
    gaming-research.json
  chatlogs/
    work-project.jsonl          # Permanent message log
    personal.jsonl
    gaming-research.jsonl
  dashboards/
    default.yaml                # Dashboard configuration
    custom.yaml                 # User customization
```

### Session File Format

```javascript
{
  "session_id": "work-project-abc123",
  "name": "Debug authentication bug",
  "status": "open",
  "tags": ["work", "debugging", "auth"],

  // Cached context (artifact summaries)
  "artifacts_context": {
    "text": "Open efforts:\n1. Debug auth bug...",
    "hash": "abc123def456",
    "last_built": "2026-01-13T15:30:00Z"
  },

  // Metadata
  "metadata": {
    "created": "2026-01-13T10:00:00Z",
    "last_active": "2026-01-13T15:30:00Z",
    "message_count": 24,
    "artifact_ids": ["effort-1", "fact-2", "event-3"]
  },

  // Quick stats for dashboard
  "stats": {
    "open_efforts": 2,
    "resolved_efforts": 1,
    "facts": 3,
    "events": 5
  }
}
```

### Context Builder Updates

```python
def build_context(session_id: str) -> str:
    """Build context for a session with caching."""

    # Load session
    session = load_session(session_id)

    # Get current artifact hash
    artifacts = get_session_artifacts(session_id)
    current_hash = hash_artifacts(artifacts)

    # Check cache
    if current_hash == session.artifacts_context.hash:
        # Cache hit - reuse
        artifacts_text = session.artifacts_context.text
    else:
        # Cache miss - rebuild
        artifacts_text = render_artifacts(artifacts)
        session.artifacts_context = {
            "text": artifacts_text,
            "hash": current_hash,
            "last_built": now()
        }
        save_session(session)

    # Load recent messages
    recent_messages = load_chatlog(session_id, limit=10)

    # Assemble final context
    context = f"""
{system_prompt}

{artifacts_text}

Recent conversation:
{recent_messages}
"""

    return context
```

### Dashboard Rendering

```python
class Dashboard:
    def __init__(self, config: DashboardConfig):
        self.widgets = load_widgets(config)

    def render(self) -> str:
        """Render dashboard to text/terminal."""
        output = []

        for widget in self.widgets:
            data = widget.query()  # Query knowledge network
            rendered = widget.render(data)  # Render to text
            output.append(rendered)

        return "\n".join(output)

# Usage
dashboard = Dashboard.load_user_config()
print(dashboard.render())
```

## User Flows

### Flow 1: New User First Session

```
1. User launches oi
2. Dashboard shows: "No sessions yet. Start talking or create a session."
3. User types: "help me debug this code"
4. System auto-creates session: "session-2026-01-13" (timestamp)
5. User gets response
6. System interprets: "This is an effort"
7. Dashboard updates: "1 open session, 1 open effort"
```

### Flow 2: Returning User

```
1. User launches oi
2. Dashboard shows:
   - 2 open sessions (work-project, personal)
   - 3 open efforts across sessions
   - 2 recent conclusions
3. User clicks "work-project" session
4. Context loaded (cached artifacts + recent messages)
5. User continues conversation
```

### Flow 3: Concluding Work

```
1. User finishes debugging
2. User types: "/resolve used JWT secret validation"
3. System resolves effort with resolution
4. User types: "/session conclude Fixed auth bug"
5. Session marked as concluded
6. Dashboard updates: "1 open session, 0 open efforts in work-project"
7. Session moves to "concluded" section
```

### Flow 4: Resuming Old Work

```
1. User sees "gaming-research (concluded 3 days ago)"
2. User types: "/session resume gaming-research"
3. System loads session context (cached)
4. Shows: "Resumed: gaming-research. Conclusion: Chose Logitech mouse"
5. User: "actually, what about the Razer alternative?"
6. System reopens effort (was resolved, now open again)
7. Session status changes: concluded → open
```

## Integration with Cascading Inference

Sessions + cascading inference work together:

```
User: "/session new work-auth"
  → Command parsed (Level 1)
  → Session created instantly
  → No LLM call needed

User: "debug this auth issue"
  → Session context loaded (cached artifacts)
  → Main LLM responds
  → Interpretation: Is this an effort?
  → Cascading inference decides (command/pattern/local/remote)
  → Artifact created in session

User: "/resolve fixed it"
  → Command parsed (Level 1)
  → Current open effort resolved
  → Session stats updated
  → No LLM call needed
```

**Commands work at session AND artifact level!**

## Open Questions

### 1. Default Session Behavior

- Auto-create session on first message?
- Require explicit `/session new`?
- Use "default" session if none specified?

### 2. Session Isolation

- Are facts shared across sessions or isolated?
- Can efforts span multiple sessions?
- How to reference artifacts from other sessions?

### 3. Concluding Sessions

- Auto-conclude if all efforts resolved?
- Require explicit `/session conclude`?
- What happens to unresolved efforts?

### 4. Dashboard Defaults

- What does first-time user dashboard look like?
- When to suggest customization?
- Community dashboard templates?

### 5. Context Size Limits

- Max artifacts per session before suggesting split?
- Max messages before suggesting conclude?
- How to handle very long-running sessions?

### 6. Cross-Session Features

- Search across all sessions?
- Link artifacts between sessions?
- Merge sessions?
- Session hierarchies (project → tasks)?

## Success Metrics

**Efficiency:**
- Context build time (should be near-instant with caching)
- Cache hit rate (% of turns that reuse cached context)
- Average session length before conclusion

**User Experience:**
- Time to find relevant context (dashboard vs chat list)
- Session switch frequency
- Dashboard customization adoption

**Knowledge Quality:**
- Artifacts per session (density)
- Concluded vs abandoned sessions
- Cross-session artifact references

## Future: Advanced Features

### Session Analytics

```bash
> /session stats work-project

Session: work-project
Created: 2026-01-10
Duration: 3 days
Messages: 247
Efforts: 12 (8 resolved, 4 open)
Facts: 23
Tokens used: ~125,000
Tokens saved via compression: ~850,000 (87% reduction)
```

### Session Graphs

Visualize knowledge network for a session:

```
work-project
├── [effort] Debug auth bug
│   ├── [fact] JWT uses HS256
│   ├── [fact] Secret stored in .env
│   └── [resolved] Fixed validation logic
├── [effort] Refactor user service
│   └── [open] Extract to separate module
└── [event] Team meeting discussed API changes
```

### Session Templates

```bash
> /session new bug-fix --template=debugging

Created session: bug-fix
Template: debugging
  - Auto-tags: debugging, bug
  - Pre-loaded facts: project structure, common issues
  - Suggested efforts: reproduce bug, find root cause, fix, test
```

### Collaborative Sessions

```bash
> /session share work-project --with=teammate@example.com
> /session merge personal-research → team-project
```

## Key Insights

> **Sessions replace chat history as the unit of context.**
> Users build/load context explicitly rather than searching for the right chat.

> **Context caching makes long sessions efficient.**
> Rebuild artifacts context only when changed, reuse cached version otherwise.

> **Dashboards are personalized entry points to knowledge networks.**
> Same primitives, different views - emergent customization based on usage.

> **Sessions are first-class artifacts with lifecycle states.**
> Open, concluded, archived - just like efforts but at the workspace level.

> **The interface layer should be as flexible as the knowledge layer.**
> Composable primitives enable emergent, personalized experiences.

---

*Brainstormed: 2026-01-13*
*Status: Design phase*
*Dependencies: Cascading inference (slash commands), artifact system*
*Next: Create slice spec, prototype session file format*
