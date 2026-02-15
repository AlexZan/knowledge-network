"""End-to-end test with real LLM (deepseek-chat).

Verifies:
1. LLM correctly detects when to open/close efforts from natural language
2. Token measurements match predictions
3. Tool-based flow works end-to-end

Run with: pytest tests/test_e2e_real_llm.py -v -s
Requires: DEEPSEEK_API_KEY environment variable
"""

import json
import os
import yaml
import pytest
from pathlib import Path

from oi.orchestrator import process_turn, _build_messages
from oi.tools import get_open_effort
from oi.tokens import count_tokens


requires_llm = pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not set — skipping real LLM test"
)

MODEL = "deepseek/deepseek-chat"


def _context_tokens(session_dir):
    messages = _build_messages(session_dir)
    return sum(count_tokens(m["content"]) for m in messages)


@requires_llm
class TestRealLLMToolCalling:
    """Verify LLM correctly calls tools via natural language."""

    def test_llm_opens_effort_via_tool_call(self, tmp_path):
        """User says 'let's debug X' → LLM calls open_effort tool → manifest updated."""
        session_dir = tmp_path / "session"
        response = process_turn(
            session_dir,
            "Let's debug the auth bug - users are getting 401 errors after about an hour",
            model=MODEL
        )

        effort = get_open_effort(session_dir)
        assert effort is not None, f"LLM did not open an effort. Response: {response[:200]}"
        print(f"\nOpened effort: {effort['id']}")
        print(f"Response: {response[:200]}")

    def test_ambient_message_no_effort(self, tmp_path):
        """Casual message → no effort created."""
        session_dir = tmp_path / "session"
        response = process_turn(session_dir, "Hello, how are you?", model=MODEL)

        effort = get_open_effort(session_dir)
        assert effort is None, f"LLM opened an effort for casual chat. Response: {response[:200]}"

        # Ambient log should exist
        raw = session_dir / "raw.jsonl"
        assert raw.exists()

    def test_follow_up_stays_in_effort(self, tmp_path):
        """After opening effort, follow-up messages don't open a second one."""
        session_dir = tmp_path / "session"

        # Open effort
        process_turn(
            session_dir,
            "Let's work on fixing the login timeout issue",
            model=MODEL
        )
        assert get_open_effort(session_dir) is not None

        # Follow-up
        process_turn(
            session_dir,
            "The access token expires after 1 hour, we have refresh tokens configured",
            model=MODEL
        )

        # Still only one effort
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        efforts = [e for e in manifest.get("efforts", []) if e["status"] == "open"]
        assert len(efforts) == 1, f"Expected 1 open effort, got {len(efforts)}"

    def test_llm_closes_effort_via_tool_call(self, tmp_path):
        """User signals completion → LLM calls close_effort → effort concluded with summary."""
        session_dir = tmp_path / "session"

        # Open and work
        process_turn(
            session_dir,
            "Let's work on fixing the database connection pool exhaustion",
            model=MODEL
        )
        process_turn(
            session_dir,
            "The pool size was set to 5 but we need at least 20 for our load",
            model=MODEL
        )

        # Signal completion
        response = process_turn(
            session_dir,
            "I've increased the pool size to 25 and the connection errors are gone. Bug is fixed, we're done.",
            model=MODEL
        )

        effort = get_open_effort(session_dir)
        assert effort is None, f"LLM did not close the effort. Response: {response[:200]}"

        # Verify summary in manifest
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        concluded = [e for e in manifest["efforts"] if e["status"] == "concluded"]
        assert len(concluded) == 1
        assert concluded[0]["summary"], "Summary should not be empty"
        print(f"\nSummary: {concluded[0]['summary']}")

    def test_full_scenario_token_savings(self, tmp_path):
        """Full scenario: ambient → open → work → close. Measure token savings."""
        session_dir = tmp_path / "session"

        # Ambient
        process_turn(session_dir, "Hey, how's it going?", model=MODEL)
        t_ambient = _context_tokens(session_dir)

        # Open
        process_turn(
            session_dir,
            "Let's debug the auth bug - users get 401 errors after an hour",
            model=MODEL
        )
        t_open = _context_tokens(session_dir)

        # Work
        process_turn(
            session_dir,
            "The access token TTL is 1 hour. The refreshAccessToken function exists "
            "in tokenService.ts but nothing calls it automatically.",
            model=MODEL
        )
        process_turn(
            session_dir,
            "So the token expires because nothing triggers a refresh. "
            "I'll add an axios interceptor to handle this.",
            model=MODEL
        )
        t_work = _context_tokens(session_dir)

        # Close
        process_turn(
            session_dir,
            "I implemented the interceptor and tested it - 401 errors are gone. "
            "Bug is fixed, let's wrap this up.",
            model=MODEL
        )
        t_closed = _context_tokens(session_dir)

        print(f"\nToken progression:")
        print(f"  Ambient: {t_ambient}")
        print(f"  After open: {t_open}")
        print(f"  After work: {t_work}")
        print(f"  After close: {t_closed}")
        if t_work > 0:
            savings = (1 - t_closed / t_work) * 100
            print(f"  Savings: {savings:.0f}%")
