# Slice 1a: Minimal Effort Artifact Compaction - User Stories

Issue: N/A
Status: Draft
Dependencies: None

---

## Story 1: Start the CLI

**As a** user
**I want to** run `oi` in my terminal
**So that** I can start chatting immediately

**Acceptance:**
- [ ] Running `oi` displays a prompt ready for input
- [ ] No loading messages, splash screens, or instructions appear
- [ ] The prompt appears within 2 seconds of running the command

---

## Story 2: Send a Message and Get a Response

**As a** user
**I want to** type a question and press enter
**So that** I get an AI response

**Acceptance:**
- [ ] After I type and press enter, the AI response appears
- [ ] While waiting for the response, I see indication that it's thinking (cursor, spinner, or similar)
- [ ] The response is displayed in a readable format
- [ ] After the response finishes, a new prompt appears for my next message

---

## Story 3: Effort Artifact Extracted on Acceptance

**As a** user
**I want to** thank the AI or confirm its answer
**So that** the resolution is captured automatically

**Acceptance:**
- [ ] When I reply with acceptance (e.g., "Thanks!", "That makes sense", "Got it"), an artifact notification appears
- [ ] The notification shows the effort summary and resolution
- [ ] The artifact text is a concise summary of what was resolved (not a copy of the full conversation)
- [ ] The notification appears after my acceptance message, before the next prompt

**Format:**
```
[effort:resolved] Debug auth bug
  => Token was expired, refresh fixed it
```

**Trigger phrases that should cause extraction:**
- "Thanks!"
- "Ah, that makes sense"
- "Got it"
- "You're right"
- "That fixed it"
- Topic change to an unrelated question

---

## Story 4: Token Stats Shown After Artifact Extraction

**As a** user
**I want to** see how many tokens were saved
**So that** I understand the compaction benefit

**Acceptance:**
- [ ] Immediately after an artifact is extracted, token stats appear
- [ ] Stats show: raw tokens, compacted tokens, and savings percentage
- [ ] Format example: `[Tokens: 1,247 raw → 68 compacted | Savings: 95%]`
- [ ] Stats reflect only the effort that was just resolved (not cumulative)

---

## Story 5: Effort Stays Open on Disagreement

**As a** user
**I want to** push back or disagree
**So that** the conversation continues without premature resolution

**Acceptance:**
- [ ] When I reply with disagreement, no artifact is extracted
- [ ] No token stats appear
- [ ] The AI responds to my disagreement and the conversation continues
- [ ] The effort remains open until I eventually accept or change topic

**Disagreement phrases that should NOT trigger extraction:**
- "No, that's not it"
- "I don't think so"
- "But what about..."
- "That doesn't work"
- "I already tried that"

---

## Story 6: Multi-Turn Disagreement Before Acceptance

**As a** user
**I want to** go back and forth multiple times before reaching resolution
**So that** only the final answer becomes the artifact resolution

**Acceptance:**
- [ ] I can disagree multiple times in a row without artifacts being extracted
- [ ] When I finally accept, the artifact captures the final resolution (not earlier wrong answers)
- [ ] The artifact resolution reflects what actually solved the problem

---

## Story 7: Reference Earlier Artifacts in Same Session

**As a** user
**I want to** ask questions that reference things we discussed earlier
**So that** the AI remembers without me re-explaining

**Acceptance:**
- [ ] After an artifact is extracted, I can ask a follow-up that references it
- [ ] The AI responds with knowledge of the earlier resolution
- [ ] I do not need to re-explain the earlier topic
- [ ] Example: After resolving auth bug and db bug, asking "which was easier to fix?" gets a relevant answer

---

## Story 8: Exit the CLI

**As a** user
**I want to** type `exit` to close the program
**So that** I can end my session cleanly

**Acceptance:**
- [ ] Typing `exit` closes the program
- [ ] The program exits without error messages
- [ ] No confirmation prompt appears (immediate exit)

---

## Story 9: Persistence Across Restart

**As a** user
**I want to** close and reopen the CLI
**So that** I can continue where I left off

**Acceptance:**
- [ ] After exiting and running `oi` again, the conversation continues
- [ ] I can ask "what were we discussing?" and get an accurate answer
- [ ] Previous artifacts are available to the AI
- [ ] I do not need to re-explain earlier context

---

## Story 10: First Launch (No Existing State)

**As a** user
**I want to** run `oi` for the first time
**So that** I start with a fresh conversation

**Acceptance:**
- [ ] Running `oi` with no prior state shows a prompt (no error)
- [ ] The first message is handled normally
- [ ] A state file is created after the first interaction

---

## Story 11: Multiple Artifacts in One Session

**As a** user
**I want to** resolve multiple topics in a single session
**So that** each is captured as a separate artifact

**Acceptance:**
- [ ] Each time I accept/thank, a new artifact is extracted
- [ ] Each artifact has its own token stats displayed
- [ ] All artifacts are available for the AI to reference
- [ ] Later questions can reference any of the artifacts from the session

---

## Story 12: Topic Change Triggers Resolution

**As a** user
**I want to** ask a completely new question
**So that** the previous topic is resolved automatically

**Acceptance:**
- [ ] When I ask a new, unrelated question after the AI gave an answer, an artifact is extracted
- [ ] I do not need to explicitly thank or accept
- [ ] The new question is handled normally after the artifact is shown

---

## Story 13: Visual Distinction of System Messages

**As a** user
**I want to** clearly distinguish system messages from AI responses
**So that** I know what is artifact feedback vs. conversation

**Acceptance:**
- [ ] Artifact notifications are visually distinct (brackets, color, or prefix)
- [ ] Token stats are visually distinct
- [ ] AI responses are clearly separate from system feedback
- [ ] My own messages are distinguishable from AI messages

---

## Story 14: Conversation Flows Without Interruption

**As a** user
**I want to** chat naturally
**So that** artifact extraction feels seamless

**Acceptance:**
- [ ] Artifact notifications appear quickly (not blocking the next prompt)
- [ ] I can immediately type my next message after seeing the notification
- [ ] The flow feels like a normal chat, not a wizard or form
- [ ] No special commands or syntax required

---

## Out of Scope (Slice 1b)

The following are explicitly NOT part of this slice:
- Manual `/resolve` command
- Manual `/reject` command
- `/expand` to see full thread
- `/artifacts` to list all artifacts
- `/stats` to see cumulative stats
- Editing or correcting artifacts
- `/help` command
- Error recovery UI
