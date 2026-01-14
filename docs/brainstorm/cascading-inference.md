# Cascading Inference Architecture

## The Performance Question

**Initial Concern**: Are we making too many LLM calls?

Current flow per turn:
```
User Input
    ↓
build_context() - algorithmic (assembles artifacts from JSON)
    ↓
LLM Call #1 - Main conversation response
    ↓
LLM Call #2 - interpret_exchange() (decides if/what artifact to create)
    ↓
Save artifact, continue
```

**Observation**: 2 LLM calls per turn could seem expensive.

## Key Insight: Token Economics vs Request Count

### The Realization

**Cost is NOT by request count - it's by token usage!**

- Interpretation call is SMALL (~500 tokens)
- But it SAVES thousands of tokens in future turns via compression
- A 12,000 token debugging session → ~400 tokens of linked artifacts
- The system is already cost-efficient through compression!

**The interpretation call is an investment that pays for itself.**

### Current Benefits

1. Interpretation happens AFTER showing user the response (non-blocking UX)
2. Small token cost now
3. Massive token savings later
4. Maintains agentic/intelligent artifact creation

## The Optimization Opportunity

While the economics work, we can still optimize for:
- **Speed**: Reduce latency when interpretation is obvious
- **Cost**: Eliminate unnecessary LLM calls for clear-cut cases
- **User control**: Let users explicitly signal intent

## Proposed Architecture: Cascading Inference

Four levels of inference, escalating only when needed:

```
User Input
    ↓
Level 1: Explicit Commands (confidence = 1.0)
    ↓ (if uncertain)
Level 2: Pattern Matching (confidence 0.7-0.95)
    ↓ (if uncertain)
Level 3: Local LLM (confidence 0.5-0.7)
    ↓ (if uncertain)
Level 4: Remote LLM (current behavior)
    ↓
Create artifact / skip
```

### Level 1: Explicit Commands (Composable Commands)

**User directly signals intent with slash commands:**

```bash
> /effort find best gaming mouse
> /fact what's the capital of France?
> /resolve I'll buy the Logitech G Pro
> /event heading to lunch

# Or inline
> find best gaming mouse /effort
> I'm tired today /event
```

**Characteristics:**
- Confidence: 1.0 (certain)
- Latency: ~0ms (instant)
- Cost: $0 (no LLM call)
- Accuracy: 100% (user explicitly declared)

**Benefits:**
- Power users get instant artifact creation
- No ambiguity, no interpretation needed
- Context builder knows EXACTLY what to do
- Zero inference overhead

### Level 2: Algorithmic Pattern Matching

**High-confidence heuristics for common patterns:**

```python
# Examples
if re.match(r"what('s| is)", text, re.I):
    → fact (confidence: 0.9)

if "find" or "looking for" or "need to" in text:
    → effort (confidence: 0.85)

if "I'll" or "I will" or "going to" + has_open_effort():
    → resolve current effort (confidence: 0.9)

if casual_greeting() or social_noise():
    → event or skip (confidence: 0.8)
```

**Characteristics:**
- Confidence: 0.7-0.95 (high but not certain)
- Latency: ~1ms (regex/pattern match)
- Cost: $0 (no LLM call)
- Accuracy: 85-95% (tunable over time)

**Benefits:**
- Catches 80%+ of common cases
- Instant, free
- Deterministic (no model variance)
- Can be tuned based on telemetry

### Level 3: Local Small Model

**Gemma/Phi/Llama for nuanced cases:**

```python
# Run locally (CPU or GPU)
local_model = load_model("gemma-2b-it")
interpretation = local_model.infer(
    user_msg=user_input,
    assistant_msg=response,
    prompt=interpret_template
)
```

