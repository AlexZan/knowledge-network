"""Tests for Story 4: Interrupt an Effort with Ambient Chat"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from oi.models import ConversationState, Artifact


class TestStory4InterruptEffortWithAmbientChat:
    """Story 4: Interrupt an Effort with Ambient Chat"""

    def test_unrelated_question_saved_to_ambient_log(self, tmp_path):
        """When user asks unrelated question, exchange saved to raw.jsonl"""
        from oi.chatlog import save_ambient_exchange
        raw_log = tmp_path / "raw.jsonl"
        save_ambient_exchange("user", "What's the weather?", raw_log)
        save_ambient_exchange("assistant", "72°F and sunny.", raw_log)
        with open(raw_log) as f:
            lines = f.readlines()
        assert len(lines) == 2
        user_entry = json.loads(lines[0])
        assert user_entry["role"] == "user"
        assert user_entry["content"] == "What's the weather?"
        assistant_entry = json.loads(lines[1])
        assert assistant_entry["role"] == "assistant"
        assert assistant_entry["content"] == "72°F and sunny."

    def test_effort_log_unchanged_by_interruption(self, tmp_path):
        """Open effort file is not modified by unrelated ambient exchange"""
        from oi.efforts import save_to_effort_log
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        initial_content = json.dumps({"role": "user", "content": "debug auth", "timestamp": "2024-01-01T00:00:00"}) + "\n"
        effort_log.write_text(initial_content)
        initial_lines = effort_log.read_text().splitlines()
        save_to_effort_log(efforts_dir, "auth-bug", "user", "What's the weather?")
        final_lines = effort_log.read_text().splitlines()
        assert final_lines == initial_lines

    def test_llm_responds_appropriately_to_unrelated_question(self, tmp_path):
        """LLM responds to unrelated question without effort tool calls"""
        from oi.llm import chat
        with patch('oi.llm.litellm.completion') as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.content = "72°F and sunny."
            mock_response.choices[0].message.tool_calls = None
            mock_completion.return_value = mock_response
            response = chat([{"role": "user", "content": "What's the weather?"}], model="gpt-4", tools=[])
            assert response == "72°F and sunny."
            mock_completion.assert_called_once()

    def test_routing_unrelated_message_to_ambient(self, tmp_path):
        """Message without effort keywords routes to ambient"""
        from oi.routing import route_message
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug", status="open")
        ])
        result = route_message(state, "What's the weather in Seattle?")
        assert result == "ambient"

    def test_routing_related_message_to_effort(self, tmp_path):
        """Message containing effort keywords routes to effort"""
        from oi.routing import route_message
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug", status="open")
        ])
        result = route_message(state, "The auth token is still broken")
        assert result == "auth-bug"

    def test_ambient_exchange_does_not_trigger_effort_tools(self, tmp_path):
        """LLM does not call effort tools for ambient interruption"""
        from oi.llm import chat
        with patch('oi.llm.litellm.completion') as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.content = "72°F and sunny."
            mock_response.choices[0].message.tool_calls = None
            mock_completion.return_value = mock_response
            response = chat([{"role": "user", "content": "What's the weather?"}], model="gpt-4", tools=[])
            assert response == "72°F and sunny."
            mock_completion.assert_called_once()
            call_kwargs = mock_completion.call_args[1]
            assert call_kwargs.get("tools") == []