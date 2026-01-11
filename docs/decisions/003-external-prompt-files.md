# Decision 003: External Prompt Files

## Context

System prompts for LLM operations (like conclusion extraction) were initially hardcoded in Python.

## Decision

Store all system prompts in external markdown files under `src/oi/prompts/`.

## Reasoning

1. **Iterate without code changes** - Tweak prompts by editing markdown, no Python changes needed
2. **Version control clarity** - Git diff shows exactly how prompts evolved over time
3. **Self-documenting** - Prompt files serve as documentation of system behavior
4. **Testable** - Can A/B test different prompt versions by swapping files

## Structure

```
src/oi/prompts/
├── conclusion_extraction.md
└── (future prompts...)
```

## Implementation

```python
def load_prompt(name: str) -> str:
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text(encoding="utf-8").strip()
```
