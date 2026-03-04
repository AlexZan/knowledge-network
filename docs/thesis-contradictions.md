# Thesis Contradictions Report

Auto-generated from `.oi-test/knowledge.yaml` after batch-linking 236 nodes
extracted from `docs/thesis.md`. **37 contradictions** found across
26 target nodes.

Each contradiction represents a tension the LLM detected between two claims
in the thesis. These are not necessarily errors — many reflect genuine
ambiguities worth resolving for clarity.

---

## Cluster: decision-001

**Target node** [decision]: The framework decides to represent each conclusion as a node within a growing knowledge network, allowing confidence to emerge from the network’s topology rather than explicit confidence scores.

4 contradiction(s) against this node:

### 1. fact-152 → decision-001

- **A** [fact]: Every confidence score in the knowledge graph is derived from auditable evidence.
- **B** [decision]: The framework decides to represent each conclusion as a node within a growing knowledge network, allowing confidence to emerge from the network’s topology rather than explicit confidence scores.
- **LLM reasoning**: Decision‑001 claims confidence emerges from topology without explicit scores, whereas Node A asserts every confidence score is explicitly derived from evidence.
- **Combined degree**: 69

### 2. fact-159 → decision-001

- **A** [fact]: In the near term, a mature knowledge graph can become structured training data, offering pre‑organized nodes, edges, confidence levels, and provenance chains, making fine‑tuning on graph data potentially far more efficient than training on unstructured text.
- **B** [decision]: The framework decides to represent each conclusion as a node within a growing knowledge network, allowing confidence to emerge from the network’s topology rather than explicit confidence scores.
- **LLM reasoning**: Node A assumes explicit confidence levels are part of the graph, whereas the decision states confidence emerges from topology without explicit scores.
- **Combined degree**: 63

### 3. fact-183 → decision-001

- **A** [fact]: Open Systems' voting-experience system could serve as the confidence mechanism for a public knowledge network.
- **B** [decision]: The framework decides to represent each conclusion as a node within a growing knowledge network, allowing confidence to emerge from the network’s topology rather than explicit confidence scores.
- **LLM reasoning**: Node A proposes a voting system as the confidence mechanism, opposing the claim that confidence should emerge from network topology.
- **Combined degree**: 62

### 4. fact-178 → decision-001

- **A** [fact]: The framework maps the concept of 'Confidence from support' to experience derived from upvotes in the Open Systems governance system.
- **B** [decision]: The framework decides to represent each conclusion as a node within a growing knowledge network, allowing confidence to emerge from the network’s topology rather than explicit confidence scores.
- **LLM reasoning**: Node A ties confidence to explicit upvote support, contradicting the claim that confidence emerges without explicit scores.
- **Combined degree**: 60

## Cluster: fact-103

**Target node** [fact]: If no explicit preference declaration is made, the conflict is flagged for user or roundtable resolution

2 contradiction(s) against this node:

### 5. fact-089 → fact-103

- **A** [fact]: Resolution of preference conflicts is context-dependent and may involve an explicit choice or coexistence
- **B** [fact]: If no explicit preference declaration is made, the conflict is flagged for user or roundtable resolution
- **LLM reasoning**: Node A introduces coexistence as a possible resolution, contradicting the claim that lack of explicit declaration always leads to flagging for user/roundtable.
- **Combined degree**: 42

### 6. fact-105 → fact-103

- **A** [fact]: The system prevents silent overwrites by making all conflicts explicit
- **B** [fact]: If no explicit preference declaration is made, the conflict is flagged for user or roundtable resolution
- **LLM reasoning**: Node A’s guarantee of explicitness opposes the claim that conflicts without explicit declaration are merely flagged for later resolution.
- **Combined degree**: 29

## Cluster: decision-014

**Target node** [decision]: Resolution of a preference conflict without explicit declaration requires an explicit choice from the user or roundtable

2 contradiction(s) against this node:

### 7. fact-089 → decision-014

