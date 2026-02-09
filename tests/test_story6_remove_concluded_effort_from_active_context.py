"""Tests for Story 6: Remove Concluded Effort from Active Context"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest
import yaml

from oi.models import ConversationState, Artifact


class TestStory6RemoveConcludedEffortFromActiveContext:
    """Story 6: Remove Concluded Effort from Active Context"""

    def test_context_excludes_raw_log_of_concluded_effort(self, tmp_path):
        """After an effort is concluded, its raw log is no longer included in context"""
        # Arrange
        from oi.context import build_turn_context  # New function
        
        # Setup session directory with concluded effort
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        
        # Create concluded effort raw log with content
        concluded_log = efforts_dir / "concluded-effort.jsonl"
        concluded_log.write_text(json.dumps({"role": "user", "content": "old concluded message"}) + "\n")
        
        # Create open effort raw log with content
        open_log = efforts_dir / "open-effort.jsonl"
        open_log.write_text(json.dumps({"role": "user", "content": "current open message"}) + "\n")
        
        # Create manifest with both efforts
        manifest = tmp_path / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {"id": "concluded-effort", "status": "concluded", "summary": "Fixed old bug"},
                {"id": "open-effort", "status": "open", "summary": "Working on new feature"}
            ]
        }
        manifest.write_text(yaml.dump(manifest_data))
        
        # Create state with both efforts as artifacts
        state = ConversationState(artifacts=[
            Artifact(id="concluded-effort", artifact_type="effort", summary="Fixed old bug", status="resolved"),
            Artifact(id="open-effort", artifact_type="effort", summary="Working on new feature", status="open")
        ])
        
        # Act
        context = build_turn_context(state, tmp_path)
        
        # Assert - concluded effort raw content NOT in context
        assert "old concluded message" not in context
        # Assert - open effort raw content IS in context
        assert "current open message" in context

    def test_context_includes_only_summary_for_concluded_efforts(self, tmp_path):
        """Only the summary of concluded effort (from manifest) is included in context"""
        # Arrange
        from oi.context import build_turn_context  # New function
        
        # Setup session directory
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        
        # Create concluded effort with raw log
        concluded_log = efforts_dir / "auth-bug.jsonl"
        concluded_log.write_text(json.dumps({"role": "user", "content": "detailed debug steps"}) + "\n")
        
        # Create manifest with concluded effort summary
        manifest = tmp_path / "manifest.yaml"
        summary_text = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor."
        manifest_data = {
            "efforts": [
                {"id": "auth-bug", "status": "concluded", "summary": summary_text}
            ]
        }
        manifest.write_text(yaml.dump(manifest_data))
        
        # Create state
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary=summary_text, status="resolved")
        ])
        
        # Act
        context = build_turn_context(state, tmp_path)
        
        # Assert - summary text IS in context
        assert summary_text in context
        # Assert - raw log details NOT in context
        assert "detailed debug steps" not in context

    def test_concluded_effort_raw_log_preserved_on_disk(self, tmp_path):
        """Raw log file for concluded effort is preserved on disk for future reference"""
        # Arrange
        from oi.storage import conclude_effort  # New function
        
        # Setup open effort
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        effort_log = efforts_dir / "debug-effort.jsonl"
        effort_log.write_text(json.dumps({"role": "user", "content": "debug message 1"}) + "\n" +
                             json.dumps({"role": "assistant", "content": "debug response 1"}) + "\n")
        
        # Create initial manifest
        manifest = session_dir / "manifest.yaml"
        manifest_data = {"efforts": [{"id": "debug-effort", "status": "open"}]}
        manifest.write_text(yaml.dump(manifest_data))
        
        # Create state
        state = ConversationState(artifacts=[
            Artifact(id="debug-effort", artifact_type="effort", summary="Debug session", status="open")
        ])
        
        # Act - conclude the effort
        with patch('oi.llm.summarize_effort') as mock_summarize:
            mock_summarize.return_value = "Debug summary of the session"
            conclude_effort("debug-effort", state, session_dir)
        
        # Assert - raw log file still exists
        assert effort_log.exists()
        
        # Assert - can read raw content from concluded effort log
        with open(effort_log) as f:
            lines = f.readlines()
            assert len(lines) == 2
            first_msg = json.loads(lines[0])
            assert first_msg["content"] == "debug message 1"

    def test_build_turn_context_includes_manifest_summaries_not_raw_logs(self, tmp_path):
        """Context includes concluded effort summaries from manifest, not raw logs"""
        # Arrange
        from oi.context import build_turn_context  # New function
        
        # Setup multiple concluded efforts
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        
        # Create raw logs with detailed content
        effort1_log = efforts_dir / "effort1.jsonl"
        effort1_log.write_text(json.dumps({"role": "user", "content": "detailed step 1 of effort 1"}) + "\n")
        
        effort2_log = efforts_dir / "effort2.jsonl"
        effort2_log.write_text(json.dumps({"role": "user", "content": "detailed step 2 of effort 2"}) + "\n")
        
        # Create manifest with summaries only
        manifest = tmp_path / "manifest.yaml"
        summary1 = "Effort 1: Implemented login flow"
        summary2 = "Effort 2: Fixed database timeout"
        manifest_data = {
            "efforts": [
                {"id": "effort1", "status": "concluded", "summary": summary1},
                {"id": "effort2", "status": "concluded", "summary": summary2}
            ]
        }
        manifest.write_text(yaml.dump(manifest_data))
        
        # Create state
        state = ConversationState(artifacts=[
            Artifact(id="effort1", artifact_type="effort", summary=summary1, status="resolved"),
            Artifact(id="effort2", artifact_type="effort", summary=summary2, status="resolved")
        ])
        
        # Act
        context = build_turn_context(state, tmp_path)
        
        # Assert - summaries are in context
        assert summary1 in context
        assert summary2 in context
        
        # Assert - raw log details are NOT in context
        assert "detailed step 1 of effort 1" not in context
        assert "detailed step 2 of effort 2" not in context

    def test_context_includes_raw_log_only_for_open_efforts(self, tmp_path):
        """Raw log is included in context only for efforts with status 'open'"""
        # Arrange
        from oi.context import build_turn_context  # New function
        
        # Setup efforts with different statuses
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        
        # Create logs
        open_log = efforts_dir / "open.jsonl"
        open_log.write_text(json.dumps({"role": "user", "content": "open effort content"}) + "\n")
        
        resolved_log = efforts_dir / "resolved.jsonl"
        resolved_log.write_text(json.dumps({"role": "user", "content": "resolved effort content"}) + "\n")
        
        archived_log = efforts_dir / "archived.jsonl"
        archived_log.write_text(json.dumps({"role": "user", "content": "archived effort content"}) + "\n")
        
        # Create manifest
        manifest = tmp_path / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {"id": "open", "status": "open", "summary": "Open effort summary"},
                {"id": "resolved", "status": "concluded", "summary": "Resolved effort summary"},
                {"id": "archived", "status": "archived", "summary": "Archived effort summary"}
            ]
        }
        manifest.write_text(yaml.dump(manifest_data))
        
        # Create state with all statuses
        state = ConversationState(artifacts=[
            Artifact(id="open", artifact_type="effort", summary="Open effort summary", status="open"),
            Artifact(id="resolved", artifact_type="effort", summary="Resolved effort summary", status="resolved"),
            Artifact(id="archived", artifact_type="effort", summary="Archived effort summary", status="archived")
        ])
        
        # Act
        context = build_turn_context(state, tmp_path)
        
        # Assert - only open effort raw content in context
        assert "open effort content" in context
        assert "resolved effort content" not in context
        assert "archived effort content" not in context
        
        # Assert - summaries for all efforts in context (from manifest)
        assert "Open effort summary" in context
        assert "Resolved effort summary" in context
        assert "Archived effort summary" in context