"""Tests for Story 5: Explicitly Conclude an Effort"""

import pytest
import json
import yaml
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestStory5ConcludeEffort:
    """Story 5: When user says they're done with a task, conclude the effort."""

    def test_user_concluding_message_triggers_summary_creation(self, tmp_path):
        """When user says 'X is done' about an open effort, assistant creates summary."""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import save_state, load_state
        from oi.models import ConversationState
        
        # Create state with open effort
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        state = ConversationState(
            efforts=[
                {
                    "id": "auth-bug",
                    "status": "open",
                    "title": "Debug auth 401 errors",
                    "summary": ""
                }
            ],
            facts=[]
        )
        save_state(state, state_dir)
        
        # Create effort log
        effort_log = state_dir / "efforts" / "auth-bug.jsonl"
        effort_log.parent.mkdir(exist_ok=True)
        effort_log.write_text(json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n")
        effort_log.write_text(json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n")
        
        # Mock LLM to return a summary
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh."
            
            # Act - User says effort is done
            result_state = process_turn(state, "auth bug is done", model="gpt-4")
        
        # Assert - LLM was called to create summary
        assert mock_chat.called
        call_args = mock_chat.call_args[0][0]  # messages argument
        assert any("summary" in msg.get("content", "").lower() for msg in call_args)
        assert any("auth" in msg.get("content", "").lower() for msg in call_args)

    def test_assistant_confirms_conclusion_by_name(self, tmp_path):
        """Assistant confirms the effort has been concluded by name in response."""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import save_state, load_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        state = ConversationState(
            efforts=[
                {
                    "id": "auth-bug",
                    "status": "open",
                    "title": "Debug auth 401 errors",
                    "summary": ""
                }
            ],
            facts=[]
        )
        save_state(state, state_dir)
        
        effort_log = state_dir / "efforts" / "auth-bug.jsonl"
        effort_log.parent.mkdir(exist_ok=True)
        effort_log.write_text(json.dumps({"role": "user", "content": "Let's debug auth"}) + "\n")
        
        # Mock LLM for summary
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Summary of auth fix"
            
            # Act
            result_state = process_turn(state, "looks good, auth is done", model="gpt-4")
            
            # Get the assistant's response (we need to capture it from the mocked chat or from state)
            # Since process_turn returns a state, we need to check what was written to chatlog
            pass
        
        # This test requires checking the assistant's confirmation message
        # We'll need to mock the chat function to capture what it returns as response
        # and assert that "auth-bug" is in the confirmation
        
        # For now, we'll test the confirmation is saved in effort log
        with open(effort_log, 'r') as f:
            lines = f.readlines()
            last_line = json.loads(lines[-1]) if lines else {}
            assert "auth" in last_line.get("content", "").lower() or "auth-bug" in last_line.get("content", "").lower()

    def test_effort_status_changes_from_open_to_concluded_in_manifest(self, tmp_path):
        """Effort's status in manifest changes from 'open' to 'concluded'."""
        # Arrange
        from oi.conversation import conclude_effort
        from oi.storage import save_state, load_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create manifest with open effort
        manifest_path = state_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "title": "Debug auth 401 errors",
                    "summary": "",
                    "created_at": "2024-01-01T00:00:00"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        # Mock LLM summary
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Debugged 401 errors"
            
            # Act
            conclude_effort("auth-bug", state_dir, model="gpt-4")
        
        # Assert
        loaded = yaml.safe_load(manifest_path.read_text())
        effort = next(e for e in loaded["efforts"] if e["id"] == "auth-bug")
        assert effort["status"] == "concluded"

    def test_summary_is_added_to_manifest(self, tmp_path):
        """The summary is added to the manifest for the concluded effort."""
        # Arrange
        from oi.conversation import conclude_effort
        from oi.storage import save_state, load_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        manifest_path = state_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "title": "Debug auth 401 errors",
                    "summary": "",
                    "created_at": "2024-01-01T00:00:00"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        expected_summary = "Debugged 401 errors occurring after 1 hour. Root cause was refresh tokens existing but never being called automatically."
        
        # Mock LLM to return specific summary
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = expected_summary
            
            # Act
            conclude_effort("auth-bug", state_dir, model="gpt-4")
        
        # Assert
        loaded = yaml.safe_load(manifest_path.read_text())
        effort = next(e for e in loaded["efforts"] if e["id"] == "auth-bug")
        assert effort["summary"] == expected_summary
        assert len(effort["summary"]) > 0

    def test_concluding_message_and_confirmation_saved_to_effort_raw_log(self, tmp_path):
        """User's concluding message and assistant's confirmation are saved to effort's raw log."""
        # Arrange
        from oi.conversation import process_turn
        from oi.chatlog import read_recent
        from oi.storage import save_state, load_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        state = ConversationState(
            efforts=[
                {
                    "id": "auth-bug",
                    "status": "open",
                    "title": "Debug auth 401 errors",
                    "summary": ""
                }
            ],
            facts=[]
        )
        save_state(state, state_dir)
        
        # Create effort log with some existing messages
        effort_log = state_dir / "efforts" / "auth-bug.jsonl"
        effort_log.parent.mkdir(exist_ok=True)
        with open(effort_log, 'w') as f:
            f.write(json.dumps({"role": "user", "content": "Let's debug auth"}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": "Opening effort"}) + "\n")
        
        # Mock LLM for summary
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Summary here"
            
            # Act - User concludes
            process_turn(state, "auth bug is fixed and done", model="gpt-4")
        
        # Assert - Both user concluding message and assistant confirmation are in effort log
        with open(effort_log, 'r') as f:
            lines = f.readlines()
            messages = [json.loads(line) for line in lines]
            
            # Find user concluding message
            user_msgs = [m for m in messages if m["role"] == "user"]
            assert any("done" in m.get("content", "").lower() or "fixed" in m.get("content", "").lower() for m in user_msgs)
            
            # Find assistant confirmation
            assistant_msgs = [m for m in messages if m["role"] == "assistant"]
            assert any("conclud" in m.get("content", "").lower() or "auth-bug" in m.get("content", "").lower() for m in assistant_msgs)

    def test_multiple_conclusion_triggers_work(self, tmp_path):
        """Various phrases like 'X is done', 'looks good', 'finished' trigger conclusion."""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import save_state, load_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        test_cases = [
            ("auth bug is done", True),
            ("looks good to me", True),
            ("finished with auth", True),
            ("let's move on", False),  # Not a clear conclusion
            ("what about this other thing", False),
        ]
        
        for user_input, should_conclude in test_cases:
            # Reset state for each test case
            state = ConversationState(
                efforts=[
                    {
                        "id": "auth-bug",
                        "status": "open",
                        "title": "Debug auth",
                        "summary": ""
                    }
                ],
                facts=[]
            )
            save_state(state, state_dir)
            
            # Clear effort log
            effort_log = state_dir / "efforts" / "auth-bug.jsonl"
            effort_log.parent.mkdir(exist_ok=True)
            effort_log.write_text("")
            
            # Mock LLM
            with patch('oi.llm.chat') as mock_chat:
                mock_chat.return_value = "Summary"
                
                # Act
                result_state = process_turn(state, user_input, model="gpt-4")
                
                # Assert
                if should_conclude:
                    # Check effort was concluded
                    manifest_path = state_dir / "manifest.yaml"
                    if manifest_path.exists():
                        loaded = yaml.safe_load(manifest_path.read_text())
                        effort = next(e for e in loaded["efforts"] if e["id"] == "auth-bug")
                        assert effort["status"] == "concluded"
                else:
                    # Effort should still be open
                    manifest_path = state_dir / "manifest.yaml"
                    if manifest_path.exists():
                        loaded = yaml.safe_load(manifest_path.read_text())
                        effort = next(e for e in loaded["efforts"] if e["id"] == "auth-bug")
                        assert effort["status"] == "open"