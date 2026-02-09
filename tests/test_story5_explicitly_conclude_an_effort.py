"""Tests for Story 5: Conclude Effort"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStory5ExplicitlyConcludeEffort:
    """Story 5: Explicitly Conclude an Effort"""
    
    def test_detect_effort_conclusion_returns_effort_id_when_user_says_effort_is_done(self):
        """AC1: When I say "X is done" about an open effort, the system detects it"""
        from oi.detection import detect_effort_conclusion  # ImportError = red phase
        
        # Arrange
        state = MagicMock()
        state.get_open_efforts.return_value = [
            MagicMock(id="auth-bug", artifact_type="effort", status="open")
        ]
        user_message = "The auth bug is done"
        
        # Act
        result = detect_effort_conclusion(state, user_message)
        
        # Assert
        assert result == "auth-bug"
    
    def test_detect_effort_conclusion_returns_effort_id_when_user_says_looks_good(self):
        """AC1: When I say "looks good" about an open effort, the system detects it"""
        from oi.detection import detect_effort_conclusion
        
        # Arrange
        state = MagicMock()
        state.get_open_efforts.return_value = [
            MagicMock(id="payment-api", artifact_type="effort", status="open")
        ]
        user_message = "The payment API looks good"
        
        # Act
        result = detect_effort_conclusion(state, user_message)
        
        # Assert
        assert result == "payment-api"
    
    def test_conclude_effort_changes_manifest_status_to_concluded(self, tmp_path):
        """AC3: The effort's status in the manifest changes from 'open' to 'concluded'"""
        from oi.storage import conclude_effort  # ImportError = red phase
        
        # Arrange
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        manifest_path = session_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump({
            "efforts": [
                {"id": "auth-bug", "status": "open", "summary": "Debug auth issues"},
                {"id": "other", "status": "open", "summary": "Other task"}
            ]
        }))
        
        # Act
        conclude_effort("auth-bug", session_dir, "Fixed auth bug by adding interceptor")
        
        # Assert
        manifest = yaml.safe_load(manifest_path.read_text())
        auth_bug = next(e for e in manifest["efforts"] if e["id"] == "auth-bug")
        assert auth_bug["status"] == "concluded"
        # Other effort unchanged
        other = next(e for e in manifest["efforts"] if e["id"] == "other")
        assert other["status"] == "open"
    
    def test_conclude_effort_adds_summary_to_manifest(self, tmp_path):
        """AC4: The summary is added to the manifest"""
        from oi.storage import conclude_effort
        
        # Arrange
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        manifest_path = session_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump({
            "efforts": [{"id": "auth-bug", "status": "open"}]
        }))
        
        summary = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh."
        
        # Act
        conclude_effort("auth-bug", session_dir, summary)
        
        # Assert
        manifest = yaml.safe_load(manifest_path.read_text())
        effort = manifest["efforts"][0]
        assert effort["summary"] == summary
        assert "conclusion" not in effort  # Should be "summary" field, not "conclusion"
    
    def test_conclude_effort_saves_messages_to_effort_raw_log(self, tmp_path):
        """AC5: My concluding message and the assistant's confirmation are saved to the effort's raw log"""
        from oi.storage import save_to_effort_log  # ImportError = red phase
        
        # Arrange
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log_path = efforts_dir / "auth-bug.jsonl"
        
        user_message = "The auth bug is done"
        assistant_message = "Concluding effort: auth-bug"
        
        # Act
        save_to_effort_log("auth-bug", efforts_dir, "user", user_message)
        save_to_effort_log("auth-bug", efforts_dir, "assistant", assistant_message)
        
        # Assert
        lines = effort_log_path.read_text().strip().split('\n')
        assert len(lines) == 2
        
        first_entry = json.loads(lines[0])
        assert first_entry["role"] == "user"
        assert first_entry["content"] == user_message
        
        second_entry = json.loads(lines[1])
        assert second_entry["role"] == "assistant"
        assert second_entry["content"] == assistant_message
    
    def test_create_effort_summary_calls_llm_with_effort_content_and_returns_summary(self):
        """AC1: Assistant creates a summary of the effort (LLM call)"""
        from oi.llm import create_effort_summary  # ImportError = red phase
        
        # Arrange
        effort_content = "user: Let's debug the auth bug\nassistant: Opening effort...\nuser: Here's the code\nassistant: Found the issue..."
        expected_summary = "Debugged authentication bug related to token refresh"
        
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = expected_summary
            
            # Act
            result = create_effort_summary(effort_content, "auth-bug")
            
            # Assert
            assert result == expected_summary
            mock_chat.assert_called_once()
            call_args = mock_chat.call_args[0][0]
            assert "auth-bug" in call_args
            assert "summarize" in call_args.lower()
    
    def test_format_conclusion_confirmation_includes_effort_name(self):
        """AC2: The assistant confirms the effort has been concluded by name"""
        from oi.context import format_conclusion_confirmation  # ImportError = red phase
        
        # Arrange
        effort_id = "auth-bug"
        summary = "Debugged 401 errors after 1 hour"
        
        # Act
        confirmation = format_conclusion_confirmation(effort_id, summary)
        
        # Assert
        assert "auth-bug" in confirmation
        assert "concluded" in confirmation.lower() or "concluding" in confirmation.lower()
        # Should include at least part of the summary
        assert any(word in confirmation for word in summary.split()[:3])