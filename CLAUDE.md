# Knowledge Network — Project Instructions

## Test Environment

Tests MUST be run with the project venv:

```bash
# One-time venv setup (if .venv doesn't exist):
cd /data/Dev/knowledge-network
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,mcp]"

# Run unit tests (fast, no external calls):
.venv/bin/python -m pytest

# Run integration tests (uses Ollama — free but slow):
.venv/bin/python -m pytest -m integration

# Run LLM tests (costs money — ONLY with user approval):
.venv/bin/python -m pytest -m llm

# Run everything:
.venv/bin/python -m pytest -m ""
```

**NEVER run `pytest` or `python -m pytest` directly** — it will use the system Python which is missing litellm and other dependencies, causing false import errors.

## Test Tiers

Tests are split into three tiers by marker. The default `pytest` command runs only unit tests (configured in `pyproject.toml`).

| Tier | Marker | What it tests | Speed | Cost | When to run |
|------|--------|---------------|-------|------|-------------|
| **unit** | (default) | Pure logic, all I/O mocked | <10s | Free | Every change, freely |
| **integration** | `@pytest.mark.integration` | Local services (Ollama) | ~30s+ | Free | Before commits, major changes |
| **llm** | `@pytest.mark.llm` | Remote APIs (Cerebras) | ~60s | ~$1/run | Final gate, explicit approval only |

- **`pytest`** — unit tests only. Fast, no external calls. Run freely.
- **`pytest -m integration`** — Ollama integration tests. Free but needs Ollama running.
- **`pytest -m llm`** — remote LLM tests. **Only run with explicit user approval.**
- **`pytest -m ""`** — everything. Same cost/approval rules as LLM tests.

**NEVER run LLM tests without user approval.** When verifying code changes, run `pytest` (unit) first. Only run `-m llm` as a final gate when the user says to.

## Ollama (Local Embeddings)

Ollama is **not running by default** — it's disabled as a system service to avoid loading nvidia modules and wasting power.

```bash
# Start ollama before embedding/integration work:
sudo systemctl start ollama

# Stop when done:
sudo systemctl stop ollama
```

- Ollama runs on **CPU by default** (GPU is off). This is fine for embeddings.
- For large batch jobs needing GPU: run `gpu-on --force` before starting ollama.
- Models auto-unload after 30s of inactivity (`OLLAMA_KEEP_ALIVE=30s`).
- **Always stop ollama when done** — don't leave it running.

## Unit Test Isolation — CRITICAL

**Unit tests must NEVER make external calls** — no Ollama, no LLM APIs, no HTTP requests.

The main leak vector is `add_knowledge()`, which by default calls:
- `embed_node()` → Ollama HTTP API (embedding)
- `run_linking()` → `chat()` → LLM API (linking classification)

**Prevention patterns (use one per test file):**
1. **Autouse fixture** (preferred for test files that call `add_knowledge` often):
   ```python
   @pytest.fixture(autouse=True)
   def _no_external_calls():
       with patch("oi.embed.get_embedding", return_value=None), \
            patch("oi.linker.chat", return_value='{"edge_type": "none", "reasoning": "mocked"}'):
           yield
   ```
2. **Skip flags** (for occasional calls):
   ```python
   add_knowledge(session_dir, "fact", "...", skip_embed=True, skip_linking=True)
   ```

**If you add a test that calls `add_knowledge()`, you MUST use one of these patterns.** If the test suite takes >15s, something is leaking external calls — investigate immediately.

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