**Characteristics:**
- Confidence: 0.5-0.7 (uncertain, needs intelligence)
- Latency: ~100-500ms (local inference)
- Cost: $0 (runs on user's machine)
- Accuracy: 75-90% (small model trade-off)

**Benefits:**
- Still fast (sub-second)
- Free (no API cost)
- Handles nuanced cases patterns miss
- Privacy-preserving (local inference)

**Challenges:**
- Setup complexity (model download)
- Requires compute resources
- Quality vs main model

### Level 4: Remote LLM (Current Behavior)

**Fall back to remote LLM for truly ambiguous cases:**

- Confidence: <0.5 (very uncertain)
- Latency: ~1-3s (API roundtrip)
- Cost: ~500 tokens (~$0.001 with DeepSeek)
- Accuracy: 95%+ (best model)

**Benefits:**
- Highest quality
- Handles edge cases
- Already implemented

## Implementation Roadmap

### Phase 1: POC - Slash Commands Only
**Goal**: Prove composable commands work

```python
# Parse slash commands
def parse_command(user_input):
    if "/effort" in user_input:
        return Artifact(type="effort", ...)
    elif "/fact" in user_input:
        return Artifact(type="fact", ...)
    elif "/resolve" in user_input:
        return resolve_current_effort(...)
    else:
        return None  # Fall through to remote LLM
```

**Features:**
- Simple string parsing
- Standard slash command syntax (`/effort`, `/fact`, `/resolve`, `/event`)
- Falls back to current remote LLM interpretation if no command
- No pattern matching, no local model yet

**Success Metrics:**
- Commands work correctly
- Users find them natural
- Telemetry shows usage patterns

### Phase 2: Pattern Matching
**Goal**: Reduce remote LLM calls by 60-80%

```python
def pattern_match(user_input, assistant_response):
    confidence, artifact_type = apply_patterns(...)
    if confidence >= 0.7:
        return create_artifact(artifact_type, ...)
    return None  # Escalate
```

**Features:**
- Regex-based pattern detection
- Tunable confidence thresholds
- Telemetry to measure accuracy
- Fallback to remote LLM

### Phase 3: Local Model
**Goal**: Handle nuanced cases without API calls

```python
class LocalInterpreter:
    def __init__(self, model_name="gemma-2b-it"):
        self.model = load_local_model(model_name)

    def infer(self, user_msg, assistant_msg):
        # Local inference with interpret.md prompt
        return self.model.generate(...)
```

**Features:**
- Optional (flag-gated)
- Multiple model options (Gemma, Phi, Llama)
- Confidence scoring
- Graceful fallback if model unavailable

### Phase 4: Telemetry & Tuning
**Goal**: Optimize thresholds based on real usage

```python
# Track which level was used and accuracy
telemetry.log(
    level_used="pattern_match",
    confidence=0.85,
    artifact_created=True,
    user_corrected=False
)

# Periodically tune thresholds
analyze_telemetry() → adjust_confidence_thresholds()
```

## Cascade Decision Logic

```python
class CascadingInference:
    def interpret(self, user_input, assistant_response, state):
        # Level 1: Explicit commands
        if artifact := parse_command(user_input):
            telemetry.log("level_1_command")
            return artifact

        # Level 2: Pattern matching
        confidence, artifact = pattern_match(user_input, assistant_response, state)
        if confidence >= 0.7:
            telemetry.log("level_2_pattern", confidence=confidence)
            return artifact

        # Level 3: Local model (if available)
        if self.local_model:
            confidence, artifact = self.local_model.infer(user_input, assistant_response)
            if confidence >= 0.5:
                telemetry.log("level_3_local", confidence=confidence)
                return artifact

        # Level 4: Remote LLM
        telemetry.log("level_4_remote")
        return remote_llm_interpret(user_input, assistant_response)
```

## Command Syntax Options Considered

| Syntax | Example | Pros | Cons |
|--------|---------|------|------|
| **Slash (chosen)** | `/effort find mouse` | Standard, familiar | Prefix-only |
| Brackets | `find mouse [effort]` | Works anywhere | Less standard |
| @ Symbol | `@effort find mouse` | Clean, mentions-like | Can conflict with usernames |
| Natural | `remember this as fact` | Most natural | Ambiguous, needs parsing |

**Decision**: Start with **slash commands** (standard, familiar from Discord/Slack/CLI).

## Confidence Thresholds

Initial values (to be tuned):

| Level | Min Confidence | Typical Latency | Cost |
|-------|---------------|-----------------|------|
| Command | 1.0 | ~0ms | $0 |
| Pattern | 0.7 | ~1ms | $0 |
| Local | 0.5 | ~200ms | $0 |
| Remote | 0.0 | ~2s | ~$0.001 |

## Success Metrics

**Efficiency:**
- % of turns handled without remote LLM
- Average latency per interpretation
- Cost per 100 turns

**Accuracy:**
- Artifact creation accuracy by level
- User correction rate (did they need to manually fix?)
- False negative rate (missed artifacts)

**Adoption:**
- % of users using slash commands
- Most common commands
- Command usage over time

## Open Questions

### 1. Command Discoverability
- How do users learn about commands?
- Auto-suggest when system detects intent?
- Help text / command palette?

### 2. Command Conflicts
- What if user types `/effort` in natural text?
- Escape sequence for literal slash?
- Only parse commands at start of message?

### 3. Partial Commands
- Allow `/e` for `/effort`?
- Tab completion?
- Fuzzy matching?

### 4. State-Aware Commands
- `/resolve` - should auto-resolve most recent open effort?
- `/continue` - reopen last resolved effort?
- `/tag debugging` - tag current or last artifact?

### 5. Confidence Calibration
- How to measure real accuracy?
- User feedback mechanism?
- A/B testing thresholds?

### 6. Local Model Selection
- Which model is best trade-off? (Gemma 2B vs Phi-2 vs Llama 3B)
- Quantization? (4-bit vs 8-bit vs full)
- CPU vs GPU? (accessibility vs speed)

## Related Work

- **Command-based systems**: Slack, Discord, IRC bots
- **Intent classification**: Rasa, DialogFlow, LLM function calling
- **Cascading inference**: LLM routing, model cascades in production
- **Local-first AI**: Ollama, LM Studio, GPT4All

## Next Steps

1. **Implement Phase 1 (POC)**:
   - Add command parsing to `interpret.py`
   - Support `/effort`, `/fact`, `/resolve`, `/event`
   - Wire into `conversation.py`

2. **Document in slice**:
   - Create slice spec for cascading inference
   - User stories for command usage
   - Scenarios for each level

3. **Prototype pattern matching**:
   - Research common patterns in test scenarios
   - Build pattern library
   - Measure baseline accuracy

4. **Research local models**:
   - Benchmark Gemma 2B, Phi-2, Llama 3B
   - Test interpretation quality
   - Measure latency on various hardware

## Key Insights

> **The system already optimizes for token economics through compression.**
> The interpretation call is a small investment that pays massive dividends.

> **Composable commands give users direct control over the knowledge network.**
> Explicit intent eliminates ambiguity and interpretation overhead entirely.

> **Cascading inference optimizes for the common case.**
> Most interpretations are obvious - save the intelligence for when it's needed.

> **Four levels balance speed, cost, accuracy, and user control.**
> Each level handles what it's best at, escalating only when uncertain.

---

*Brainstormed: 2026-01-13*
*Status: Phase 1 (POC) - Slash commands only*
*Next: Implement command parsing, then document in slice spec*
