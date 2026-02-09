"""Tests for Story 3: Capture Messages Within an Open Effort"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from oi.models import ConversationState, Artifact


class TestStory3CaptureMessagesWithinOpenEffort:
    """Story 3: Capture Messages Within an Open Effort"""

    def test_user_message_saved_to_open_effort_log(self, tmp_path):
        """When user sends a message while an effort is open, it is saved to that effort's raw log"""
        # Arrange
        from oi.effort_log import append_to_effort_log  # New function, ImportError = red
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        effort_id = "auth-bug"
        effort_log = efforts_dir / f"{effort_id}.jsonl"
        
        # Act - user message
        user_message = {"role": "user", "content": "Let's debug the auth bug"}
        append_to_effort_log(session_dir, effort_id, user_message)
        
        # Assert
        assert effort_log.exists()
        with open(effort_log) as f:
            lines = f.readlines()
            assert len(lines) == 1
            saved = json.loads(lines[0])
            assert saved["role"] == "user"
            assert saved["content"] == "Let's debug the auth bug"

    def test_assistant_response_saved_to_same_effort_log(self, tmp_path):
        """The assistant's response is also saved to the same effort's raw log"""
        # Arrange
        from oi.effort_log import append_to_effort_log  # New function, ImportError = red
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        effort_id = "auth-bug"
        effort_log = efforts_dir / f"{effort_id}.jsonl"
        
        # Add user message first
        user_msg = {"role": "user", "content": "Let's debug the auth bug"}
        append_to_effort_log(session_dir, effort_id, user_msg)
        
        # Act - assistant response
        assistant_msg = {"role": "assistant", "content": "Opening effort: auth-bug"}
        append_to_effort_log(session_dir, effort_id, assistant_msg)
        
        # Assert
        with open(effort_log) as f:
            lines = f.readlines()
            assert len(lines) == 2
            
            # Check first message is user
            first = json.loads(lines[0])
            assert first["role"] == "user"
            
            # Check second message is assistant
            second = json.loads(lines[1])
            assert second["role"] == "assistant"
            assert "auth-bug" in second["content"]

    def test_open_effort_raw_log_included_in_context(self, tmp_path):
        """The entire raw log of an open effort is included in the context for the next turn"""
        # Arrange
        from oi.context import build_turn_context  # Only ONE new import
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        effort_id = "auth-bug"
        effort_log = efforts_dir / f"{effort_id}.jsonl"
        
        # Create effort log with conversation history using standard library
        messages = [
            {"role": "user", "content": "Let's debug the auth bug"},
            {"role": "assistant", "content": "Opening effort: auth-bug"},
            {"role": "user", "content": "Access token is 1 hour, yes we have refresh tokens"},
            {"role": "assistant", "content": "The 1-hour TTL matches the failure timing."}
        ]
        for msg in messages:
            effort_log.write_text(json.dumps(msg) + "\n", mode="a" if effort_log.exists() else "w")
        
        # Create state with open effort artifact
        state = ConversationState(
            artifacts=[
                Artifact(
                    id=effort_id,
                    artifact_type="effort",
                    summary="Debug auth bug",
                    status="open"
                )
            ]
        )
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert - all messages from effort log should be in context
        assert "Let's debug the auth bug" in context
        assert "Opening effort: auth-bug" in context
        assert "Access token is 1 hour" in context
        assert "1-hour TTL matches" in context

    def test_only_open_effort_logs_included_in_context(self, tmp_path):
        """Only open effort logs are included in context, not concluded efforts"""
        # Arrange
        from oi.context import build_turn_context  # Only ONE new import
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        # Create open effort log
        open_effort_id = "auth-bug"
        open_log = efforts_dir / f"{open_effort_id}.jsonl"
        open_log.write_text(json.dumps({"role": "user", "content": "Debug auth"}) + "\n")
        
        # Create concluded effort log
        concluded_effort_id = "payment-feature"
        concluded_log = efforts_dir / f"{concluded_effort_id}.jsonl"
        concluded_log.write_text(json.dumps({"role": "user", "content": "Implement payment"}) + "\n")
        
        # Create state with one open, one concluded
        state = ConversationState(
            artifacts=[
                Artifact(
                    id=open_effort_id,
                    artifact_type="effort",
                    summary="Debug auth",
                    status="open"
                ),
                Artifact(
                    id=concluded_effort_id,
                    artifact_type="effort",
                    summary="Payment feature",
                    status="resolved"
                )
            ]
        )
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert - only open effort content in context
        assert "Debug auth" in context
        assert "Implement payment" not in context

    def test_multiple_open_efforts_all_included_in_context(self, tmp_path):
        """When multiple efforts are open, all their raw logs are included in context"""
        # Arrange
        from oi.context import build_turn_context  # Only ONE new import
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        # Create two open effort logs
        effort1_id = "auth-bug"
        effort1_log = efforts_dir / f"{effort1_id}.jsonl"
        effort1_log.write_text(json.dumps({"role": "user", "content": "Auth debug message"}) + "\n")
        
        effort2_id = "payment-feature"
        effort2_log = efforts_dir / f"{effort2_id}.jsonl"
        effort2_log.write_text(json.dumps({"role": "user", "content": "Payment feature message"}) + "\n")
        
        # Create state with both efforts open
        state = ConversationState(
            artifacts=[
                Artifact(
                    id=effort1_id,
                    artifact_type="effort",
                    summary="Debug auth",
                    status="open"
                ),
                Artifact(
                    id=effort2_id,
                    artifact_type="effort",
                    summary="Payment feature",
                    status="open"
                )
            ]
        )
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert - both effort contents in context
        assert "Auth debug message" in context
        assert "Payment feature message" in context

    def test_effort_log_appends_new_messages(self, tmp_path):
        """New messages are appended to existing effort log without overwriting"""
        # Arrange
        from oi.effort_log import append_to_effort_log  # New function, ImportError = red
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        effort_id = "auth-bug"
        effort_log = efforts_dir / f"{effort_id}.jsonl"
        
        # Create initial messages using standard library
        initial_messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Message 2"}
        ]
        for msg in initial_messages:
            effort_log.write_text(json.dumps(msg) + "\n", mode="a" if effort_log.exists() else "w")
        
        # Act - append new message
        new_message = {"role": "user", "content": "Message 3"}
        append_to_effort_log(session_dir, effort_id, new_message)
        
        # Assert - all 3 messages present, in order
        with open(effort_log) as f:
            lines = f.readlines()
            assert len(lines) == 3
            
            messages = [json.loads(line) for line in lines]
            assert messages[0]["content"] == "Message 1"
            assert messages[1]["content"] == "Message 2"
            assert messages[2]["content"] == "Message 3"

    def test_effort_log_creates_file_if_not_exists(self, tmp_path):
        """Effort log file is created if it doesn't exist when first message saved"""
        # Arrange
        from oi.effort_log import append_to_effort_log  # New function, ImportError = red
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        effort_id = "new-effort"
        effort_log = efforts_dir / f"{effort_id}.jsonl"
        
        # Assert file doesn't exist initially
        assert not effort_log.exists()
        
        # Act
        message = {"role": "user", "content": "First message in new effort"}
        append_to_effort_log(session_dir, effort_id, message)
        
        # Assert file created and contains message
        assert effort_log.exists()
        with open(effort_log) as f:
            saved = json.loads(f.readline())
            assert saved["content"] == "First message in new effort"