- **A** [fact]: Resolution of preference conflicts is context-dependent and may involve an explicit choice or coexistence
- **B** [decision]: Resolution of a preference conflict without explicit declaration requires an explicit choice from the user or roundtable
- **LLM reasoning**: Node A allows coexistence as a resolution, opposing the decision that an explicit user or roundtable choice is required when no declaration is made.
- **Combined degree**: 41

### 8. fact-105 → decision-014

- **A** [fact]: The system prevents silent overwrites by making all conflicts explicit
- **B** [decision]: Resolution of a preference conflict without explicit declaration requires an explicit choice from the user or roundtable
- **LLM reasoning**: Node A eliminates the situation of conflicts without explicit declaration, contradicting the decision that such conflicts require an explicit user or roundtable choice.
- **Combined degree**: 28

## Cluster: fact-089

**Target node** [fact]: Resolution of preference conflicts is context-dependent and may involve an explicit choice or coexistence

2 contradiction(s) against this node:

### 9. fact-094 → fact-089

- **A** [fact]: Preference issues are resolved through an explicit declaration of choice by a participant.
- **B** [fact]: Resolution of preference conflicts is context-dependent and may involve an explicit choice or coexistence
- **LLM reasoning**: Node A requires an explicit declaration for resolution, while candidate 1 allows coexistence as an alternative.
- **Combined degree**: 36

### 10. decision-015 → fact-089

- **A** [decision]: User preferences must be set through explicit human choice to maintain user agency
- **B** [fact]: Resolution of preference conflicts is context-dependent and may involve an explicit choice or coexistence
- **LLM reasoning**: Node A insists on explicit choice, while the candidate allows coexistence without explicit choice.
- **Combined degree**: 29

## Cluster: fact-088

**Target node** [fact]: Preference conflicts are subjective choices where both options are valid

2 contradiction(s) against this node:

### 11. decision-014 → fact-088

- **A** [decision]: Resolution of a preference conflict without explicit declaration requires an explicit choice from the user or roundtable
- **B** [fact]: Preference conflicts are subjective choices where both options are valid
- **LLM reasoning**: Node A requires a single chosen winner, contradicting fact‑088’s claim that both options can remain valid.
- **Combined degree**: 32

### 12. fact-095 → fact-088

- **A** [fact]: The roundtable mechanism involves active user participation to select a winner for preference conflicts lacking explicit declarations.
- **B** [fact]: Preference conflicts are subjective choices where both options are valid
- **LLM reasoning**: Node A’s claim that a winner is selected conflicts with the idea that both options remain equally valid.
- **Combined degree**: 20

## Cluster: fact-010

**Target node** [fact]: Conclusion‑triggered compaction creates a knowledge network where node connectivity determines confidence levels without requiring manually assigned probabilities.

1 contradiction(s) against this node:

### 13. fact-183 → fact-010

- **A** [fact]: Open Systems' voting-experience system could serve as the confidence mechanism for a public knowledge network.
- **B** [fact]: Conclusion‑triggered compaction creates a knowledge network where node connectivity determines confidence levels without requiring manually assigned probabilities.
- **LLM reasoning**: Node A suggests an alternative voting‑based confidence method, conflicting with the idea that connectivity alone determines confidence.
- **Combined degree**: 44

## Cluster: fact-151

**Target node** [fact]: Every conclusion in the knowledge graph includes provenance information.

2 contradiction(s) against this node:

### 14. fact-146 → fact-151

- **A** [fact]: The neural network cannot explain why it knows the requirement to validate JWT tokens, lacking provenance information.
- **B** [fact]: Every conclusion in the knowledge graph includes provenance information.
- **LLM reasoning**: Fact‑151 asserts every conclusion includes provenance, which directly opposes Node A’s claim of missing provenance.
- **Combined degree**: 18

### 15. fact-147 → fact-151

