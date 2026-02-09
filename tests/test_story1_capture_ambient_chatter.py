"""Tests for Story 1: Capture Ambient Chatter"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import tempfile

from oi.models import ConversationState, Artifact


class TestStory1CaptureAmbientChatter:
    """Story 1: Capture Ambient Chatter"""

    def test_ambient_message_saved_to_raw_jsonl(self, tmp_path):
        """When user sends a message not related to an open effort, it is saved to raw.jsonl"""
        # Arrange
        from oi.chatlog import save_ambient_message  # New function, ImportError = correct red
        raw_log = tmp_path / "raw.jsonl"
        
        # No open efforts
        state = ConversationState(artifacts=[])
        message = "Hey, how's it going?"
        
        # Act
        save_ambient_message(state, message, raw_log)
        
        # Assert
        assert raw_log.exists()
        with open(raw_log, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            saved = json.loads(lines[0])
            assert saved["role"] == "user"
            assert saved["content"] == message
            assert "timestamp" in saved  # Should have timestamp

    def test_ambient_assistant_response_saved_to_raw_jsonl(self, tmp_path):
        """Assistant's response to ambient message is also saved to raw.jsonl"""
        # Arrange
        from oi.chatlog import save_ambient_response  # New function
        raw_log = tmp_path / "raw.jsonl"
        
        # Add user message first
        with open(raw_log, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "Hey"}) + '\n')
        
        response = "Good! Ready to help."
        
        # Act
        save_ambient_response(response, raw_log)
        
        # Assert
        with open(raw_log, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2
            
            user_msg = json.loads(lines[0])
            assert user_msg["role"] == "user"
            
            assistant_msg = json.loads(lines[1])
            assert assistant_msg["role"] == "assistant"
            assert assistant_msg["content"] == response
            assert "timestamp" in assistant_msg

    def test_ambient_messages_included_in_next_turn_context(self, tmp_path):
        """Ambient messages and responses are always included in context for next turn"""
        # Arrange
        from oi.context import build_conversation_context  # Already exists, but needs to include ambient
        from oi.models import ConversationState
        
        # Create raw.jsonl with ambient exchange
        raw_log = tmp_path / "raw.jsonl"
        ambient_exchanges = [
            {"role": "user", "content": "Hey, how's it going?", "timestamp": "2024-01-01T10:00:00"},
            {"role": "assistant", "content": "Good! Ready to help.", "timestamp": "2024-01-01T10:00:01"}
        ]
        
        with open(raw_log, 'w') as f:
            for exchange in ambient_exchanges:
                f.write(json.dumps(exchange) + '\n')
        
        # No open efforts
        state = ConversationState(artifacts=[])
        
        # Act
        context = build_conversation_context(state, raw_log)
        
        # Assert
        # Should include the ambient exchanges in context
        assert "Hey, how's it going?" in context
        assert "Good! Ready to help." in context
        # Should indicate these are from ambient context
        assert "ambient" in context.lower() or "chat" in context.lower()

    def test_message_not_related_to_open_effort_routes_to_ambient(self):
        """Routing logic identifies messages not related to open efforts as ambient"""
        # Arrange
        from oi.routing import route_message  # New function
        message = "Quick question - what's the weather in Seattle?"
        
        # No open efforts
        state = ConversationState(artifacts=[])
        
        # Act
        result = route_message(state, message)
        
        # Assert
        assert result == "ambient"

    def test_message_related_to_open_effort_routes_to_effort(self):
        """Routing logic identifies messages related to open efforts as effort-specific"""
        # Arrange
        from oi.routing import route_message
        message = "Back to auth - I implemented the interceptor and it works."
        
        # Has open effort
        state = ConversationState(artifacts=[
            Artifact(
                id="auth-bug",
                artifact_type="effort",
                summary="Debug auth 401 errors",
                status="open"
            )
        ])
        
        # Act - don't mock internal function, just test behavior
        result = route_message(state, message)
        
        # Assert - should route to the effort ID
        assert result == "auth-bug"

    def test_ambient_log_preserves_all_exchanges_chronologically(self, tmp_path):
        """raw.jsonl preserves chronological order of all ambient exchanges"""
        # Arrange
        from oi.chatlog import save_ambient_exchange  # New function that saves both at once
        raw_log = tmp_path / "raw.jsonl"
        
        exchanges = [
            ("user", "Hey"),
            ("assistant", "Hi there"),
            ("user", "Quick question"),
            ("assistant", "Sure")
        ]
        
        # Act - simulate multiple turns
        for role, content in exchanges:
            save_ambient_exchange(role, content, raw_log)
        
        # Assert
        with open(raw_log, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 4
            
            for i, (expected_role, expected_content) in enumerate(exchanges):
                saved = json.loads(lines[i])
                assert saved["role"] == expected_role
                assert saved["content"] == expected_content
        
        # Verify chronological order by timestamps
        with open(raw_log, 'r') as f:
            timestamps = []
            for line in f:
                saved = json.loads(line.strip())
                timestamps.append(saved["timestamp"])
            
            # Timestamps should be in increasing order
            assert all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))

    def test_ambient_context_includes_most_recent_exchanges_first(self, tmp_path):
        """When building context, most recent ambient exchanges appear first (newest at top)"""
        # Arrange
        from oi.context import build_conversation_context
        
        # Create raw.jsonl with multiple ambient exchanges
        raw_log = tmp_path / "raw.jsonl"
        exchanges = [
            {"role": "user", "content": "First message", "timestamp": "2024-01-01T10:00:00"},
            {"role": "assistant", "content": "First response", "timestamp": "2024-01-01T10:00:01"},
            {"role": "user", "content": "Second message", "timestamp": "2024-01-01T10:01:00"},
            {"role": "assistant", "content": "Second response", "timestamp": "2024-01-01T10:01:01"},
            {"role": "user", "content": "Third message", "timestamp": "2024-01-01T10:02:00"},
            {"role": "assistant", "content": "Third response", "timestamp": "2024-01-01T10:02:01"},
        ]
        
        with open(raw_log, 'w') as f:
            for exchange in exchanges:
                f.write(json.dumps(exchange) + '\n')
        
        state = ConversationState(artifacts=[])
        
        # Act
        context = build_conversation_context(state, raw_log)
        
        # Assert - most recent exchanges should appear first in context
        # Find positions in the context string
        third_pos = context.find("Third message")
        second_pos = context.find("Second message")
        first_pos = context.find("First message")
        
        # All should be present
        assert third_pos != -1
        assert second_pos != -1
        assert first_pos != -1
        
        # Most recent (third) should appear before older ones
        assert third_pos < second_pos < first_pos