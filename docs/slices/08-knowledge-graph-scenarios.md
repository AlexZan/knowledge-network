# Slice 8 Scenario: Knowledge Graph

A complete walkthrough of the Slice 8 experience — Conclusion Nodes, Connections & Queries, Abstraction & Privacy, Conflict Resolution, and Emergent Confidence.

Updated to reflect [Decision 010](../decisions/010-one-chat-no-projects.md) (one chat, no projects), [Decision 011](../decisions/011-efforts-are-kg-nodes.md) (everything is a node), and [Decision 012](../decisions/012-session-as-audit-log.md) (sessions as audit logs).

**Design principle**: The knowledge graph is the agent's brain, not the user's dashboard. The user interacts with an intelligent agent that *thinks* using its accumulated knowledge. The graph internals (node types, confidence scores, edge classifications) are machinery — they surface only when the user asks to dig deeper, never as the default interface.

---

## The Session

### Scenario 1: The First Nodes

It's a Monday morning and I've been using `oi` for a few weeks — mostly debugging and architecture discussions on a backend API service. I launch:

```
oi
```

```
[3 open effort(s)]
  - auth-bug (active)
  - rate-limiter
  - db-pool-sizing

>
```

I start in on today's problem.

```
> I keep getting intermittent 401s on the /health endpoint. Only on the second request, never the first. Happens about 30% of the time.
```

The assistant opens an effort and we dig in. Fifteen minutes later I've found it — the token validator is reading from a cache that hasn't been warmed on connection reuse. I type the resolution:

```
> Got it. The token cache isn't initialized on reused connections. Fixed by calling warm_cache() in the connection factory. Done.
```

The assistant calls `close_effort`. The usual summary appears, and beneath it something new — a quiet note:

```
Effort concluded: token-cache-bug

  Summary: Intermittent 401s on /health caused by uninitialized token cache
  on reused connections. Fix: call warm_cache() in connection factory.

  Learned:
    - Token cache must be initialized on connection reuse
    - Always validate auth state at connection initialization, not first use
```

Short, plain language. The system is telling me what it took away from the effort — what it'll remember. I go back to work. Over the next few days I conclude two more efforts: `jwt-expiry-edge-case` and `api-gateway-timeout`. Each conclusion prints similar "Learned" lines. I don't think much of it.

---

### Scenario 2: Past Experience Informs New Work

Three days later I'm starting on a mobile API wrapper for the same backend service.

```
> I need to design the auth flow for the mobile app. We'll use JWTs with
> refresh tokens. What should I be thinking about?
```

The response covers the standard JWT advice — expiry windows, secure storage, refresh mechanics. But then it adds something I wasn't expecting:

```
One thing to watch out for: mobile clients pool TCP connections, and
I've seen auth state go stale on reused connections before. When we
debugged the token-cache-bug, the root cause was that the token
validator wasn't re-initialized on connection reuse — second requests
on a reused connection would intermittently 401.

I'd recommend validating token freshness per-request rather than
trusting the pooled connection's existing headers. We also ran into
a related issue with jwt-expiry-edge-case where expired tokens
weren't cleared on rotation — worth building the token lifecycle as
a state machine (issue → validate → rotate → revoke) rather than
ad hoc checks.
```

I read this and feel a small jolt of recognition. It's right — I already burned time on this exact class of bug. The assistant didn't dump a list of "knowledge nodes" at me. It just... knew, and wove it into its advice like a colleague who'd been there for the first debugging session.

I could ask "what are you basing that on?" and it would show me the specific conclusions it drew from, the efforts they came from, how confident it is. But I don't need to. The advice is specific, grounded, and actionable.

We conclude the effort later that day. The assistant's "Learned" section notes the connection: "Mobile auth design informed by prior token cache and JWT expiry findings."

---

### Scenario 3: The Pattern Emerges

A week later I'm debugging why certain financial transaction batches are being partially processed. After an hour of tracing, I find it: the batch processor validates the authorization token at batch submission time, but individual record processors re-use a cached credential that expires mid-batch. Late records fail silently.

```
> Found it. The credential is validated at batch start but not at record
> processing time. Records processed after credential expiry fail silently.
> Fixed by checking credential freshness per record. Done.
```