- **A** [fact]: The neural network cannot show what evidence supports its conclusion about JWT validation, providing no audit trail.
- **B** [fact]: Every conclusion in the knowledge graph includes provenance information.
- **LLM reasoning**: Node A claims no audit trail exists, contradicting the claim that every conclusion includes provenance.
- **Combined degree**: 18

## Cluster: fact-053

**Target node** [fact]: Confidence score reflects two independent confirmations

1 contradiction(s) against this node:

### 16. fact-125 → fact-053

- **A** [fact]: Initial confidence in the principle "validate inputs at trust boundaries" was low because it relied on a single source
- **B** [fact]: Confidence score reflects two independent confirmations
- **LLM reasoning**: Node A notes only a single source, contradicting the statement that confidence reflects two independent confirmations.
- **Combined degree**: 28

## Cluster: fact-137

**Target node** [fact]: The knowledge network handles forgetting through conflict resolution, which is explicit and not catastrophic.

2 contradiction(s) against this node:

### 17. fact-133 → fact-137

- **A** [fact]: Traditional neural networks suffer catastrophic forgetting, where new training corrupts previously learned patterns.
- **B** [fact]: The knowledge network handles forgetting through conflict resolution, which is explicit and not catastrophic.
- **LLM reasoning**: Node A says forgetting is catastrophic, while the candidate claims forgetting is handled explicitly and not catastrophic.
- **Combined degree**: 13

### 18. fact-134 → fact-137

- **A** [fact]: Traditional neural networks require freezing to preserve learned knowledge.
- **B** [fact]: The knowledge network handles forgetting through conflict resolution, which is explicit and not catastrophic.
- **LLM reasoning**: Node A implies forgetting is catastrophic unless frozen, contradicting the claim that forgetting is handled explicitly and not catastrophic.
- **Combined degree**: 13

## Cluster: fact-127

**Target node** [fact]: Confidence emerges from the network structure without the need for manual scoring.

1 contradiction(s) against this node:

### 19. fact-183 → fact-127

- **A** [fact]: Open Systems' voting-experience system could serve as the confidence mechanism for a public knowledge network.
- **B** [fact]: Confidence emerges from the network structure without the need for manual scoring.
- **LLM reasoning**: Node A introduces a voting system, contradicting the statement that confidence emerges automatically from network structure.
- **Combined degree**: 25

## Cluster: fact-174

**Target node** [fact]: Thesis 5 defines confidence scoring based on network topology

1 contradiction(s) against this node:

### 20. fact-183 → fact-174

- **A** [fact]: Open Systems' voting-experience system could serve as the confidence mechanism for a public knowledge network.
- **B** [fact]: Thesis 5 defines confidence scoring based on network topology
- **LLM reasoning**: Node A's voting‑experience suggestion opposes the thesis that confidence scoring is based on network topology.
- **Combined degree**: 24

## Cluster: fact-094

**Target node** [fact]: Preference issues are resolved through an explicit declaration of choice by a participant.

1 contradiction(s) against this node:

### 21. fact-095 → fact-094

- **A** [fact]: The roundtable mechanism involves active user participation to select a winner for preference conflicts lacking explicit declarations.
- **B** [fact]: Preference issues are resolved through an explicit declaration of choice by a participant.
- **LLM reasoning**: Node A proposes resolution without an explicit declaration, opposing the claim that explicit choice is required.
- **Combined degree**: 23

## Cluster: fact-139

**Target node** [fact]: In Living Knowledge Networks the network itself serves as the model without a separate training phase

1 contradiction(s) against this node:

### 22. fact-158 → fact-139

- **A** [fact]: In the current stage, the large language model performs reasoning and a personal knowledge graph stores an individual user's accumulated experience, expanding automatically as a side effect of work.
- **B** [fact]: In Living Knowledge Networks the network itself serves as the model without a separate training phase
- **LLM reasoning**: Node A relies on a separate LLM for reasoning, contradicting the claim that the network itself serves as the model without separate training.
- **Combined degree**: 23

## Cluster: fact-038

**Target node** [fact]: Lessons learned in one session are not transferred to subsequent sessions

