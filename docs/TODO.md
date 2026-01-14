# Design TODO

Open threads from brainstorming sessions that need further exploration.

---

## High Priority

### 1. Child Efforts Design
**Status**: Mentioned, not designed
**Question**: How does effort hierarchy work? When is something a child effort vs a new chat?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - "Constraint as Feature" section

Open questions:
- [ ] What makes something a "child" vs "sibling" effort?
- [ ] How deep can nesting go?
- [ ] How do child efforts roll up to parent?
- [ ] Can a child effort become its own chat (promotion)?

---

### 2. Chat Log Format
**Status**: Mentioned, not designed
**Question**: What does the summarized chat log artifact look like?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - "Two files per chat" concept
- [refined-chat-model.md](brainstorm/refined-chat-model.md) - Chat + artifacts model

Open questions:
- [ ] What fields does a chat log entry have?
- [ ] How is it different from an effort artifact?
- [ ] What level of detail in summaries?
- [ ] How are links to raw logs stored?

---

### 3. Slice 1 Redesign
**Status**: Likely needed
**Question**: Apply new "one chat = one effort" model to concrete implementation

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - New model
- [1a-minimal.md](slices/1a-minimal.md) - Original slice spec
- [1a-minimal-scenario.md](scenarios/1a-minimal-scenario.md) - Original scenario
- [1a-minimal-stories.md](stories/1a-minimal-stories.md) - Original stories

Open questions:
- [ ] Does "open/resolved" artifact state still make sense?
- [ ] How does the bug we found get resolved in new model?
- [ ] What's the new minimal scenario?

---

## Medium Priority

### 4. Fork Mechanics
**Status**: Mentioned, not designed
**Question**: What gets copied when forking? How does context transfer?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - Topic change handling
- [refined-chat-model.md](brainstorm/refined-chat-model.md) - Fork concept

Open questions:
- [ ] Fork = full copy or selective copy?
- [ ] Does forked chat link back to parent?
- [ ] How is fork different from "new chat with artifacts"?

---

### 5. Vector Filtering Design
**Status**: Mentioned, not designed
**Question**: How do we calculate relevance for filtering low-value turns?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - Lazy compaction section
- [refined-chat-model.md](brainstorm/refined-chat-model.md) - RAG strategy

Open questions:
- [ ] How to calculate "chat vector" (overall topic)?
- [ ] What similarity threshold for filtering?
- [ ] Filter on every prompt or only during compaction?
- [ ] What about turns that are low relevance but important (corrections)?

---

### 6. AI Chat Retrieval
**Status**: Mentioned, not designed
**Question**: How does AI find relevant old context for new chats?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - Chat management section
- [refined-chat-model.md](brainstorm/refined-chat-model.md) - RAG strategy

Open questions:
- [ ] Search artifacts, chat logs, or both?
- [ ] How to rank relevance?
- [ ] How much old context to pull in?
- [ ] User confirmation before pulling old context?

---

## Medium Priority (Human Interface)

### 9. Human Context Dashboard
**Status**: New, brainstormed
**Question**: How do we help humans manage their cognitive load alongside AI context?

Supporting docs:
- [human-context-management.md](brainstorm/human-context-management.md) - Full brainstorm

Core insight: The human has a context limit too. They lose track of artifacts created, decisions made, relationships between things.

Needs:
- [ ] Session summary generation (what was created/decided)
- [ ] Artifact inventory view (grouped by type, project, effort)
- [ ] Relationship visualization (how artifacts connect)
- [ ] Search/filter across artifacts
- [ ] Effort-artifact linking (what artifacts belong to which effort)

Open questions:
- [ ] TUI vs web dashboard vs both?
- [ ] Auto-generate summaries or manual?
- [ ] Integration with existing tools (Obsidian, Notion)?

---

## Lower Priority

### 7. Agents Revisited
**Status**: Open question
**Question**: If context is self-managing, what role do subagents play?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - "Agents in This Model" section
- [refined-chat-model.md](brainstorm/refined-chat-model.md) - Agent-artifact architecture

Open questions:
- [ ] Are subagents still needed for separate context?
- [ ] Subagents for parallelism instead of context isolation?
- [ ] Subagents as "effort executors" with specific instructions?
- [ ] Interactive main agent vs autonomous subagent - when to use which?

---

### 8. Effort Weight Inference
**Status**: Partially designed
**Question**: How is effort weight automatically inferred?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - Effort weight section + Focus constraint section

Decisions made:
- [x] Default weights per effort type (dev=high, learning=low, etc.)
- [x] Weight controls focus constraint (high=locked, low=flexible)
- [x] User overrides via `/lock`, `/unlock`, `/weight`

Open questions:
- [ ] What keywords/signals trigger what weight?
- [ ] Can weight change mid-effort?
- [ ] How to detect effort type reliably?

---

### 10. Model Escalation Strategy
**Status**: Captured, not detailed
**Question**: How do we minimize cost by defaulting to cheap models and escalating only on failure?

Supporting docs:
- [effort-scoped-context.md](brainstorm/effort-scoped-context.md) - Model escalation section
- Open Colony pipeline had this (GLM → Sonnet → Opus)

Core concept:
- Start with free/cheap tier (GLM, Haiku)
- Escalate after 2 failures at current tier
- Effort weight influences starting tier and escalation speed
- Track cost per effort, show user breakdown

Open questions:
- [ ] How to detect "failure" vs "needs user input"?
- [ ] De-escalation logic (when to go back to cheap)?
- [ ] Task→model mapping learned from usage?
- [ ] Fine-tuning cheap models on expensive successes?

---

## Completed

_(Move items here when done)_
