# User Stories: Two-Log Proof of Concept

## Story 1: Capture Ambient Chatter

**As a** user
**I want to** have casual conversation with the assistant
**So that** I can ask quick questions without starting a focused effort

**Acceptance Criteria:**
- [ ] When I send a message not related to an open effort, it is saved to the ambient raw log (`raw.jsonl`)
- [ ] The assistant's response to my ambient message is also saved to the ambient raw log
- [ ] Ambient messages and responses are always included in the context for the next turn

## Story 2: Explicitly Open a New Effort

**As a** user
**I want to** explicitly start working on a specific task
**So that** my conversation about that task is isolated and can be managed separately

**Acceptance Criteria:**
- [ ] When I say "Let's work on X" or similar, the assistant creates a new effort file (`efforts/X.jsonl`)
- [ ] The assistant confirms the effort has been opened by name
- [ ] The effort is marked as "open" in the manifest
- [ ] My opening message and the assistant's confirmation are saved to the new effort's raw log

## Story 3: Capture Messages Within an Open Effort

**As a** user
**I want to** continue discussing the focused task
**So that** all relevant context stays together

**Acceptance Criteria:**
- [ ] When I send a message while an effort is open, it is saved to that effort's raw log (`efforts/X.jsonl`)
- [ ] The assistant's response is also saved to the same effort's raw log
- [ ] The entire raw log of an open effort is included in the context for the next turn

## Story 4: Handle Interruptions During an Effort

**As a** user
**I want to** ask a quick unrelated question in the middle of working on an effort
**So that** I can get immediate help without breaking my flow

**Acceptance Criteria:**
- [ ] When I ask an unrelated question while an effort is open, the message is routed to ambient (not to the effort)
- [ ] The effort log is not modified by the interruption
- [ ] The open effort remains open and its context is still available after the interruption

## Story 5: Explicitly Conclude an Effort

**As a** user
**I want to** signal when I'm done with a task
**So that** the conversation about that task can be summarized and removed from active context

**Acceptance Criteria:**
- [ ] When I say "X is done" or "looks good" about an open effort, the assistant creates a summary of the effort
- [ ] The assistant confirms the effort has been concluded by name
- [ ] The effort's status in the manifest changes from "open" to "concluded"
- [ ] The summary is added to the manifest
- [ ] My concluding message and the assistant's confirmation are saved to the effort's raw log

## Story 6: Remove Concluded Effort from Active Context

**As a** user
**I want** concluded efforts to not take up context space
**So that** I can work on new tasks without being slowed down by old conversations

**Acceptance Criteria:**
- [ ] After an effort is concluded, its raw log is no longer included in the context for subsequent turns
- [ ] Only the summary of the concluded effort (from the manifest) is included in the context
- [ ] The raw log file for the concluded effort is preserved on disk for potential future reference

## Story 7: Assemble Context from Multiple Sources

**As a** user
**I want** the assistant to have access to all relevant information
**So that** it can provide helpful responses based on our complete conversation history

**Acceptance Criteria:**
- [ ] The context for each turn includes: all ambient messages (`raw.jsonl`), all effort summaries (from `manifest.yaml`), and the full raw logs of all open efforts
- [ ] The context does NOT include the raw logs of concluded efforts
- [ ] When I open a new effort after concluding one, the context includes: ambient + all summaries + new effort's raw log

## Story 8: Start a New Effort After Concluding One

**As a** user
**I want to** begin working on a new task after finishing the previous one
**So that** I can maintain productivity without context pollution

**Acceptance Criteria:**
- [ ] After concluding an effort, I can say "Let's work on Y" to start a new effort
- [ ] The assistant creates a new effort file for Y
- [ ] The new effort is marked as "open" in the manifest
- [ ] The context includes: ambient + all summaries (including the just-concluded effort) + new effort's raw log

## Story 9: Verify Token Savings from Effort Management

**As a** product owner
**I want to** measure the token reduction when efforts are concluded
**So that** I can validate the core hypothesis of effort-based context management

**Acceptance Criteria:**
- [ ] The token count of the current context can be measured
- [ ] After concluding an effort, the measured token count is lower than before
- [ ] The token reduction is significant (e.g., 80%+ savings for that effort)
- [ ] The summary in the manifest is substantially smaller than the raw effort log it replaces