"""Tests for Story 6: Remove Concluded Effort from Active Context"""

import json
import yaml
import pytest
from pathlib import Path


class TestStory6RemoveConcludedEffortFromActiveContext:
    """Story 6: Remove Concluded Effort from Active Context"""

    def test_context_excludes_raw_log_of_concluded_effort(self, tmp_path):
        """After an effort is concluded, its raw log is no longer included in the context for subsequent turns"""
        # Arrange
        from oi.context import build_turn_context  # Will fail - doesn't exist yet
        
        # Create session directory with concluded effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create manifest with concluded effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh.",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        manifest_path = session_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create raw log for concluded effort (should NOT be in context)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n" +
            json.dumps({"role": "user", "content": "Access token is 1 hour"}) + "\n"
        )
        
        # Create raw.jsonl with ambient messages
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )
        
        # State with concluded effort artifact
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(
                id="auth-bug",
                artifact_type="effort",
                summary="Debugged 401 errors",
                status="resolved",
                resolution="Added axios interceptor"
            )
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert: raw effort content should NOT be in context
        assert "Let's debug the auth bug" not in context
        assert "Opening effort: auth-bug" not in context
        assert "Access token is 1 hour" not in context
        
        # Assert: ambient content should be in context
        assert "Hey, how's it going?" in context
        assert "Good! Ready to help." in context

    def test_context_includes_summary_of_concluded_effort(self, tmp_path):
        """Only the summary of the concluded effort (from the manifest) is included in the context"""
        # Arrange
        from oi.context import build_turn_context
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create manifest with concluded effort summary
        summary_text = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh."
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": summary_text,
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        manifest_path = session_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create raw log for concluded effort
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n"
        )
        
        # Create ambient raw log
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hello"}) + "\n"
        )
        
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(
                id="auth-bug",
                artifact_type="effort",
                summary="Debugged 401 errors",
                status="resolved"
            )
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert: summary should be in context
        assert "Debugged 401 errors after 1 hour" in context
        assert "axios interceptor for proactive refresh" in context
        assert summary_text in context

    def test_raw_log_file_preserved_after_conclusion(self, tmp_path):
        """The raw log file for the concluded effort is preserved on disk for potential future reference"""
        # Arrange
        from oi.context import build_turn_context
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create manifest with concluded effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed auth bug",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        manifest_path = session_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create raw log for concluded effort
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        original_content = (
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort"}) + "\n" +
            json.dumps({"role": "user", "content": "Access token is 1 hour"}) + "\n"
        )
        effort_log.write_text(original_content)
        
        # Create ambient raw log
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hello"}) + "\n"
        )
        
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(
                id="auth-bug",
                artifact_type="effort",
                summary="Fixed auth bug",
                status="resolved"
            )
        ])
        
        # Act - build context (should not modify or delete the raw log)
        context = build_turn_context(state, session_dir)
        
        # Assert: raw log file still exists
        assert effort_log.exists()
        
        # Assert: content is unchanged
        assert effort_log.read_text() == original_content
        
        # Assert: file is still in efforts directory
        assert effort_log.parent == efforts_dir
        assert effort_log.name == "auth-bug.jsonl"

    def test_context_includes_multiple_concluded_effort_summaries(self, tmp_path):
        """Context includes summaries of multiple concluded efforts but not their raw logs"""
        # Arrange
        from oi.context import build_turn_context
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create manifest with multiple concluded efforts
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed 401 errors with axios interceptor",
                    "raw_file": "efforts/auth-bug.jsonl"
                },
                {
                    "id": "ui-bug",
                    "status": "concluded", 
                    "summary": "Fixed button alignment in mobile view",
                    "raw_file": "efforts/ui-bug.jsonl"
                }
            ]
        }
        manifest_path = session_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create raw logs for concluded efforts
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # auth-bug raw log
        auth_log = efforts_dir / "auth-bug.jsonl"
        auth_log.write_text(
            json.dumps({"role": "user", "content": "auth debug message"}) + "\n"
        )
        
        # ui-bug raw log
        ui_log = efforts_dir / "ui-bug.jsonl"
        ui_log.write_text(
            json.dumps({"role": "user", "content": "ui debug message"}) + "\n"
        )
        
        # Create ambient raw log
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hello"}) + "\n"
        )
        
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Fixed 401 errors", status="resolved"),
            Artifact(id="ui-bug", artifact_type="effort", summary="Fixed button alignment", status="resolved")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert: summaries are in context
        assert "Fixed 401 errors with axios interceptor" in context
        assert "Fixed button alignment in mobile view" in context
        
        # Assert: raw log content is NOT in context
        assert "auth debug message" not in context
        assert "ui debug message" not in context