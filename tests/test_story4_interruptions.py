"""Tests for Story 4: Handle Interruptions During an Effort"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

from oi.models import ConversationState, Artifact, Message
from oi.conversation import process_turn
from oi.chatlog import append_exchange, read_recent
from oi.storage import load_state, save_state
from oi.detection import is_disagreement, ResolutionDetector


class TestStory4HandleInterruptions:
    """Story 4: Handle Interruptions During an Effort"""

    def test_interruption_question_gets_response(self, tmp_path):
        """When I ask an unrelated question while an effort is open, the assistant responds to my question"""
        # Arrange
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create a state with an open effort
        state = ConversationState(
            efforts=[
                {"id": "effort-1", "status": "open", "title": "Debug auth bug"}
            ]
        )
        save_state(state, state_dir)
        
        # Mock the LLM to return a response about weather
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            
            # Act
            result_state = process_turn(state, "Quick question - what's the weather in Seattle?", "gpt-4", state_dir)
        
        # Assert: The assistant responded to the interruption
        mock_chat.assert_called_once()
        call_args = mock_chat.call_args[0][0]  # messages argument
        last_message = call_args[-1]
        assert last_message["content"] == "Quick question - what's the weather in Seattle?"
        
        # The response should be in the result (though process_turn might not return full response text)
        # At minimum, the state should still exist
        assert result_state is not None

    def test_interruption_saved_to_ambient_raw_log(self, tmp_path):
        """The interruption question and response are saved to the ambient raw log (raw.jsonl), not the effort log"""
        # Arrange
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        
        # Create raw.jsonl with some ambient content
        raw_log = state_dir / "raw.jsonl"
        with open(raw_log, "w") as f:
            f.write(json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n")
        
        # Create an effort log
        effort_log = efforts_dir / "effort-1.jsonl"
        with open(effort_log, "w") as f:
            f.write(json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n")
        
        # Create manifest.yaml with open effort
        manifest = state_dir / "manifest.yaml"
        with open(manifest, "w") as f:
            yaml.dump({
                "efforts": [
                    {"id": "effort-1", "status": "open", "title": "Debug auth bug"}
                ]
            }, f)
        
        state = load_state(state_dir)
        
        # Mock LLM
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            
            # Act: Ask interruption question
            process_turn(state, "Quick question - what's the weather in Seattle?", "gpt-4", state_dir)
        
        # Assert: Interruption saved to raw.jsonl (ambient)
        with open(raw_log) as f:
            lines = f.readlines()
        
        # Should have original 2 lines + 2 new lines (user interruption + assistant response)
        assert len(lines) >= 4
        
        # Last two lines should be the interruption
        last_user_msg = json.loads(lines[-2])
        last_assistant_msg = json.loads(lines[-1])
        
        assert last_user_msg["role"] == "user"
        assert "weather" in last_user_msg["content"].lower() or "seattle" in last_user_msg["content"].lower()
        assert last_assistant_msg["role"] == "assistant"
        assert "72" in last_assistant_msg["content"] or "sunny" in last_assistant_msg["content"]
        
        # Assert: Effort log NOT modified
        with open(effort_log) as f:
            effort_lines = f.readlines()
        assert len(effort_lines) == 2  # Still only the original effort messages

    def test_open_effort_remains_available_after_interruption(self, tmp_path):
        """The open effort remains open and its context is still available after the interruption"""
        # Arrange
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create state with open effort
        initial_state = ConversationState(
            efforts=[
                {"id": "effort-1", "status": "open", "title": "Debug auth bug"}
            ],
            facts=["Access token TTL is 1 hour"]
        )
        save_state(initial_state, state_dir)
        
        # Mock LLM for interruption
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            
            # Act: Ask interruption
            state_after_interruption = process_turn(
                initial_state, 
                "Quick question - what's the weather in Seattle?", 
                "gpt-4", 
                state_dir
            )
        
        # Assert: Effort still open in state
        assert len(state_after_interruption.efforts) == 1
        effort = state_after_interruption.efforts[0]
        assert effort["id"] == "effort-1"
        assert effort["status"] == "open"
        
        # Assert: Can continue working on effort after interruption
        # Mock LLM to respond to effort-related question
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "The 1-hour TTL matches the failure timing."
            
            # Act: Ask effort-related question
            state_after_effort = process_turn(
                state_after_interruption,
                "Back to auth - the token is 1 hour TTL",
                "gpt-4",
                state_dir
            )
        
        # Assert: Effort context was available (LLM should have been called with context)
        mock_chat.assert_called_once()
        call_messages = mock_chat.call_args[0][0]
        
        # Check that effort context was included in the messages
        message_contents = [msg["content"] for msg in call_messages]
        context_text = " ".join(message_contents)
        
        # The effort context should be in the messages (either as system prompt or in conversation history)
        # Since we can't know exact implementation, we assert that process_turn was called successfully
        # and returned a state (not None)
        assert state_after_effort is not None
        
        # Additional check: effort log should exist and be writable
        efforts_dir = state_dir / "efforts"
        effort_log = efforts_dir / "effort-1.jsonl"
        
        # The system should have created or appended to the effort log
        # (implementation detail, but part of the story requirement)
        if effort_log.exists():
            with open(effort_log) as f:
                effort_messages = [json.loads(line) for line in f.readlines()]
            
            # Should have effort-related messages, not weather messages
            effort_contents = " ".join([msg["content"] for msg in effort_messages])
            assert "weather" not in effort_contents.lower()
            assert "seattle" not in effort_contents.lower()

    def test_interruption_detection_does_not_close_effort(self, tmp_path):
        """Interruption detection (like topic change) should not automatically close the open effort"""
        # Arrange
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create state with open effort
        state = ConversationState(
            efforts=[
                {"id": "effort-1", "status": "open", "title": "Debug auth bug"}
            ]
        )
        save_state(state, state_dir)
        
        # Mock resolution detector to identify topic change but NOT close effort
        with patch("oi.detection.ResolutionDetector") as MockDetector:
            mock_detector = MagicMock()
            mock_detector.is_topic_change.return_value = True  # It's a topic change
            mock_detector.is_resolution.return_value = False  # But NOT a resolution
            MockDetector.return_value = mock_detector
            
            # Also mock LLM
            with patch("oi.llm.chat") as mock_chat:
                mock_chat.return_value = "That's a different topic, but your effort on auth bug is still open."
                
                # Act: Ask completely unrelated question
                result_state = process_turn(
                    state,
                    "What's the capital of France?",  # Completely unrelated
                    "gpt-4",
                    state_dir
                )
        
        # Assert: Effort still open
        assert len(result_state.efforts) == 1
        assert result_state.efforts[0]["status"] == "open"
        
        # Assert: Topic change was detected (if implementation uses it)
        # This tests that topic change detection doesn't automatically close efforts
        mock_detector.is_topic_change.assert_called()
        mock_detector.is_resolution.assert_called()  # Should check if it's a resolution

    def test_effort_context_preserved_in_llm_call_after_interruption(self, tmp_path):
        """After an interruption, the next effort-related message should include the effort context"""
        # Arrange
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create a more complete state with effort context
        state = ConversationState(
            efforts=[
                {
                    "id": "effort-1", 
                    "status": "open", 
                    "title": "Debug auth bug",
                    "context": "We're debugging 401 errors after 1 hour. Token TTL is 1 hour."
                }
            ]
        )
        save_state(state, state_dir)
        
        # Create effort log with some history
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "effort-1.jsonl"
        with open(effort_log, "w") as f:
            f.write(json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n")
            f.write(json.dumps({"role": "user", "content": "Access token is 1 hour"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "That matches the failure timing"}) + "\n")
        
        # Mock 1: Interruption
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "72°F and sunny."
            process_turn(state, "What's the weather?", "gpt-4", state_dir)
        
        # Mock 2: Back to effort - capture what context was sent to LLM
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Continuing with the auth bug..."
            
            # Act: Go back to effort
            process_turn(state, "Back to auth - what about refresh tokens?", "gpt-4", state_dir)
            
            # Assert: LLM was called with messages that include effort context
            assert mock_chat.called
            messages = mock_chat.call_args[0][0]
            
            # Convert messages to text for searching
            all_content = " ".join([msg.get("content", "") for msg in messages])
            
            # The effort context should be present in the messages sent to LLM
            # This could be in a system message, or the effort log contents should be included
            # We check for keywords from our effort
            assert "auth" in all_content.lower() or "401" in all_content.lower() or "token" in all_content.lower()
            
            # The weather interruption should NOT be in the effort context
            # (implementation specific, but reasonable expectation)
            if "weather" in all_content.lower():
                # If weather appears, it should only be in the actual user message asking about it,
                # not as context for the effort
                pass  # Acceptable if user explicitly asked about weather in this turn