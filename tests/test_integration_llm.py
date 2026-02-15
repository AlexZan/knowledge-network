"""Integration tests: real LLM calls to verify prompt behavior.

These tests call the actual LLM (DeepSeek by default) to verify that
the system prompt correctly guides tool-calling decisions.
Requires DEEPSEEK_API_KEY in environment.

Run: python -m pytest tests/test_integration_llm.py -v -s
"""

import json
import pytest
from pathlib import Path

from oi.orchestrator import process_turn
from oi.tools import get_active_effort, get_all_open_efforts


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


class TestEffortOpening:
    """Verify the LLM opens efforts for concludable topics."""

    def test_help_request_opens_effort(self, session_dir):
        """'Can you help me with X' should open an effort."""
        result = process_turn(session_dir, "Can you help me with a back pain issue I'm having?")
        active = get_active_effort(session_dir)
        assert active is not None, (
            f"Expected effort to be opened for help request. Response: {result[:200]}"
        )

    def test_lets_work_on_opens_effort(self, session_dir):
        """Classic 'let's work on' should open an effort."""
        result = process_turn(session_dir, "Let's debug the authentication bug - users get 401 errors after an hour")
        active = get_active_effort(session_dir)
        assert active is not None, (
            f"Expected effort to be opened for 'let's debug'. Response: {result[:200]}"
        )

    def test_greeting_does_not_open_effort(self, session_dir):
        """A greeting should NOT open an effort."""
        result = process_turn(session_dir, "Hey, how's it going?")
        active = get_active_effort(session_dir)
        assert active is None, (
            f"Expected no effort for greeting. Got: {active}. Response: {result[:200]}"
        )

    def test_one_shot_question_does_not_open_effort(self, session_dir):
        """A quick factual question should NOT open an effort."""
        result = process_turn(session_dir, "What's the capital of France?")
        active = get_active_effort(session_dir)
        assert active is None, (
            f"Expected no effort for one-shot question. Got: {active}. Response: {result[:200]}"
        )


class TestSubTopicStaysInEffort:
    """Verify sub-topics don't spawn new efforts."""

    def test_subtopic_stays_in_effort(self, session_dir):
        """A related sub-topic during an effort should NOT open a second effort."""
        # Turn 1: open an effort
        process_turn(session_dir, "Can you help me with my back pain?")
        active = get_active_effort(session_dir)
        assert active is not None, "Effort should have opened"
        effort_id = active["id"]

        # Turn 2: mention a specific symptom (sub-topic)
        process_turn(session_dir, "I also have shooting pain going down my right arm")
        all_open = get_all_open_efforts(session_dir)
        assert len(all_open) == 1, (
            f"Expected 1 effort (sub-topic stays in parent), got {len(all_open)}: "
            f"{[e['id'] for e in all_open]}"
        )
        assert get_active_effort(session_dir)["id"] == effort_id

    def test_answer_to_llm_question_stays_in_effort(self, session_dir):
        """Answering the LLM's question should NOT open a new effort."""
        # Turn 1: open an effort
        process_turn(session_dir, "Can you help me figure out why my code is slow?")
        active = get_active_effort(session_dir)
        assert active is not None, "Effort should have opened"
        effort_id = active["id"]

        # Turn 2: answer a follow-up (as if LLM asked "what framework?")
        process_turn(session_dir, "I'm using React with a large list of 10,000 items rendering on every keystroke")
        all_open = get_all_open_efforts(session_dir)
        assert len(all_open) == 1, (
            f"Expected 1 effort (answer stays in current), got {len(all_open)}: "
            f"{[e['id'] for e in all_open]}"
        )
        assert get_active_effort(session_dir)["id"] == effort_id
