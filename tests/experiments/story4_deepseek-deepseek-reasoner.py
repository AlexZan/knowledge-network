"""Tests for Story 4: Handle Interruptions During an Effort"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import yaml

from oi.conversation import process_turn
from oi.storage import load_state, save_state
from oi.models import ConversationState, Message
from oi.chatlog import read_recent


class TestStory4HandleInterruptions:
    """Story 4: Handle Interruptions During an Effort"""

    @pytest.fixture
    def state_with_open_effort(self, tmp_path):
        """Create a state directory with an open effort"""
        state_dir = tmp_path / "test_session"
        state_dir.mkdir()
        
        # Create manifest with open effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "start_turn": 3,
                    "summary": "Debugging 401 errors after 1 hour"
                }
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Create raw.jsonl with initial ambient messages
        raw_log = state_dir / "raw.jsonl"
        with open(raw_log, 'w') as f:
            # Turns 1-2: ambient chatter
            f.write(json.dumps({"turn": 1, "role": "user", "content": "Hey, how's it going?"}) + "\n")
            f.write(json.dumps({"turn": 2, "role": "assistant", "content": "Good! Ready to help."}) + "\n")
        
        # Create effort log with effort messages
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        with open(effort_log, 'w') as f:
            # Turns 3-4: effort start
            f.write(json.dumps({"turn": 3, "role": "user", "content": "Let's debug the auth bug"}) + "\n")
            f.write(json.dumps({"turn": 4, "role": "assistant", "content": "Opening effort: auth-bug"}) + "\n")
            # Turns 5-10: working on effort
            f.write(json.dumps({"turn": 5, "role": "user", "content": "Access token is 1 hour"}) + "\n")
            f.write(json.dumps({"turn": 6, "role": "assistant", "content": "The 1-hour TTL matches"}) + "\n")
        
        # Create state
        state = ConversationState(state_dir=state_dir)
        save_state(state, state_dir)
        
        return state_dir

    def test_interruption_gets_response(self, state_with_open_effort, tmp_path):
        """When I ask an unrelated question while an effort is open, the assistant responds to my question"""
        state_dir = state_with_open_effort
        
        # Mock the LLM to return a weather response
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            
            # Load current state
            state = load_state(state_dir)
            
            # Process interruption (unrelated weather question)
            result = process_turn(state, "Quick question - what's the weather in Seattle?", "gpt-4")
            
            # Verify LLM was called
            mock_chat.assert_called_once()
            
            # Verify response contains weather info
            assert "72°F" in result.assistant_response
            assert "sunny" in result.assistant_response.lower()

    def test_interruption_saved_to_ambient_log(self, state_with_open_effort, tmp_path):
        """The interruption question and response are saved to the ambient raw log, not the effort log"""
        state_dir = state_with_open_effort
        raw_log = state_dir / "raw.jsonl"
        effort_log = state_dir / "efforts" / "auth-bug.jsonl"
        
        # Count initial lines
        initial_raw_lines = len(raw_log.read_text().strip().splitlines())
        initial_effort_lines = len(effort_log.read_text().strip().splitlines())
        
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            
            state = load_state(state_dir)
            process_turn(state, "Quick question - what's the weather in Seattle?", "gpt-4")
            
            # Save updated state
            save_state(state, state_dir)
        
        # Check raw.jsonl has new lines (interruption)
        final_raw_lines = len(raw_log.read_text().strip().splitlines())
        assert final_raw_lines == initial_raw_lines + 2  # User + assistant messages
        
        # Check effort log unchanged
        final_effort_lines = len(effort_log.read_text().strip().splitlines())
        assert final_effort_lines == initial_effort_lines
        
        # Verify raw.jsonl contains weather-related messages
        raw_content = raw_log.read_text()
        assert "weather in Seattle" in raw_content
        assert "72°F" in raw_content
        
        # Verify effort log does NOT contain weather messages
        effort_content = effort_log.read_text()
        assert "weather" not in effort_content
        assert "Seattle" not in effort_content

    def test_open_effort_remains_open_after_interruption(self, state_with_open_effort, tmp_path):
        """The open effort remains open and its context is still available after the interruption"""
        state_dir = state_with_open_effort
        manifest_path = state_dir / "manifest.yaml"
        
        # Load initial manifest
        initial_manifest = yaml.safe_load(manifest_path.read_text())
        initial_effort = initial_manifest["efforts"][0]
        assert initial_effort["status"] == "open"
        assert initial_effort["id"] == "auth-bug"
        
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            
            state = load_state(state_dir)
            process_turn(state, "Quick question - what's the weather in Seattle?", "gpt-4")
            save_state(state, state_dir)
        
        # Load manifest after interruption
        final_manifest = yaml.safe_load(manifest_path.read_text())
        final_effort = final_manifest["efforts"][0]
        
        # Effort should still be open
        assert final_effort["status"] == "open"
        assert final_effort["id"] == "auth-bug"
        
        # Effort context should still be accessible via conversation state
        state = load_state(state_dir)
        open_efforts = state.get_open_efforts()
        assert len(open_efforts) == 1
        assert open_efforts[0]["id"] == "auth-bug"
        
        # We should be able to continue the effort after interruption
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Let me check the refresh token logic again."
            
            # Process another turn about the auth bug (continuing effort)
            result = process_turn(state, "Back to auth - what about the refresh token timing?", "gpt-4")
            
            # Verify context includes effort history
            # The mock should have been called with messages including effort context
            call_args = mock_chat.call_args
            messages = call_args[0][0]  # First positional arg is messages list
            
            # Should include effort messages (turns 3-6) in context
            effort_messages = [m for m in messages if "auth bug" in m.get("content", "").lower() or 
                              "refresh token" in m.get("content", "").lower()]
            assert len(effort_messages) > 0  # Should have some effort context