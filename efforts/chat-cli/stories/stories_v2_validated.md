# User Stories: Effort-Based Context Management

## Story 1: Start a New Session with Ambient Chat

**As a** user
**I want to** start a chat session with the assistant
**So that** I can begin a conversation without immediately focusing on a specific task

**Acceptance Criteria:**
- [ ] When I start a session, I can exchange casual messages with the assistant
- [ ] These initial messages are stored in the ambient conversation log (raw.jsonl)

## Story 2: Open a New Effort

**As a** user
**I want to** explicitly open a new effort
**So that** I can focus on a specific task and have its context isolated from ambient chat

**Acceptance Criteria:**
- [ ] When I state my intent to work on a specific task (e.g., "Let's debug the auth bug"), the assistant acknowledges opening a new effort
- [ ] The system creates a new effort file (e.g., `efforts/auth-bug.jsonl`)
- [ ] The effort is marked as "open" in the session manifest
- [ ] Messages that contain keywords from the effort name (e.g., "auth" or "bug" for "auth-bug") or explicitly reference the effort's context (e.g., "this bug", "the auth issue") are stored in the effort file; messages without such keywords or references are stored in the ambient log.

## Story 3: Work Within an Open Effort

**As a** user
**I want to** have a focused conversation about the effort
**So that** all relevant context for that task is available to the assistant

**Acceptance Criteria:**
- [ ] While an effort is open, my messages about that task and the assistant's responses are appended to the effort file
- [ ] The assistant has access to the full conversation history of the open effort
- [ ] The ambient conversation log does not grow with effort-related messages

## Story 4: Interrupt an Effort with Ambient Chat

**As a** user
**I want to** ask unrelated questions while an effort is open
**So that** I can handle quick distractions without polluting the effort context

**Acceptance Criteria:**
- [ ] When I ask a question that does NOT contain keywords from the open effort's name (e.g., "auth" or "bug" for "auth-bug") and does NOT explicitly reference the effort's context, the assistant responds appropriately
- [ ] The unrelated exchange is stored in the ambient conversation log (raw.jsonl)
- [ ] The open effort file is not modified by the interruption

## Story 5: Conclude an Open Effort

**As a** user
**I want to** explicitly conclude an effort
**So that** its detailed context is removed from the active session to save tokens, but its knowledge is preserved

**Acceptance Criteria:**
- [ ] When I state that the effort is complete (e.g., "Bug is fixed!"), the assistant acknowledges concluding the effort
- [ ] The effort status in the manifest changes from "open" to "concluded"
- [ ] The assistant provides a brief summary of what was accomplished
- [ ] The effort's raw conversation file is preserved in the filesystem but its content is removed from the active session context
- [ ] The session's total context size decreases significantly (showing token savings)

## Story 6: Open a New Effort After Concluding a Previous One

**As a** user
**I want to** start a new effort after concluding a previous one
**So that** I can work on a different task with a clean, focused context

**Acceptance Criteria:**
- [ ] After concluding an effort, I can state my intent to work on a new task
- [ ] The assistant opens a new effort with its own isolated file
- [ ] The new effort is marked as "open" in the manifest
- [ ] The concluded effort remains in the manifest but its raw log is not included in the active context

## Story 7: Reference a Concluded Effort On-Demand

**As a** user
**I want to** ask for specific details from a concluded effort
**So that** I can recall precise information without keeping all old context in memory

**Acceptance Criteria:**
- [ ] When I explicitly ask about something from a concluded effort by name or description (e.g., "what was the exact code from the auth bug effort?"), the assistant can retrieve it
- [ ] The assistant reads from the specific concluded effort's raw log file to find the exact details
- [ ] The retrieved information is presented to me in the current conversation
- [ ] The concluded effort's full context is not permanently added back to the active session; only the specific retrieved information is included in the response.