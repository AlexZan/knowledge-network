"""Tests for Story 3: Capture Messages Within an Open Effort"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestStory3CaptureMessagesWithinOpenEffort:
    """Story 3: Capture Messages Within an Open Effort"""

    def test_user_message_saved_to_open_effort_log(self, tmp_path):
        """When I send a message while an effort is open, it is saved to that effort's raw log"""
        # Arrange
        from oi.effort_log import save_message_to_effort_log  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        effort_log = efforts_dir / "auth-bug.jsonl"
        
        # Act
        save_message_to_effort_log(session_dir, "auth-bug", "user", "Let's debug the auth bug - users are getting 401s after about an hour")
        
        # Assert
        with open(effort_log) as f:
            lines = f.readlines()
        saved = json.loads(lines[0])
        assert saved["role"] == "user"
        assert "auth bug" in saved["content"].lower()
        assert saved["content"] == "Let's debug the auth bug - users are getting 401s after about an hour"

    def test_assistant_response_saved_to_same_effort_log(self, tmp_path):
        """The assistant's response is also saved to the same effort's raw log"""
        # Arrange
        from oi.effort_log import save_message_to_effort_log  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        effort_log = efforts_dir / "auth-bug.jsonl"
        
        # Act - save user message
        save_message_to_effort_log(session_dir, "auth-bug", "user", "Let's debug the auth bug")
        # Act - save assistant response
        save_message_to_effort_log(session_dir, "auth-bug", "assistant", "Opening effort: auth-bug. That timing suggests token expiration.")
        
        # Assert
        with open(effort_log) as f:
            lines = f.readlines()
        assert len(lines) == 2
        user_msg = json.loads(lines[0])
        assistant_msg = json.loads(lines[1])
        assert user_msg["role"] == "user"
        assert assistant_msg["role"] == "assistant"
        assert "opening effort" in assistant_msg["content"].lower()

    def test_open_effort_log_included_in_context_for_next_turn(self, tmp_path):
        """The entire raw log of an open effort is included in the context for the next turn"""
        # Arrange
        from oi.context import build_turn_context  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        # Create effort log with multiple messages
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n" +
            json.dumps({"role": "user", "content": "Access token is 1 hour, yes we have refresh tokens"}) + "\n"
        )
        
        # Create manifest with open effort
        manifest = session_dir / "manifest.yaml"
        manifest.write_text("""
efforts:
  - id: auth-bug
    status: open
    summary: Debugging 401 errors
""")
        
        # Create state with open effort artifact
        from oi.models import Artifact, ConversationState
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Debugging 401 errors", status="open")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert - all messages from effort log should be in context
        assert "Let's debug the auth bug" in context
        assert "Opening effort: auth-bug" in context
        assert "Access token is 1 hour" in context
        assert "refreshtokens" in context.replace(" ", "").replace("-", "").lower()