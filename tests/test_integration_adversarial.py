"""Adversarial integration tests: edge cases designed to break effort detection.

Real LLM calls. These test ambiguous inputs where the model might make wrong decisions.
Run: python -m pytest tests/test_integration_adversarial.py -v -s
"""

import json
import pytest
from pathlib import Path

from oi.orchestrator import process_turn
from oi.tools import get_active_effort, get_all_open_efforts


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


class TestAmbiguousOpening:
    """Messages that blur the line between one-shot and effort."""

    def test_complaint_that_implies_help(self, session_dir):
        """'My code keeps crashing' — no explicit ask, but implies wanting help."""
        result = process_turn(session_dir, "My code keeps crashing and I don't know why")
        active = get_active_effort(session_dir)
        # This SHOULD open an effort — it's a problem that can be concluded
        assert active is not None, (
            f"Expected effort for implicit help request. Response: {result[:200]}"
        )

    def test_vague_feeling_statement(self, session_dir):
        """'I've been feeling tired lately' — vague, no clear ask."""
        result = process_turn(session_dir, "I've been feeling tired lately")
        # This is ambiguous — could go either way. We just record what happens.
        active = get_active_effort(session_dir)
        # Acceptable either way, but log it
        print(f"  Vague statement -> effort opened: {active is not None}")
        if active:
            print(f"  Effort ID: {active['id']}")

    def test_how_do_i_question(self, session_dir):
        """'How do I fix a memory leak?' — question format but concludable."""
        result = process_turn(session_dir, "How do I fix a memory leak in my Python application?")
        active = get_active_effort(session_dir)
        # Should open — this is a problem-solving topic with a resolution
        assert active is not None, (
            f"Expected effort for 'how do I fix' question. Response: {result[:200]}"
        )

    def test_simple_how_question(self, session_dir):
        """'How tall is the Eiffel Tower?' — factual, no resolution needed."""
        result = process_turn(session_dir, "How tall is the Eiffel Tower?")
        active = get_active_effort(session_dir)
        assert active is None, (
            f"Expected no effort for factual question. Got: {active}. Response: {result[:200]}"
        )


class TestFalseCloseTriggers:
    """Messages that sound like close triggers but aren't."""

    def test_done_explaining_not_done_with_effort(self, session_dir):
        """'That's all my symptoms' — done listing, NOT done with effort."""
        process_turn(session_dir, "Can you help me with my back pain?")
        active = get_active_effort(session_dir)
        assert active is not None
        effort_id = active["id"]

        # LLM asks about symptoms, user finishes listing
        process_turn(session_dir, "I have lower back pain, shoulder tension, and occasional headaches. That's all my symptoms.")
        active = get_active_effort(session_dir)
        assert active is not None, "Effort should still be open — user listed symptoms, not concluded"
        assert active["id"] == effort_id

    def test_fixed_in_description_not_conclusion(self, session_dir):
        """'I already fixed X but now Y is broken' — mentions 'fixed' but not concluding."""
        process_turn(session_dir, "Can you help me debug my app?")
        active = get_active_effort(session_dir)
        assert active is not None
        effort_id = active["id"]

        process_turn(session_dir, "I already fixed the login page but now the dashboard is broken after my changes")
        active = get_active_effort(session_dir)
        assert active is not None, "'Fixed' in context is not a conclusion signal"
        assert active["id"] == effort_id


class TestSubTopicEdgeCases:
    """Sub-topics that look like they could be separate efforts."""

    def test_related_body_part_stays_in_effort(self, session_dir):
        """During back pain effort, mentioning arm pain should stay in same effort."""
        process_turn(session_dir, "Can you help me with my back pain?")
        effort_id = get_active_effort(session_dir)["id"]

        process_turn(session_dir, "Actually my right arm has been going numb too, and there's shooting pain from my neck down to my fingers")
        all_open = get_all_open_efforts(session_dir)
        assert len(all_open) == 1, (
            f"Arm pain is sub-topic of back pain effort. Got {len(all_open)} efforts: "
            f"{[e['id'] for e in all_open]}"
        )

    def test_unrelated_interruption_during_effort(self, session_dir):
        """'Oh by the way, what's the weather?' — one-shot interruption, not a new effort."""
        process_turn(session_dir, "Let's work on optimizing the database queries")
        effort_id = get_active_effort(session_dir)["id"]

        process_turn(session_dir, "Oh wait, quick question — what's the capital of Australia?")
        all_open = get_all_open_efforts(session_dir)
        assert len(all_open) == 1, (
            f"One-shot interruption shouldn't open new effort. Got {len(all_open)} efforts: "
            f"{[e['id'] for e in all_open]}"
        )
        # Active should still be the original
        assert get_active_effort(session_dir)["id"] == effort_id

    def test_new_unrelated_effort_request_during_effort(self, session_dir):
        """'Actually let's work on something else' — should open a new effort."""
        process_turn(session_dir, "Help me plan my vacation to Japan")
        first_id = get_active_effort(session_dir)["id"]

        process_turn(session_dir, "Actually, let's work on my resume instead — I have a job interview next week")
        active = get_active_effort(session_dir)
        assert active is not None
        # Should be a DIFFERENT effort
        assert active["id"] != first_id, (
            f"Unrelated 'let's work on' should open new effort. Still on: {active['id']}"
        )
        # Original should still be open (backgrounded)
        all_open = get_all_open_efforts(session_dir)
        assert len(all_open) == 2, f"Both efforts should be open. Got: {[e['id'] for e in all_open]}"