The effort closes. The "Learned" section appears — and this time there's an extra line:

```
  Learned:
    - Batch processors must validate credentials per record, not just
      at batch submission
    - Credential freshness must be checked at each processing unit

  I'm noticing a pattern: this is the third time I've seen auth state
  go stale between the point where it was validated and the point where
  it was actually used. The token cache bug, the JWT rotation issue,
  and now this batch credential problem are all the same class of mistake.

  Generalized: "Validate auth state where trust is consumed, not where
  the request enters the system."
```

That last part is new. The system noticed the convergence on its own — three different efforts, all pointing at the same underlying principle. It didn't ask me to tag or categorize anything. It just told me what it sees.

```
> That's a good catch. What's the difference between the specific
> lessons and that generalized one?
```

```
The specific lessons are tied to their context — "check credential
freshness per record in batch systems" only applies to batch processing.
The generalized version strips those details and captures the underlying
principle: validate where you consume, not where you receive.

The specific ones are private to your work. The general one is
something you could put in a code review guideline or share with a
team without revealing anything about your projects.
```

I hadn't asked for a privacy analysis. But the distinction makes sense — and it means the system is quietly building layers of knowledge, from raw debugging details up to principles I could actually teach someone.

---

### Scenario 4: The Contradiction

Two months have passed. I've been using `oi` across many different efforts. The knowledge graph has grown quietly in the background. I've mostly forgotten about it.

I start a new effort on a high-throughput message queue. After some profiling, I conclude that validating message signatures on every dequeue is the bottleneck. My recommendation: validate once at ingestion, cache the result, and skip re-validation on dequeue.

```
> Profiling shows signature validation on dequeue is 40% of processing
> time. We should validate at ingestion and cache the result. Done.
```

The effort closes. The summary appears. Then something I haven't seen before:

```
  Learned:
    - For this message queue, validate signatures at ingestion and
      cache the result

  I need to flag something: this conclusion conflicts with advice
  I've been applying elsewhere.

  You're recommending: validate once at entry, skip re-validation later.
  But I've also learned (from three prior efforts): validate at the
  point of consumption, not at entry.

  Both can't be right as general rules. I think they might apply to
  different situations, but I want your input before I reconcile them.

  From what I can see:
    - The prior principle (validate at consumption) came from cases
      where auth state *changed* after entry — cached credentials
      expired, tokens rotated. The bug was stale state.
    - This new case involves signature validation — a cryptographic
      property of the message itself. A valid signature at ingestion
      remains valid. The message doesn't change.

  My suggestion: "Validate mutable auth state at each consumption
  point. Validate immutable properties once at entry and cache."

  Does that capture the right distinction, or do you see it differently?
```

I stare at this for a moment. It's right — I argued both sides at different times for different reasons. And the suggested resolution is better than either original principle. I type:

```
> That's exactly right. The distinction is mutable vs immutable state.
> Go with your suggestion.
```

```
  Updated. The new principle replaces both predecessors:
    "Validate mutable auth state at each consumption point. Validate
    immutable properties once at entry and cache the result."

  The previous conclusions are still in my memory as context for how
  we got here, but this refined version is what I'll apply going forward.
```

The system caught something I would have held as two unrelated conclusions for months without noticing they pointed in different directions. And it asked me to weigh in rather than silently resolving it or dumping a raw conflict report.

---

### Scenario 5: Accumulated Expertise

Six months on. I've concluded well over a hundred efforts. I'm starting a new engagement — a security review for a third-party service, which means I'm thinking from first principles about auth architecture.

```
> I'm doing a security review of an external service. I want to know what
> I've learned about auth vulnerabilities from my own work — the
> patterns I keep seeing.
```

```
From everything I've seen across your auth work, there's a strong
pattern: auth bugs almost always come from trusting cached state that
has since changed. The fix is consistently to validate closer to the
point of use than feels convenient.

The core principle I'd apply to this review:

  "Validate mutable auth state at each consumption point. Validate
  immutable properties once at entry and cache the result."

This has held up across seven independent efforts — token cache
issues, JWT rotation bugs, batch credential expiry, and more. One
challenge to it (the message queue optimization) turned out to
refine rather than disprove it.

Related things I'd check for:
  - Token lifecycle: is it managed as a state machine, or ad hoc?
    (I've seen rotation bugs twice when it's ad hoc)
  - Auth failure handling: does the system fail loudly or degrade
    silently? Silent degradation has been the root cause in two
    efforts.

Want me to build a review checklist from this, or dig into any of
the specific cases I'm drawing from?
```

