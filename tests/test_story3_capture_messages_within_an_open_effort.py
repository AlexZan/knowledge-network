"""Tests for Story 3: Capture Messages Within an Open Effort"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime


class TestStory3CaptureMessagesWithinOpenEffort:
    """Story 3: Capture Messages Within an Open Effort"""

    def test_user_message_saved_to_open_effort_log(self, tmp_path):
        """When I send a message while an effort is open, it is saved to that effort's raw log (efforts/X.jsonl)"""
        from oi.storage import save_to_effort_log  # Will fail - doesn't exist yet
        effort_id = "auth-bug"
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        effort_file = efforts_dir / f"{effort_id}.jsonl"
        
        # Act
        save_to_effort_log(effort_id, session_dir, "user", "Let's check the refresh token logic")
        
        # Assert
        assert effort_file.exists()
        with open(effort_file) as f:
            lines = f.readlines()
        assert len(lines) == 1
        saved = json.loads(lines[0])
        assert saved["role"] == "user"
        assert saved["content"] == "Let's check the refresh token logic"
        assert "timestamp" in saved

    def test_assistant_response_saved_to_same_effort_log(self, tmp_path):
        """The assistant's response is also saved to the same effort's raw log"""
        from oi.storage import save_to_effort_log  # Will fail - doesn't exist yet
        effort_id = "auth-bug"
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        effort_file = efforts_dir / f"{effort_id}.jsonl"
        
        # Add a user message first
        with open(effort_file, "a") as f:
            f.write(json.dumps({"role": "user", "content": "test", "timestamp": "2024-01-01T00:00:00"}) + "\n")
        
        # Act
        save_to_effort_log(effort_id, session_dir, "assistant", "The refresh token should be called automatically")
        
        # Assert
        with open(effort_file) as f:
            lines = f.readlines()
        assert len(lines) == 2
        saved = json.loads(lines[1])
        assert saved["role"] == "assistant"
        assert saved["content"] == "The refresh token should be called automatically"
        assert "timestamp" in saved

    def test_open_effort_raw_log_included_in_context(self, tmp_path):
        """The entire raw log of an open effort is included in the context for the next turn"""
        from oi.context import build_turn_context  # Will fail - doesn't exist yet
        from oi.models import ConversationState, Artifact
        
        # Arrange: Create an open effort artifact and its raw log
        effort_id = "auth-bug"
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        effort_file = efforts_dir / f"{effort_id}.jsonl"
        
        # Write multiple messages to the effort log
        messages = [
            {"role": "user", "content": "Let's debug the auth bug", "timestamp": "2024-01-01T00:00:00"},
            {"role": "assistant", "content": "Opening effort: auth-bug", "timestamp": "2024-01-01T00:00:01"},
            {"role": "user", "content": "The token expires after 1 hour", "timestamp": "2024-01-01T00:00:02"},
            {"role": "assistant", "content": "That suggests refresh token issue", "timestamp": "2024-01-01T00:00:03"}
        ]
        with open(effort_file, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")
        
        # Create state with open effort
        state = ConversationState(artifacts=[
            Artifact(id=effort_id, artifact_type="effort", summary="Auth bug", status="open")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert: All messages from the effort log should appear in context
        assert "Let's debug the auth bug" in context
        assert "Opening effort: auth-bug" in context
        assert "The token expires after 1 hour" in context
        assert "That suggests refresh token issue" in context

    def test_multiple_messages_appended_to_effort_log(self, tmp_path):
        """Multiple messages in sequence are appended to the same effort log file"""
        from oi.storage import save_to_effort_log  # Will fail - doesn't exist yet
        effort_id = "auth-bug"
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        effort_file = efforts_dir / f"{effort_id}.jsonl"
        
        # Act: Save multiple messages
        save_to_effort_log(effort_id, session_dir, "user", "First message")
        save_to_effort_log(effort_id, session_dir, "assistant", "First response")
        save_to_effort_log(effort_id, session_dir, "user", "Follow-up question")
        
        # Assert
        with open(effort_file) as f:
            lines = f.readlines()
        assert len(lines) == 3
        
        messages = [json.loads(line) for line in lines]
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "First message"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "First response"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "Follow-up question"

    def test_effort_log_created_if_not_exists(self, tmp_path):
        """Effort log file is created if it doesn't exist when saving first message"""
        from oi.storage import save_to_effort_log  # Will fail - doesn't exist yet
        effort_id = "new-effort"
        session_dir = tmp_path / "session"
        
        # Act
        save_to_effort_log(effort_id, session_dir, "user", "Starting new effort")
        
        # Assert
        effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"
        assert effort_file.exists()
        assert effort_file.parent.exists()  # efforts directory created
        
        with open(effort_file) as f:
            saved = json.loads(f.read())
        assert saved["role"] == "user"
        assert saved["content"] == "Starting new effort"

    def test_only_open_efforts_included_in_context(self, tmp_path):
        """Only open efforts' raw logs are included in context, not concluded ones"""
        from oi.context import build_turn_context  # Will fail - doesn't exist yet
        from oi.models import ConversationState, Artifact
        
        # Arrange: Create two efforts - one open, one concluded
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        # Open effort log
        open_effort_file = efforts_dir / "open-effort.jsonl"
        open_effort_file.write_text(json.dumps({"role": "user", "content": "Working on open task", "timestamp": "2024-01-01T00:00:00"}) + "\n")
        
        # Concluded effort log (should NOT be in context)
        concluded_effort_file = efforts_dir / "concluded-effort.jsonl"
        concluded_effort_file.write_text(json.dumps({"role": "user", "content": "Old concluded task", "timestamp": "2024-01-01T00:00:00"}) + "\n")
        
        # Create state with both efforts
        state = ConversationState(artifacts=[
            Artifact(id="open-effort", artifact_type="effort", summary="Open task", status="open"),
            Artifact(id="concluded-effort", artifact_type="effort", summary="Concluded task", status="resolved")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert
        assert "Working on open task" in context  # Open effort included
        assert "Old concluded task" not in context  # Concluded effort NOT included

    def test_orchestrator_saves_both_messages_to_effort_log(self, tmp_path):
        """Orchestrator saves both user message and assistant response to effort log via tool use"""
        from oi.routing import route_message  # Will fail - doesn't exist yet
        from oi.models import ConversationState, Artifact
        
        # Arrange: Create state with open effort
        effort_id = "auth-bug"
        state = ConversationState(artifacts=[
            Artifact(id=effort_id, artifact_type="effort", summary="Auth bug", status="open")
        ])
        
        # Act: Route a message while an effort is open
        result = route_message(state, "What about the refresh token?")
        
        # Assert: Should route to the open effort
        assert result == effort_id