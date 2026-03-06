# Knowledge Network — Project Instructions

## Test Environment

Tests MUST be run with the project venv:

```bash
# One-time venv setup (if .venv doesn't exist):
cd /data/Dev/knowledge-network
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,mcp]"

# Run tests (free, no API calls):
.venv/bin/python -m pytest

# Run LLM tests (costs money — ONLY with user approval):
.venv/bin/python -m pytest -m llm

# Run everything:
.venv/bin/python -m pytest -m ""
```

**NEVER run `pytest` or `python -m pytest` directly** — it will use the system Python which is missing litellm and other dependencies, causing false import errors.

## Test Cost Discipline

Tests are split by `@pytest.mark.llm`. The default `pytest` command excludes LLM tests automatically (configured in `pyproject.toml`).

- **`pytest`** — free tests only. Run freely, no API cost. (~10s)
- **`pytest -m llm`** — LLM integration tests. Costs ~$1/run on Cerebras. **Only run with explicit user approval.**
- **`pytest -m ""`** — everything. Same cost rules as LLM tests.

**NEVER run LLM tests without user approval.** When verifying code changes, run `pytest` (free) first. Only run `-m llm` as a final gate when the user says to.

## Test Runner Log (Automatic)

A pytest plugin in `tests/conftest.py` **automatically** records results to `tests/.last_run` after every test run. You never need to manually update this file.

**What happens automatically on every run:**
- Results (passed/failed/skipped/duration) are written to `tests/.last_run`
- A **diff summary** prints at the end of pytest output comparing against the previous run
- Regressions (new failures, new skips) are highlighted in red/yellow
- The file records: git commit + dirty flag, whether e2e tests were included, failed test IDs

**Before making code changes:** read `tests/.last_run` to know the baseline. The plugin will diff against it for you.

**Format of `tests/.last_run`:**
```
passed: NNN
failed: 0
skipped: N
date: YYYY-MM-DD
commit: abc1234 (dirty)
duration: 10.0s
e2e: excluded
command: .venv/bin/python -m pytest
failed_tests: <only present if failed > 0>
```

**If `tests/.last_run` does not exist:** just run the test suite — the plugin will create it automatically.

## Test Discipline — CRITICAL RULES

1. **NEVER normalize test failures.** If tests fail, they are broken. Stop and fix them. Do not rationalize failures as "pre-existing" or "environmental." If you're unsure, check `tests/.last_run` for the baseline — that is the source of truth.

2. **Skip count changes are regressions.** If the baseline says 1 skipped and you see 38 skipped, that is a bug you introduced. Investigate immediately.

3. **Establish baseline before changing code.** If `tests/.last_run` doesn't exist or seems stale, run the test suite on unmodified code FIRST. The plugin will create/update the baseline automatically.

4. **Every phase gets verified.** After each phase of a multi-step change, run the relevant tests. If anything regresses, fix it before moving to the next phase.

5. **Test results are pass/fail — not a spectrum.** The only acceptable result is: same passes, same skips, zero new failures. Anything else means stop and fix.