This reads like advice from a senior colleague who's been through the wars. The system didn't show me a graph query with node types and confidence levels. It synthesized its accumulated experience into actionable guidance, with an offer to show its work if I want to go deeper.

```
> Build the checklist. And actually — I'm curious how you arrived at
> that core principle. Can you show me the trail?
```

The assistant walks me through the history: the first token-cache-bug where the principle was born as a specific observation, the JWT rotation issue that confirmed it, the batch credential bug that triggered the generalization, and the message queue contradiction that sharpened it. It pulls up the session log from the original token-cache-bug debugging — the dead ends, the hypotheses I rejected, the moment I asked "wait, is the cache even initialized here?"

The full reasoning trail, from raw debugging session to high-confidence principle, is traceable. But I only see it because I asked. The default experience is just good advice.

```
> Great. I'm done with the security review. Done.
```

```
Effort concluded: security-review

  Summary: Reviewed auth architecture of external service using
  accumulated auth principles. Key recommendation: validate mutable
  auth state at consumption, not at entry.

  Learned:
    - This service validates session tokens at the API gateway only —
      downstream services trust forwarded headers
    - Gateway-only validation is likely insufficient for multi-tier
      architectures (new observation, would need more evidence to
      confirm as a pattern)
```

The new observation sits quietly. If another effort confirms it, the system will strengthen the conclusion. If something contradicts it, I'll hear about it. Either way, the knowledge graph grows — and I just keep working.

---

## What I Observed

1. Launching `oi` shows open efforts — no project name, no session number, no knowledge graph stats.
2. When an effort concludes, a "Learned" section beneath the summary shows what the system took away, in plain language — not raw graph data.
3. When starting work on a related topic, the assistant weaves past experience into its advice naturally — like a colleague who remembers what happened last time.
4. The assistant doesn't dump node lists or ask me to evaluate relevance. It applies what it knows and lets me dig deeper if I want to.
5. When enough instances of the same insight accumulate, the system notices the pattern and tells me it's generalizing — explaining the abstraction in plain terms, not graph jargon.
6. The generalized principle is naturally framed as shareable (no identifying details) vs. specific (context-bound), without me asking about privacy.
7. When the system's accumulated knowledge contradicts itself, it flags the conflict, explains both sides with context, suggests a resolution, and asks for my input — rather than silently resolving or dumping raw conflict data.
8. The resolution flow reads like a conversation with a thoughtful colleague, not a database conflict resolution UI.
9. When I explicitly ask for expertise on a topic, the system synthesizes its knowledge into actionable advice — structured by relevance, not by graph topology.
10. Confidence is implicit in how the system presents things: strong patterns are stated confidently ("this has held up across seven efforts"), weak ones are hedged ("new observation, would need more evidence").
11. The full reasoning trail — from raw debugging sessions to generalized principles — is traceable when I ask for it, but never thrust at me.
12. Session logs preserve the brainstorm paths, dead ends, and ambient reasoning that produced each conclusion — the "dark matter" between knowledge nodes.

---

## What I Didn't Have To Do

- No managing projects or remembering project names — I just type `oi` and talk
- No reading graph query output to figure out what's relevant — the agent decided and applied it
- No evaluating confidence scores or node types — the agent used them internally and presented advice at the right confidence level
- No manually connecting past efforts to current work — the agent recognized the patterns and brought them in
- No categorizing or tagging conclusions — the system inferred what to remember from the content
- No reviewing old efforts for contradictions — the system flagged the conflict when it arose
- No managing a knowledge base — the graph grew as a side effect of working
- No asking "what do I know about X?" unless I wanted to dig deeper — the system proactively applied relevant knowledge
- No privacy management — specific details stayed private, generalizations were naturally shareable
- No worrying about losing brainstorm context — session logs captured everything, conclusions or not