2 contradiction(s) against this node:

### 23. fact-059 → fact-038

- **A** [fact]: Lessons derived from personal conversations are often universally applicable.
- **B** [fact]: Lessons learned in one session are not transferred to subsequent sessions
- **LLM reasoning**: Node A suggests lessons can be universally applied across contexts, which opposes the claim that lessons are not transferred between sessions.
- **Combined degree**: 11

### 24. fact-068 → fact-038

- **A** [fact]: The privacy gradient framework organizes knowledge into four layers that progress from highly sensitive raw data to universally sharable fundamental concepts
- **B** [fact]: Lessons learned in one session are not transferred to subsequent sessions
- **LLM reasoning**: Node A implies that knowledge can become universally sharable across contexts, which conflicts with the claim that lessons learned in one session are not transferred to subsequent sessions.
- **Combined degree**: 11

## Cluster: fact-125

**Target node** [fact]: Initial confidence in the principle "validate inputs at trust boundaries" was low because it relied on a single source

1 contradiction(s) against this node:

### 25. fact-123 → fact-125

- **A** [fact]: Three additional projects cited the principle "validate inputs at trust boundaries", bringing total inbound support count to five and raising confidence to high
- **B** [fact]: Initial confidence in the principle "validate inputs at trust boundaries" was low because it relied on a single source
- **LLM reasoning**: Node A’s claim of high confidence conflicts with the earlier claim that confidence was low.
- **Combined degree**: 20

## Cluster: decision-006

**Target node** [decision]: For high‑confidence conclusions, the system should compact automatically without user prompting

2 contradiction(s) against this node:

### 26. decision-005 → decision-006

- **A** [decision]: The system should offer to compact when any of the identified triggers are detected
- **B** [decision]: For high‑confidence conclusions, the system should compact automatically without user prompting
- **LLM reasoning**: Node A proposes prompting the user to compact, while decision‑006 mandates automatic compacting without prompting.
- **Combined degree**: 10

### 27. fact-106 → decision-006

- **A** [fact]: The system preserves history, keeping superseded conclusions accessible
- **B** [decision]: For high‑confidence conclusions, the system should compact automatically without user prompting
- **LLM reasoning**: Node A's preservation of superseded conclusions conflicts with automatic compacting of high‑confidence conclusions.
- **Combined degree**: 8

## Cluster: decision-011

**Target node** [decision]: When an explicit preference declaration is made, the declared option becomes the winner and replaces the prior version.

1 contradiction(s) against this node:

### 28. fact-102 → decision-011

- **A** [fact]: Both the superseded old preference and the new preference remain stored in the network, allowing preferences to revert later
- **B** [decision]: When an explicit preference declaration is made, the declared option becomes the winner and replaces the prior version.
- **LLM reasoning**: Node A says the old preference remains stored for possible revert, contradicting decision‑011's claim that the prior version is replaced.
- **Combined degree**: 16

## Cluster: fact-095

**Target node** [fact]: The roundtable mechanism involves active user participation to select a winner for preference conflicts lacking explicit declarations.

1 contradiction(s) against this node:

### 29. fact-105 → fact-095

- **A** [fact]: The system prevents silent overwrites by making all conflicts explicit
- **B** [fact]: The roundtable mechanism involves active user participation to select a winner for preference conflicts lacking explicit declarations.
- **LLM reasoning**: Node A states all conflicts become explicit, contradicting the premise that roundtable selection is needed for conflicts lacking explicit declarations.
- **Combined degree**: 16

## Cluster: decision-016

**Target node** [decision]: Validate inputs at trust boundaries as a recommended security practice

1 contradiction(s) against this node:

### 30. fact-125 → decision-016

- **A** [fact]: Initial confidence in the principle "validate inputs at trust boundaries" was low because it relied on a single source
- **B** [decision]: Validate inputs at trust boundaries as a recommended security practice
- **LLM reasoning**: Node A's indication of low confidence undermines the recommendation to adopt the principle as a security practice.
- **Combined degree**: 16

