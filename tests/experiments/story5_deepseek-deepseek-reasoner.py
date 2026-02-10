"""Tests for Story 5: Explicitly Conclude an Effort"""

import pytest
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime


class TestStory5ExplicitlyConcludeEffort:
    """Story 5: Explicitly Conclude an Effort"""
    
    def test_conclude_effort_updates_manifest_status_to_concluded(self, tmp_path):
        """When effort is concluded, its status in manifest changes from 'open' to 'concluded'"""
        # Arrange - create manifest with open effort using standard library
        manifest_path = tmp_path / "manifest.yaml"
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "summary": "Debug 401 errors",
                    "created": "2024-01-01T00:00:00",
                    "updated": "2024-01-01T00:00:00"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest))
        
        # Act - call the implementation function (will fail if doesn't exist)
        from oi.storage import conclude_effort
        conclude_effort("auth-bug", tmp_path, "Debugged 401 errors after 1 hour")
        
        # Assert - status changed to "concluded"
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        effort = next(eff for eff in updated_manifest["efforts"] if eff["id"] == "auth-bug")
        assert effort["status"] == "concluded"
    
    def test_conclude_effort_adds_summary_to_manifest(self, tmp_path):
        """When effort is concluded, the summary is added to the manifest"""
        # Arrange - create manifest with open effort
        manifest_path = tmp_path / "manifest.yaml"
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "summary": "Debug 401 errors",
                    "created": "2024-01-01T00:00:00",
                    "updated": "2024-01-01T00:00:00"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest))
        
        # Act - call with new summary
        from oi.storage import conclude_effort
        new_summary = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh."
        conclude_effort("auth-bug", tmp_path, new_summary)
        
        # Assert - summary was updated
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        effort = next(eff for eff in updated_manifest["efforts"] if eff["id"] == "auth-bug")
        assert effort["summary"] == new_summary
        assert "refresh tokens" in effort["summary"]
    
    def test_conclude_effort_updates_updated_timestamp(self, tmp_path):
        """When effort is concluded, the updated timestamp is refreshed"""
        # Arrange - create manifest with old timestamp
        manifest_path = tmp_path / "manifest.yaml"
        old_time = "2024-01-01T00:00:00"
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "summary": "Debug 401 errors",
                    "created": old_time,
                    "updated": old_time
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest))
        
        # Act
        from oi.storage import conclude_effort
        conclude_effort("auth-bug", tmp_path, "Debugged")
        
        # Assert - updated timestamp changed, created unchanged
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        effort = next(eff for eff in updated_manifest["efforts"] if eff["id"] == "auth-bug")
        assert effort["created"] == old_time
        assert effort["updated"] != old_time
        # Check it's a valid ISO datetime
        parsed_time = datetime.fromisoformat(effort["updated"].replace('Z', '+00:00'))
        assert isinstance(parsed_time, datetime)
    
    def test_save_to_effort_log_appends_user_concluding_message(self, tmp_path):
        """When user says 'X is done', the concluding message is saved to effort's raw log"""
        # Arrange
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        # Add some existing messages using standard library
        existing = [
            {"role": "user", "content": "Let's debug auth", "timestamp": "2024-01-01T00:00:00"},
            {"role": "assistant", "content": "Opening effort", "timestamp": "2024-01-01T00:00:01"}
        ]
        effort_log.write_text("\n".join(json.dumps(msg) for msg in existing) + "\n")
        
        # Act
        from oi.storage import save_to_effort_log
        save_to_effort_log("auth-bug", tmp_path, "user", "Back to auth - I implemented the interceptor and it works. Bug is fixed!")
        
        # Assert - new message appended
        lines = effort_log.read_text().strip().split("\n")
        saved = json.loads(lines[-1])  # Last line
        assert saved["role"] == "user"
        assert "interceptor" in saved["content"]
        assert "Bug is fixed" in saved["content"]
        assert len(lines) == 3  # Original 2 + 1 new
    
    def test_save_to_effort_log_appends_assistant_confirmation(self, tmp_path):
        """When assistant confirms conclusion, the confirmation message is saved to effort's raw log"""
        # Arrange
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        # Add existing messages including user concluding message
        existing = [
            {"role": "user", "content": "Let's debug auth", "timestamp": "2024-01-01T00:00:00"},
            {"role": "user", "content": "Bug is fixed!", "timestamp": "2024-01-01T00:01:00"}
        ]
        effort_log.write_text("\n".join(json.dumps(msg) for msg in existing) + "\n")
        
        # Act
        from oi.storage import save_to_effort_log
        save_to_effort_log("auth-bug", tmp_path, "assistant", "Concluding effort: auth-bug\n\nSummary: Debugged 401 errors...")
        
        # Assert - assistant message appended
        lines = effort_log.read_text().strip().split("\n")
        saved = json.loads(lines[-1])
        assert saved["role"] == "assistant"
        assert "Concluding effort: auth-bug" in saved["content"]
        assert "Summary:" in saved["content"]
        assert len(lines) == 3