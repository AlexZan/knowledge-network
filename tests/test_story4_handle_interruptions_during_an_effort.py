"""Tests for Story 4: Handle Interruptions During an Effort"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestStory4HandleInterruptionsDuringAnEffort:
    """Story 4: Handle Interruptions During an Effort"""

    def test_interruption_question_gets_response_when_effort_open(self):
        """AC1: When I ask an unrelated question while an effort is open, the assistant responds to my question."""
        # Arrange
        from oi.models import ConversationState, Artifact
        from oi.routing import route_message
        
        # Create state with open effort
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug", status="open")
        ])
        
        # Unrelated message
        message = "Quick question - what's the weather in Seattle?"
        
        # Act - routing should detect this as ambient (not related to open effort)
        target = route_message(state, message)
        
        # Assert - message should be routed to ambient
        assert target == "ambient"
        # Note: The actual assistant response generation happens elsewhere (LLM).
        # This test verifies the routing decision only.
        # The assistant responding is implied by the target being ambient and the system
        # processing ambient messages normally.

    def test_interruption_saved_to_ambient_log_not_effort_log(self, tmp_path):
        """AC2: The interruption question and response are saved to the ambient raw log, not the effort log."""
        # Arrange
        from oi.chatlog import save_ambient_exchange
        
        raw_log = tmp_path / "raw.jsonl"
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        
        # Create existing effort log to ensure it's not modified
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(json.dumps({"role": "user", "content": "debug auth"}) + "\n")
        
        # Act - save interruption exchange to ambient log
        save_ambient_exchange("user", "What's the weather?", raw_log)
        save_ambient_exchange("assistant", "72°F and sunny.", raw_log)
        
        # Assert - ambient log contains the interruption
        with open(raw_log) as f:
            lines = f.read().strip().split("\n")
        
        assert len(lines) == 2
        user_msg = json.loads(lines[0])
        assistant_msg = json.loads(lines[1])
        
        assert user_msg["role"] == "user"
        assert "weather" in user_msg["content"].lower()
        assert assistant_msg["role"] == "assistant"
        assert "sunny" in assistant_msg["content"].lower()
        
        # Assert - effort log was NOT modified (still has only the original line)
        with open(effort_log) as f:
            effort_lines = f.read().strip().split("\n")
        
        assert len(effort_lines) == 1
        assert "debug auth" in effort_lines[0]
        assert "weather" not in effort_lines[0]

    def test_open_effort_remains_available_after_interruption(self, tmp_path):
        """AC3: The open effort remains open and its context is still available after the interruption."""
        # Arrange
        from oi.models import ConversationState, Artifact
        from oi.context import build_turn_context
        
        # Create session structure with open effort
        session_dir = tmp_path
        
        # Create raw.jsonl with ambient content
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text("")
        
        # Create effort log with existing conversation
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "debug auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n"
        )
        
        # Create manifest with open effort
        manifest = session_dir / "manifest.yaml"
        manifest.write_text("""efforts:
  - id: auth-bug
    status: open
    summary: Auth bug investigation
    created: 2023-10-01T12:00:00
    updated: 2023-10-01T12:00:00
""")
        
        # Create state with open effort
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug investigation", status="open")
        ])
        
        # Add interruption to ambient log
        with open(raw_log, "a") as f:
            f.write(json.dumps({"role": "user", "content": "Quick weather question"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Sunny day"}) + "\n")
        
        # Act - build context after interruption
        context = build_turn_context(state, session_dir)
        
        # Assert - context still includes effort content (effort is still open and in context)
        assert "auth-bug" in context
        assert "debug auth bug" in context
        # Also includes ambient interruption
        assert "weather" in context.lower() or "sunny" in context.lower()