## Cluster: decision-020

**Target node** [decision]: Persist conclusions across sessions in the knowledge base

1 contradiction(s) against this node:

### 31. fact-037 → decision-020

- **A** [fact]: Each conversation operates in isolation without sharing information across sessions
- **B** [decision]: Persist conclusions across sessions in the knowledge base
- **LLM reasoning**: Node A says conversations are isolated across sessions, while the candidate proposes persisting conclusions across sessions.
- **Combined degree**: 14

## Cluster: decision-005

**Target node** [decision]: The system should offer to compact when any of the identified triggers are detected

1 contradiction(s) against this node:

### 32. fact-106 → decision-005

- **A** [fact]: The system preserves history, keeping superseded conclusions accessible
- **B** [decision]: The system should offer to compact when any of the identified triggers are detected
- **LLM reasoning**: Offering compacting could remove superseded conclusions, contradicting Node A's emphasis on keeping them accessible.
- **Combined degree**: 12

## Cluster: fact-078

**Target node** [fact]: Value extraction allows lessons to be shared without exposing the original source data

1 contradiction(s) against this node:

### 33. fact-038 → fact-078

- **A** [fact]: Lessons learned in one session are not transferred to subsequent sessions
- **B** [fact]: Value extraction allows lessons to be shared without exposing the original source data
- **LLM reasoning**: Node A states lessons are not transferred, while the candidate claims lessons can be shared via value extraction.
- **Combined degree**: 11

## Cluster: fact-014

**Target node** [fact]: The framework addresses the problem of knowledge integrity by providing mechanisms to update beliefs without causing catastrophic forgetting.

1 contradiction(s) against this node:

### 34. fact-134 → fact-014

- **A** [fact]: Traditional neural networks require freezing to preserve learned knowledge.
- **B** [fact]: The framework addresses the problem of knowledge integrity by providing mechanisms to update beliefs without causing catastrophic forgetting.
- **LLM reasoning**: Node A says freezing is required to avoid forgetting, while the candidate claims the framework can update beliefs without causing catastrophic forgetting.
- **Combined degree**: 11

## Cluster: fact-145

**Target node** [fact]: A neural network knows that JWT tokens should be validated before database queries, a behavior learned from millions of Stack Overflow posts and security guides during training.

1 contradiction(s) against this node:

### 35. fact-149 → fact-145

- **A** [fact]: The neural network cannot distinguish between widely repeated statements and statements that are actually true, conflating popularity with truth.
- **B** [fact]: A neural network knows that JWT tokens should be validated before database queries, a behavior learned from millions of Stack Overflow posts and security guides during training.
- **LLM reasoning**: Node A claims widespread repetition can create false beliefs, contradicting fact‑145’s implication that learning from many sources yields correct knowledge.
- **Combined degree**: 9

## Cluster: fact-015

**Target node** [fact]: Current conversation systems compact information based on capacity constraints

1 contradiction(s) against this node:

### 36. preference-003 → fact-015

- **A** [preference]: The framework prefers continuous mini-compactions over delayed compaction based on memory pressure
- **B** [fact]: Current conversation systems compact information based on capacity constraints
- **LLM reasoning**: Fact‑015 states systems compact based on capacity constraints (implying delayed compaction), which opposes Node A’s preference for continuous mini‑compactions.
- **Combined degree**: 7

## Cluster: fact-146

**Target node** [fact]: The neural network cannot explain why it knows the requirement to validate JWT tokens, lacking provenance information.

1 contradiction(s) against this node:

### 37. fact-145 → fact-146

- **A** [fact]: A neural network knows that JWT tokens should be validated before database queries, a behavior learned from millions of Stack Overflow posts and security guides during training.
- **B** [fact]: The neural network cannot explain why it knows the requirement to validate JWT tokens, lacking provenance information.
- **LLM reasoning**: Node A claims the network’s knowledge comes from many sources, contradicting the claim that it lacks any provenance.
- **Combined degree**: 7
