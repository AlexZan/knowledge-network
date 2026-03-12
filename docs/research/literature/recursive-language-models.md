# Recursive Language Models (RLMs)

**Paper**: [arXiv:2512.24601](https://arxiv.org/abs/2512.24601)
**Authors**: Alex L. Zhang, Tim Kraska, Omar Khattab
**Date**: December 2025

## Summary

RLMs enable LLMs to process inputs up to 100x longer than their context window through recursive decomposition. The model receives symbolic handles to prompts (not full content) and can programmatically examine, decompose, and recursively call itself over snippets.

Key results:
- RLM(GPT-5) achieves 28% improvement on long-context tasks
- Scales to 10M+ tokens
- RLM-Qwen3-8B (small native model) approaches GPT-5 performance

## Relationship to This Project

**Orthogonal, not competing.** RLMs and our thesis solve different problems:

| | RLMs | Knowledge Network |
|---|------|-------------------|
| Problem | Process long inputs | Accumulate knowledge |
| Scope | Single inference | Across sessions |
| Output | Answer | Growing graph |

## Potential Integration

RLMs could serve as the **processing layer** for the knowledge network:

```
Long conversation history
         │
         ▼
      [RLMs]  ← Handle massive context
         │
         ▼
  Conclusion extraction
         │
         ▼
  [Knowledge Network]  ← Persist & connect
```

The "symbolic handles + metadata" approach validates our "conclusion + link" architecture - both maintain access to full content while working with compressed representations.

## Future Work

- Explore RLM-style decomposition for processing large knowledge graphs
- Consider RLMs for querying across many historical sessions
- Evaluate whether RLM training approach applies to conclusion extraction

## References

- Full paper: https://arxiv.org/abs/2512.24601
- Code: Available on GitHub (see paper)
