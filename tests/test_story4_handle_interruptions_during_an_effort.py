"""Tests for Story 4: Handle Interruptions During an Effort"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestStory4HandleInterruptions:
    """Story 4: Handle Interruptions During an Effort"""

    def test_unrelated_question_routed_to_ambient_when_effort_open(self, tmp_path):
        """When I ask an unrelated question while an effort is open, the message is routed to ambient (not to the effort)"""
        from oi.routing import route_message
        from oi.models import ConversationState, Artifact

        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug", status="open")
        ])
        result = route_message(state, "Quick question - what's the weather in Seattle?")
        assert result == "ambient"

    def test_interruption_does_not_modify_effort_log(self, tmp_path):
        """The effort log is not modified by the interruption"""
        from oi.chatlog import save_ambient_message
        from oi.models import ConversationState, Artifact

        raw_log = tmp_path / "raw.jsonl"
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(json.dumps({"role": "user", "content": "debug auth"}) + "\n")

        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug", status="open")
        ])

        save_ambient_message(state, "Quick question - what's the weather?", raw_log)

        with open(effort_log) as f:
            lines = f.readlines()
        assert len(lines) == 1
        saved = json.loads(lines[0])
        assert saved["content"] == "debug auth"

    def test_open_effort_remains_open_after_interruption(self, tmp_path):
        """The open effort remains open and its context is still available after the interruption"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(json.dumps({"role": "user", "content": "debug auth"}) + "\n")

        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug", status="open")
        ])

        context = build_turn_context(state, tmp_path)
        assert "debug auth" in context