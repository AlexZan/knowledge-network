# Slice 8 Scenario: Knowledge Graph

A complete walkthrough of the Slice 8 experience — Conclusion Nodes, Connections & Queries, Abstraction & Privacy, Conflict Resolution, and Emergent Confidence.

---

## The Session

### Scenario 1: The First Nodes

It's a Monday morning and I've been using `oi` for a few weeks on a backend project — mostly debugging and architecture discussions. I launch with my usual invocation:

```
oi --project api-service
```

The familiar header appears:

```
[Project: api-service | Session #31]
[3 concluded effort(s) searchable]

Type 'exit' to quit.
```

I've concluded three efforts in this project so far: `auth-bug`, `rate-limiter`, and `db-pool-sizing`. I start in on today's problem.

```
> I keep getting intermittent 401s on the /health endpoint. Only on the second request, never the first. Happens about 30% of the time.
```

The assistant opens an effort and we dig in. Fifteen minutes later I've found it — the token validator is reading from a cache that hasn't been warmed on connection reuse. I type the resolution:

```
> Got it. The token cache isn't initialized on reused connections. Fixed by calling warm_cache() in the connection factory. Done.
```

The assistant calls `close_effort`. But something new happens after the usual summary appears. A second banner prints beneath it:

```
Effort concluded: token-cache-bug

  Summary: Intermittent 401s on /health caused by uninitialized token cache
  on reused connections. Fix: call warm_cache() in connection factory.

  Knowledge nodes extracted:
    [fact]       Token cache must be initialized on connection reuse
    [solution]   Call warm_cache() in the connection factory, not lazily
    [principle]  Validate auth state at connection initialization, not at
                 first use
```

I pause. I've never seen those lines before. I type:

```
> What are knowledge nodes?
```

```
Knowledge nodes are conclusions I extract from your efforts and store
permanently in a graph — separate from any session. Unlike effort summaries,
which are per-project memory, nodes accumulate across everything and become
queryable.

These three nodes are now in your knowledge graph:
  - The fact (specific to this project and this bug)
  - The solution (the concrete fix)
  - The principle (the generalized lesson: initialize auth at connection
    setup, not deferred)

Over time the graph connects these nodes to related conclusions from other
efforts, other projects, and other contexts. That's when it gets interesting.
```

