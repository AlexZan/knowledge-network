"""Tests for Story 4: Handle Interruptions During an Effort"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestStory4HandleInterruptions:
    """Story 4: Handle Interruptions During an Effort"""

    def test_route_message_returns_ambient_for_unrelated_interruption_when_effort_open(self):
        """When user sends unrelated message while effort open, route returns 'ambient'"""
        # Arrange
        from oi.routing import route_message  # New function - ImportError = correct red
        
        # Create state with an open effort
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", status="open", summary="Auth 401s")
        ])
        
        # Act - unrelated interruption message
        result = route_message(state, "Quick question - what's the weather in Seattle?")
        
        # Assert
        assert result == "ambient"

    def test_route_message_returns_effort_id_for_related_message_when_effort_open(self):
        """When user sends related message while effort open, route returns effort id"""
        # Arrange
        from oi.routing import route_message
        
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", status="open", summary="Auth 401s")
        ])
        
        # Act - message related to the open effort
        result = route_message(state, "Back to auth - I implemented the interceptor")
        
        # Assert
        assert result == "auth-bug"

    def test_log_exchange_appends_to_ambient_raw_jsonl(self, tmp_path):
        """When exchange is ambient, user+assistant messages saved to raw.jsonl"""
        # Arrange
        from oi.chatlog import log_exchange  # New function - ImportError = correct red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(json.dumps({"role": "user", "content": "Hey"}) + "\n")
        
        # Act
        log_exchange(session_dir, "ambient", "user", "What's the weather?", "assistant", "72°F and sunny")
        
        # Assert
        with open(raw_log) as f:
            lines = f.readlines()
        
        assert len(lines) == 3  # Original + 2 new messages
        
        last_user = json.loads(lines[1])
        assert last_user["role"] == "user"
        assert last_user["content"] == "What's the weather?"
        
        last_assistant = json.loads(lines[2])
        assert last_assistant["role"] == "assistant"
        assert last_assistant["content"] == "72°F and sunny"

    def test_log_exchange_appends_to_effort_jsonl(self, tmp_path):
        """When exchange is effort-related, messages saved to effort log, not raw.jsonl"""
        # Arrange
        from oi.chatlog import log_exchange
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(json.dumps({"role": "user", "content": "Hey"}) + "\n")
        
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(json.dumps({"role": "user", "content": "Let's debug auth"}) + "\n")
        
        # Act
        log_exchange(session_dir, "auth-bug", "user", "The TTL is 1 hour", "assistant", "That matches the failure")
        
        # Assert
        with open(raw_log) as f:
            raw_lines = f.readlines()
        assert len(raw_lines) == 1  # Raw unchanged
        
        with open(effort_log) as f:
            effort_lines = f.readlines()
        
        assert len(effort_lines) == 3  # Original + 2 new
        
        last_user = json.loads(effort_lines[1])
        assert last_user["role"] == "user"
        assert last_user["content"] == "The TTL is 1 hour"

    def test_open_effort_remains_open_after_interruption(self, tmp_path):
        """Effort status unchanged in manifest after ambient interruption"""
        # Arrange
        from oi.storage import save_exchange_and_update_state  # New function - ImportError = correct red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create manifest with open effort
        manifest_path = session_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [{"id": "auth-bug", "status": "open", "summary": "Debug auth 401s"}]
        }
        import yaml
        manifest_path.write_text(yaml.dump(manifest_data))
        
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", status="open", summary="Auth 401s")
        ])
        
        # Act - save interruption (ambient exchange)
        save_exchange_and_update_state(
            session_dir=session_dir,
            target="ambient",
            user_message="What's the weather?",
            assistant_response="72°F",
            state=state
        )
        
        # Assert
        loaded = yaml.safe_load(manifest_path.read_text())
        efforts = loaded["efforts"]
        assert len(efforts) == 1
        assert efforts[0]["id"] == "auth-bug"
        assert efforts[0]["status"] == "open"

    def test_build_ambient_context_includes_interruption_message(self, tmp_path):
        """When building context for ambient response, interruption message included"""
        # Arrange
        from oi.context import build_ambient_context  # New function - ImportError = correct red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        raw_log = session_dir / "raw.jsonl"
        # Set up ambient log with some history
        with open(raw_log, "w") as f:
            f.write(json.dumps({"role": "user", "content": "Hey"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Hello"}) + "\n")
        
        # Act
        context = build_ambient_context(
            session_dir=session_dir,
            user_message="Quick question - what's the weather in Seattle?"
        )
        
        # Assert
        assert "Quick question - what's the weather in Seattle?" in context
        assert "Hey" in context  # Previous history included
        assert "auth-bug" not in context  # Effort context not included

    def test_generate_response_for_ambient_context_calls_llm(self):
        """When ambient context is ready, generate_response calls LLM with context"""
        # Arrange
        from oi.llm import chat  # Leaf function for LLM calls - ImportError = correct red
        
        ambient_context = "User: Hey\nAssistant: Hello\nUser: Quick question - what's the weather in Seattle?"
        
        # Mock the actual LLM API call, not our wrapper
        with patch('oi.llm._call_openai_api') as mock_api:
            mock_api.return_value = "72°F and sunny in Seattle today."
            
            # Act - directly test the chat function
            response = chat(ambient_context, "gpt-4")
        
        # Assert
        assert response == "72°F and sunny in Seattle today."
        mock_api.assert_called_once()
        # Don't assert exact args - just that it was called with our context
        call_args = mock_api.call_args[0]
        assert ambient_context in str(call_args[0])

    def test_effort_log_unchanged_after_interruption(self, tmp_path):
        """Effort log file not modified when interruption logged to ambient"""
        # Arrange
        from oi.chatlog import log_exchange
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # Create effort log with initial content
        effort_log = efforts_dir / "auth-bug.jsonl"
        initial_content = [
            {"role": "user", "content": "Let's debug auth", "timestamp": "2024-01-01T10:00:00"},
            {"role": "assistant", "content": "Opening effort: auth-bug", "timestamp": "2024-01-01T10:00:01"}
        ]
        with open(effort_log, "w") as f:
            for item in initial_content:
                f.write(json.dumps(item) + "\n")
        
        # Create ambient log
        raw_log = session_dir / "raw.jsonl"
        raw_log.touch()
        
        # Get original effort log content
        original_lines = effort_log.read_text()
        
        # Act - log ambient interruption
        log_exchange(
            session_dir=session_dir,
            target="ambient",  # NOT the effort
            role_user="user",
            content_user="What's the weather?",
            role_assistant="assistant",
            content_assistant="72°F"
        )
        
        # Assert - effort log unchanged
        assert effort_log.read_text() == original_lines
        
        # And ambient log now has the exchange
        with open(raw_log) as f:
            raw_lines = f.readlines()
        assert len(raw_lines) == 2  # user + assistant
        assert "What's the weather?" in raw_lines[0]