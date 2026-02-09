"""Tests for Story 7: Assemble Context from Multiple Sources"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml


class TestStory7AssembleContext:
    """Story 7: Assemble Context from Multiple Sources"""

    def test_context_includes_ambient_messages_from_raw_jsonl(self, tmp_path):
        """Context includes all ambient messages from raw.jsonl"""
        from oi.context import build_turn_context

        # Arrange: Create session directory with raw.jsonl containing ambient messages
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        raw_file = session_dir / "raw.jsonl"
        raw_file.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )
        
        # Create manifest with no efforts
        manifest_file = session_dir / "manifest.yaml"
        manifest_file.write_text("efforts: []\n")
        
        # Create empty efforts directory
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        state = None  # No open efforts
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert
        assert "Hey, how's it going?" in context
        assert "Good! Ready to help." in context
        assert "Recent Conversation" in context  # Context includes recent messages section

    def test_context_includes_effort_summaries_from_manifest(self, tmp_path):
        """Context includes all effort summaries from manifest.yaml"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: Create session directory with manifest containing concluded effort summaries
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create raw.jsonl with minimal ambient
        raw_file = session_dir / "raw.jsonl"
        raw_file.write_text("\n")
        
        # Create manifest with concluded effort summary
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
        
        manifest_file = session_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_data))
        
        # Create empty efforts directory
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", status="resolved", 
                    summary="Debugged 401 errors after 1 hour")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert
        assert "Debugged 401 errors after 1 hour" in context
        assert "Resolved Efforts" in context or "Past Work" in context  # Should have resolved efforts section

    def test_context_includes_full_raw_logs_of_open_efforts(self, tmp_path):
        """Context includes full raw logs of all open efforts"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: Create session with an open effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create raw.jsonl with ambient
        raw_file = session_dir / "raw.jsonl"
        raw_file.write_text(
            json.dumps({"role": "user", "content": "Ambient message"}) + "\n"
        )
        
        # Create manifest with open effort
        manifest_data = {
            "efforts": [
                {
                    "id": "guild-feature",
                    "status": "open",
                    "summary": "Add member limit to guilds",
                    "raw_file": "efforts/guild-feature.jsonl"
                }
            ]
        }
        
        manifest_file = session_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_data))
        
        # Create efforts directory with open effort log
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        effort_log = efforts_dir / "guild-feature.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's work on guild feature"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: guild-feature"}) + "\n" +
            json.dumps({"role": "user", "content": "What's the max member limit?"}) + "\n"
        )
        
        state = ConversationState(artifacts=[
            Artifact(id="guild-feature", artifact_type="effort", status="open", 
                    summary="Add member limit to guilds")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert
        assert "Let's work on guild feature" in context
        assert "Opening effort: guild-feature" in context
        assert "What's the max member limit?" in context
        # Should include the full conversation from the open effort

    def test_context_excludes_raw_logs_of_concluded_efforts(self, tmp_path):
        """Context does NOT include the raw logs of concluded efforts"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: Create session with concluded effort that has detailed raw logs
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create raw.jsonl with ambient
        raw_file = session_dir / "raw.jsonl"
        raw_file.write_text("\n")
        
        # Create manifest with concluded effort
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        
        manifest_file = session_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_data))
        
        # Create efforts directory with concluded effort log containing detailed conversation
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n" +
            json.dumps({"role": "user", "content": "The token expires after 1 hour"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Here's the interceptor code: axios.interceptors.request.use(...)"}) + "\n"
        )
        
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", status="resolved", 
                    summary="Debugged 401 errors")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert
        assert "Debugged 401 errors" in context  # Summary should be present
        assert "axios.interceptors.request.use" not in context  # Detailed code from raw log should NOT be present
        assert "The token expires after 1 hour" not in context  # Detailed conversation should NOT be present

    def test_new_effort_after_conclusion_includes_ambient_summaries_and_new_raw_log(self, tmp_path):
        """When opening a new effort after concluding one, context includes ambient + all summaries + new effort's raw log"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: Session with ambient, concluded effort, and newly opened effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create raw.jsonl with ambient messages
        raw_file = session_dir / "raw.jsonl"
        raw_file.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )
        
        # Create manifest with concluded effort and newly opened effort
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour",
                    "raw_file": "efforts/auth-bug.jsonl"
                },
                {
                    "id": "guild-feature",
                    "status": "open",
                    "summary": "Add member limit to guilds",
                    "raw_file": "efforts/guild-feature.jsonl"
                }
            ]
        }
        
        manifest_file = session_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_data))
        
        # Create efforts directory with both effort logs
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # Concluded effort log (should NOT be in context except summary)
        concluded_log = efforts_dir / "auth-bug.jsonl"
        concluded_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug auth"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Detailed interceptor code here..."}) + "\n"
        )
        
        # New open effort log (SHOULD be in context)
        new_log = efforts_dir / "guild-feature.jsonl"
        new_log.write_text(
            json.dumps({"role": "user", "content": "Now let's work on guild feature"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: guild-feature"}) + "\n"
        )
        
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", status="resolved", 
                    summary="Debugged 401 errors after 1 hour"),
            Artifact(id="guild-feature", artifact_type="effort", status="open", 
                    summary="Add member limit to guilds")
        ])
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert
        # Ambient messages present
        assert "Hey, how's it going?" in context
        
        # Concluded effort summary present, but not raw log
        assert "Debugged 401 errors after 1 hour" in context
        assert "Detailed interceptor code here..." not in context
        
        # New open effort raw log present
        assert "Now let's work on guild feature" in context
        assert "Opening effort: guild-feature" in context