I go back to work. Over the next two sessions I conclude two more efforts on this project: `jwt-expiry-edge-case` (a bug where expired tokens weren't being cleared on rotation) and `api-gateway-timeout` (a misconfigured upstream timeout causing cascading failures). Each conclusion prints a similar banner. I don't think much of it.

---

### Scenario 2: The Query

Three days later I'm starting a new project: a mobile API wrapper for the same backend service. I launch with:

```
oi --project mobile-api
```

```
[Project: mobile-api | Session #1]
[0 concluded effort(s) searchable]

Type 'exit' to quit.
```

Fresh project, blank slate. I start planning the auth layer for the mobile client.

```
> I need to design the auth flow for the mobile app. We'll use JWTs with
> refresh tokens. What should I be thinking about?
```

The response is solid — standard JWT advice about expiry windows, secure storage, refresh mechanics. Then I notice a line at the bottom that wasn't there before:

```
> I also found 4 relevant nodes in your knowledge graph from past work.
> Type `show knowledge` to see them, or I can incorporate them now.
```

I type:

```
> show knowledge
```

```
Knowledge graph results for "JWT auth mobile":

  [principle]  Validate auth state at connection initialization, not at
               first use
               Source: token-cache-bug (api-service) | Confidence: low

  [fact]       Token cache must be initialized on connection reuse
               Source: token-cache-bug (api-service) | Confidence: low

  [solution]   On token rotation, clear expired tokens before issuing new
               ones — don't rely on expiry check alone
               Source: jwt-expiry-edge-case (api-service) | Confidence: low

  [principle]  Treat token lifecycle (issue, validate, rotate, revoke)
               as a state machine, not ad hoc checks
               Source: jwt-expiry-edge-case (api-service) | Confidence: low
```

I read this and feel a small jolt of recognition. The mobile client will reuse connections via a connection pool too. I already burned time on this bug once. I type:

```
> That first principle is directly relevant. Can you use it to review the
> auth design?
```

The assistant draws the connection explicitly: mobile clients pool TCP connections too, and if I initialize the auth headers once at app launch without refreshing them on connection reuse, I'll see the exact same class of bug. It suggests wrapping every request with a token freshness check rather than trusting the pooled connection's existing headers.

We conclude the effort later that day. The summary includes a note: "Design informed by prior knowledge node: validate auth state at connection initialization." The extracted nodes include a new principle that cites the old one as its source.

---

### Scenario 3: Abstraction Layers

A week later I'm working on a completely different project — a data pipeline for processing financial transactions. I launch:

```
oi --project finpipe
```

I'm debugging why certain transaction batches are being partially processed. After an hour of tracing, I find it: the batch processor validates the authorization token at batch submission time, but individual record processors re-use a cached credential that expires mid-batch. Late records fail silently.

```
> Found it. The credential is validated at batch start but not at record
> processing time. Records processed after credential expiry fail silently.
> Fixed by checking credential freshness per record. Done.
```

The effort closes. The knowledge banner appears:

```
  Knowledge nodes extracted:
    [fact]       Batch processors must validate credentials per record,
                 not just at batch submission
    [solution]   Check credential freshness at each processing unit, not
                 at batch envelope
    [principle]  Credentials and auth state decay over time — validate
                 at the point of use, not at the point of receipt

  Connections detected:
    New principle links to: "Validate auth state at connection
    initialization, not at first use" (api-service) — same class of
    problem, different surface

  Abstraction generated:
    Layer 2 (general): "Auth state must be validated where trust is
    consumed, not where the request enters the system"
```

That last line is new. I hadn't seen an abstraction generated before. The system had enough instances — three efforts across two projects, all resolving to the same underlying mistake — to move the idea up a layer.

```
> What does "Layer 2" mean?
```

```
Nodes have abstraction layers:

  Layer 0 (raw):       "batch processor failed because cached credential
                        expired mid-batch in finpipe's transaction processor"
  Layer 1 (contextual): "credentials must be validated per record in batch
                         systems, not just at submission"
  Layer 2 (general):    "validate auth state where trust is consumed, not
                         where the request enters"
  Layer 3 (universal):  Not yet generated — would require broader evidence

Layer 2 is the shareable principle — no project names, no identifying details.
Layer 0 stays private to you. Layer 2 could eventually be shared with a team
or community without exposing anything about your work.
```

I ask what it would take to reach Layer 3.

```
> What would push this to Layer 3?

Independent convergence from a domain outside software — or enough
instances that the principle clearly transcends auth and applies to any
system where a grant is issued at one boundary and consumed at another.
It's not there yet. Three software auth bugs is a strong pattern, but
it's still a software pattern, not a universal one.
```

---

### Scenario 4: The Contradiction

Two months have passed. I've been using `oi` across five projects. The knowledge graph has grown quietly in the background — dozens of nodes, many connected. I've mostly forgotten about it.

I start a new effort on a high-throughput message queue project. The topic: performance optimization. After some profiling, I conclude that validating message signatures on every dequeue is the bottleneck. My recommendation: validate once at ingestion, cache the result, and skip re-validation on dequeue.

```
> Profiling shows signature validation on dequeue is 40% of processing
> time. We should validate at ingestion and cache the result. Done.
```

The effort closes. The summary appears. Then the banner — and something different this time:

```
  Knowledge nodes extracted:
    [decision]   Validate message signatures at ingestion, cache result,
                 skip re-validation at dequeue
    [principle]  For high-throughput pipelines, validate once at trust
                 boundary, not at every consumption point

  Conflict detected:
    New principle: "Validate once at trust boundary, cache result"
    Existing principle: "Validate auth state where trust is consumed,
                         not where it enters" (Confidence: medium)

    These principles contradict each other.

    Classification: Truth conflict — both cannot be correct as stated.
    The system cannot auto-resolve this. Your input is needed.

  [resolve conflict] to address this, or [defer] to continue.
```

I stare at this for a moment. It's right — I argued both sides at different times for different reasons. I type:

```
> resolve conflict
```

```
Conflict: Validate-at-entry vs. Validate-at-consumption

  Principle A (Confidence: medium, 3 supporting nodes across 3 projects):
    "Auth state must be validated where trust is consumed, not where the
    request enters the system"
    Sources: token-cache-bug, jwt-expiry-edge-case, finpipe-credential-expiry

  Principle B (Confidence: low, 1 supporting node, just concluded):
    "For high-throughput pipelines, validate once at trust boundary, cache
    result, skip re-validation at consumption point"
    Sources: msgqueue-perf

  Context on Principle A:
    All three sources involved auth state that *changed* after entry —
    cached credentials that expired, tokens that rotated. The bug in each
    case was that the cached state was stale.

  Context on Principle B:
    Source involves signature validation — a cryptographic property of the
    message itself. A valid signature at ingestion remains valid. The message
    doesn't change.

  Suggested resolution:
    These principles may not actually conflict — they apply to different
    types of auth state.

    A applies to: mutable auth state (tokens, credentials, sessions) that
    can expire or rotate after the request arrives.

    B applies to: immutable verification (signatures, checksums) where
    the property proven at entry remains true throughout.

    A refined principle might be: "Validate mutable auth state at the point
    of consumption. Validate immutable properties once at entry and cache."

  Options:
    1. Accept the refinement above (replaces both with a more precise node)
    2. Keep both as context-dependent (tag A as "mutable state", B as
       "immutable verification")
    3. Write your own resolution
```

Option 1 feels right. I type `1`.

```
  Conflict resolved.

  Superseded:
    "Auth state must be validated where trust is consumed, not where
    it enters" → marked as subsumed by refined principle
    "Validate once at trust boundary, cache result" → same

  New node (principle, Layer 2):
    "Validate mutable auth state at each consumption point. Validate
    immutable properties once at entry and cache the result."

  Confidence: medium (inherits support from both predecessor nodes plus
  the refinement increases specificity)
```

I sit back. The system caught something I would have held as two unrelated conclusions for months without noticing they pointed in different directions. And the resolution is better than either original principle.

---

### Scenario 5: Confidence Accumulates

Six months on. I've concluded well over a hundred efforts across eight projects. I'm starting a new engagement — a security review for a third-party service, which means I'm thinking from first principles about auth architecture.

I launch `oi` and start a new effort:

```
> I'm doing a security review of an external service. I want to know what
> I've learned about auth vulnerabilities from my own projects — the
> patterns I keep seeing.
```

```
> query_knowledge auth vulnerabilities patterns
```

The response prints in a format I haven't seen before — not a flat list, but a structured graph summary:

```
Knowledge graph — topic: "auth vulnerabilities patterns"

  Core principle (Confidence: high, 7 independent sources):
    "Validate mutable auth state at each consumption point. Validate
    immutable properties once at entry and cache the result."

    Supporting nodes (selected):
      [fact] Token cache uninitialized on connection reuse (api-service)
      [fact] Batch credentials expired mid-processing (finpipe)
      [fact] Session token stale after user role change (identity-service)
      [fact] Refresh token not revoked on logout (mobile-api)
      [decision] Signature validation cached at ingestion (msgqueue-perf)
      ... 2 more

    Failed contradictions: 1
      "Validate once at trust boundary" — resolved as complementary,
      not contradictory (see conflict #1)

  Related principles (medium confidence):
    "Treat token lifecycle as a state machine, not ad hoc checks"
    (4 sources, 2 projects)

    "Auth failures should fail loudly — silent auth degradation is
    worse than a hard failure"
    (2 sources, confirmed in mobile-api and finpipe)

  Layer 2 shareable summary:
    Your work across multiple projects converges on a consistent theme:
    auth bugs almost always involve trusting cached state that has since
    changed. The fix is consistently: validate closer to the point of use
    than feels convenient.
```

I read the "Confidence: high, 7 independent sources" line. Six months ago this was a low-confidence principle extracted from a single debugging session. The system didn't ask me to rate it — it watched seven independent efforts arrive at the same place, watched one challenge fail to overturn it, and quietly raised the score.

I use this summary as the backbone of my security review checklist. I copy the Layer 2 shareable summary directly into the review document — no project names, no internal details, just the distilled lesson.

```
> I'm done with the security review. That was useful. Done.
```

```
Effort concluded: security-review

  Summary: Reviewed auth architecture of external service using accumulated
  knowledge graph principles. Key findings mapped to high-confidence node:
  "Validate mutable auth state at consumption point."

  Knowledge nodes extracted:
    [fact]      External service validates session tokens at API gateway
                only — downstream services trust forwarded headers
    [principle] Gateway-only validation is insufficient for multi-tier
                architectures (new node, low confidence — single source)
```

The cycle continues. The new low-confidence node about gateway-only validation will sit quietly until another effort either confirms it or contradicts it. If it's confirmed, its confidence will rise. If it's wrong, a contradiction will surface it for resolution.

The knowledge graph grows. Most of it I'll never look at directly. It's just there — accumulating, connecting, scoring — and surfacing the right things at the right moments.

---

## What I Observed

1. When an effort concludes, a "Knowledge nodes extracted" banner prints beneath the summary, listing typed nodes (fact, solution, principle, decision) pulled from the conversation.
2. Nodes are typed and labeled: the type appears in brackets before the content, and the source effort and project are cited.
3. When beginning a new effort on a related topic, the assistant surfaces relevant knowledge graph nodes with a "show knowledge" invitation rather than inserting them automatically.
4. Querying the knowledge graph with a topic returns structured results — nodes grouped by type, with confidence level and source cited for each.
5. When enough instances of the same principle accumulate across independent efforts, the system generates an abstraction layer — moving a specific conclusion up to a generalized principle, with the layer number shown.
6. Abstraction layers are explained on request: Layer 0 is raw (private), Layer 1 is contextual, Layer 2 is a general principle, Layer 3 is universal. Higher layers strip identifying details.
7. When a new node contradicts an existing node in the graph, a "Conflict detected" banner interrupts the normal conclusion flow and surfaces both nodes side-by-side.
8. Conflict classification is shown explicitly: truth conflict (one side must be wrong) vs. preference conflict (both can coexist with context). Truth conflicts require resolution.
9. The conflict resolution flow presents both nodes with their evidence, suggests a refined resolution when the contradiction turns out to be a precision problem rather than a real disagreement, and offers numbered options.
10. Choosing option 1 (or equivalent) supersedes both predecessor nodes with a refined replacement and inherits their confidence.
11. The `query_knowledge` tool returns a structured graph view: a core principle with its confidence level, the independent sources supporting it, any failed contradictions that attempted to disprove it, and related medium-confidence principles.
12. Confidence levels start at "low" (single source) and rise through "medium" and "high" as independent sources accumulate — without any manual scoring.
13. Failed contradictions are shown in the query result as evidence for the challenged node's confidence — the system counts how many times the node survived challenge.
14. The Layer 2 shareable summary section in query results provides ready-to-copy text that contains no project names or private details.
15. New efforts that conclude with findings adjacent to an existing principle produce a new low-confidence node, which enters the graph to await confirmation or contradiction.

---

## What I Didn't Have To Do

- No manual tagging or categorizing of conclusions — node types (fact, solution, principle, decision) were inferred from the content of the effort
- No explicit linking of related efforts — connections between nodes were detected from content similarity, not declared by the user
- No reviewing old efforts to check for contradictions — the system surfaced the conflict the moment a new node was added that contradicted an existing one
- No manually setting confidence scores — confidence emerged from how many independent sources reached the same conclusion and how many challenges the node survived
- No specifying which layer a principle belongs to — abstraction layers were generated automatically when enough instances existed to support generalization
- No re-explaining context from past projects when starting a new one — relevant nodes surfaced from the graph without being asked
- No remembering to query the graph — the assistant offered relevant nodes proactively when starting a related topic
- No managing privacy manually — Layer 0 details (file paths, project names, company-specific terms) stayed private; Layer 2 principles were automatically stripped of identifying information
- No waiting for a large number of sessions before the graph became useful — even two independent confirmations of a principle were enough to surface a connection
- No manually reviewing which nodes were superseded after conflict resolution — the system updated confidence and marked predecessor nodes as subsumed automatically
- No separate knowledge management tool or workflow — the graph was built as a side effect of normal effort-based work in the existing CLI