"""Tests for Story 6: Remove Concluded Effort from Active Context"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from oi.models import ConversationState, Artifact
from oi.storage import load_state, save_state
from oi.chatlog import read_recent, append_exchange
from oi.conversation import process_turn, generate_id, create_artifact_from_interpretation, build_context


class TestStory6RemoveConcludedEffortFromActiveContext:
    """Story 6: Remove Concluded Effort from Active Context"""

    def test_concluded_effort_raw_log_not_in_context(self, tmp_path):
        """After an effort is concluded, its raw log is no longer included in the context for subsequent turns"""
        # Arrange
        from oi.conversation import conclude_effort  # Will fail - doesn't exist yet
        from oi.context import build_context  # Will fail - doesn't exist yet
        
        # Create a state with one concluded effort
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create raw.jsonl with ambient chatter
        raw_path = state_dir / "raw.jsonl"
        raw_path.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}),
        ]))
        
        # Create efforts directory with a concluded effort
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        effort_path = efforts_dir / "auth-bug.jsonl"
        effort_path.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}),
            json.dumps({"role": "user", "content": "Access token is 1 hour"}),
            json.dumps({"role": "assistant", "content": "That's the problem"}),
        ]))
        
        # Create manifest.yaml with concluded effort
        manifest_path = state_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called.",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        # Load state
        state = load_state(state_dir)
        
        # Act - build context for a new turn
        context = build_context(state)
        
        # Assert - context should NOT contain the raw effort messages
        # (just the summary from manifest)
        assert "auth-bug" in context  # Should mention the effort
        assert "Debugged 401 errors after 1 hour" in context  # Should include summary
        # Should NOT include raw effort messages
        assert "Let's debug the auth bug" not in context
        assert "Opening effort: auth-bug" not in context
        assert "Access token is 1 hour" not in context
        assert "That's the problem" not in context

    def test_only_summary_of_concluded_effort_in_context(self, tmp_path):
        """Only the summary of the concluded effort (from the manifest) is included in the context"""
        # Arrange
        from oi.context import build_context  # Will fail - doesn't exist yet
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create manifest with concluded effort summary
        manifest_path = state_dir / "manifest.yaml"
        summary_text = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor."
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": summary_text,
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        # Create raw.jsonl with ambient
        raw_path = state_dir / "raw.jsonl"
        raw_path.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Ambient message"}),
            json.dumps({"role": "assistant", "content": "Ambient response"}),
        ]))
        
        # Create efforts directory (empty - raw file doesn't need to exist for this test)
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        
        # Load state
        state = load_state(state_dir)
        
        # Act
        context = build_context(state)
        
        # Assert - context should contain the summary exactly as in manifest
        assert summary_text in context
        # Context should be relatively short (just summary, not full raw)
        assert len(context) < 500  # Reasonable limit for summary + ambient

    def test_concluded_effort_raw_log_preserved_on_disk(self, tmp_path):
        """The raw log file for the concluded effort is preserved on disk for potential future reference"""
        # Arrange
        from oi.conversation import conclude_effort  # Will fail - doesn't exist yet
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create an open effort first
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        effort_path = efforts_dir / "auth-bug.jsonl"
        effort_content = '\n'.join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}),
            json.dumps({"role": "user", "content": "Here's the code"}),
            json.dumps({"role": "assistant", "content": "I see the issue"}),
        ])
        effort_path.write_text(effort_content)
        
        # Create manifest with open effort
        manifest_path = state_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        # Load state
        state = load_state(state_dir)
        
        # Act - conclude the effort
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called."
            conclude_effort("auth-bug", state_dir)
        
        # Assert - raw log file should still exist with original content
        assert effort_path.exists()
        assert effort_path.read_text() == effort_content
        
        # Manifest should now have concluded status and summary
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        effort_entry = updated_manifest["efforts"][0]
        assert effort_entry["status"] == "concluded"
        assert "summary" in effort_entry
        assert "raw_file" in effort_entry
        assert effort_entry["raw_file"] == "efforts/auth-bug.jsonl"

    def test_context_size_reduction_after_conclusion(self, tmp_path):
        """Context size should be significantly smaller after effort conclusion"""
        # Arrange
        from oi.context import build_context  # Will fail - doesn't exist yet
        from oi.tokens import count_tokens  # Will fail - doesn't exist yet
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create state with open effort (large raw log)
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        effort_path = efforts_dir / "large-effort.jsonl"
        
        # Create a large effort log (simulating many turns)
        large_content = []
        for i in range(20):
            large_content.append(json.dumps({"role": "user", "content": f"Message {i} about the effort"}))
            large_content.append(json.dumps({"role": "assistant", "content": f"Response {i} with detailed analysis"}))
        effort_path.write_text('\n'.join(large_content))
        
        # Create manifest with open effort
        manifest_path = state_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "large-effort",
                    "status": "open"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        # Create minimal ambient
        raw_path = state_dir / "raw.jsonl"
        raw_path.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Hi"}),
            json.dumps({"role": "assistant", "content": "Hello"}),
        ]))
        
        # Load state
        state = load_state(state_dir)
        
        # Act - get context with open effort
        context_with_open = build_context(state)
        token_count_open = count_tokens(context_with_open, "gpt-4")
        
        # Now conclude the effort
        from oi.conversation import conclude_effort  # Will fail - doesn't exist yet
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Summary of the large effort in about 50 words."
            conclude_effort("large-effort", state_dir)
        
        # Reload state
        state = load_state(state_dir)
        
        # Get context with concluded effort
        context_with_concluded = build_context(state)
        token_count_concluded = count_tokens(context_with_concluded, "gpt-4")
        
        # Assert - context should be much smaller after conclusion
        # (summary instead of full raw log)
        assert token_count_concluded < token_count_open * 0.5  # At least 50% smaller
        assert token_count_concluded < 500  # Summary should be concise

    def test_new_turn_after_conclusion_excludes_raw_log(self, tmp_path):
        """When processing a new turn after effort conclusion, raw log is not included"""
        # Arrange
        from oi.conversation import process_turn  # Will fail - doesn't exist yet
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Set up state with concluded effort
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        effort_path = efforts_dir / "done-effort.jsonl"
        effort_path.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's work on X"}),
            json.dumps({"role": "assistant", "content": "Working on X"}),
            json.dumps({"role": "user", "content": "X is done!"}),
        ]))
        
        manifest_path = state_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "done-effort",
                    "status": "concluded",
                    "summary": "Completed work on X. Successfully implemented feature.",
                    "raw_file": "efforts/done-effort.jsonl"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        raw_path = state_dir / "raw.jsonl"
        raw_path.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Ambient chat"}),
            json.dumps({"role": "assistant", "content": "Ambient reply"}),
        ]))
        
        # Load state
        state = load_state(state_dir)
        
        # Mock the LLM call to see what context it receives
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Response to new question"
            
            # Act - process a new turn
            process_turn(state, "What should we work on next?", "gpt-4", state_dir)
            
            # Assert - check what was sent to LLM
            call_args = mock_chat.call_args
            messages_sent = call_args[0][0]  # First arg is messages list
            context_message = messages_sent[0]["content"]  # System message with context
            
            # Context should include summary but not raw messages
            assert "Completed work on X" in context_message  # Summary present
            assert "Successfully implemented feature" in context_message
            assert "Let's work on X" not in context_message  # Raw messages absent
            assert "Working on X" not in context_message
            assert "X is done!" not in context_message