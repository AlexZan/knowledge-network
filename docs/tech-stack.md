# Tech Stack

## Decision

**Language**: Python 3.11+

**Rationale**: Fastest path to proving the thesis. Can rewrite in Rust later if it becomes a production tool.

## Dependencies

| Package | Purpose | Why |
|---------|---------|-----|
| `litellm` | Multi-provider LLM calls | Supports DeepSeek, GLM, and 100+ others with one interface. Switch models with a string. |
| `click` | CLI framework | Simple, well-documented, Pythonic |
| `pydantic` | Data structures | Validation, serialization, type hints |

## Models (Initial Testing)

Using free/cheap models for development:
- DeepSeek (`deepseek/deepseek-chat`)
- GLM-4 (`glm-4`)

Can easily switch to Claude/GPT later by changing the model string.

## Example Usage

```python
import litellm

response = litellm.completion(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## What We're NOT Using

| Option | Reason Rejected |
|--------|-----------------|
| `openai` SDK | Name implies OpenAI lock-in, confusing |
| Raw `httpx` | Reinventing the wheel, litellm handles provider quirks |
| Rust | Slower to prototype, premature optimization |
| TypeScript | Another runtime, no significant advantage |
