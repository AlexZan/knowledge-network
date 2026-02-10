"""Tests for Story 8: Start New Effort After Concluding One"""

import pytest
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStory8StartNewEffortAfterConcludingOne:
    """Story 8: Start a New Effort After Concluding One"""

    def test_user_let_work_on_starts_new_effort_with_open_status(self, tmp_path):
        """After concluding an effort, I can say 'Let's work on Y' to start a new effort"""
        # Arrange
        from oi.models import ConversationState, Artifact
        from oi.efforts import start_new_effort  # New function, ImportError = red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create manifest with concluded effort
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed token refresh",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest_data))
        
        # Create state with concluded artifact
        state = ConversationState(
            artifacts=[
                Artifact(
                    id="auth-bug",
                    artifact_type="effort",
                    summary="Fixed token refresh",
                    status="resolved",
                    resolution="Added axios interceptor"
                )
            ]
        )
        
        # Act
        new_effort_id = start_new_effort(
            state=state,
            session_dir=session_dir,
            user_message="Let's work on guild-feature - I want to add a member limit",
            assistant_response="Opening effort: guild-feature"
        )
        
        # Assert
        assert new_effort_id == "guild-feature"
        
        # Check artifact in state
        new_efforts = [a for a in state.artifacts if a.artifact_type == "effort" and a.id == "guild-feature"]
        assert len(new_efforts) == 1
        assert new_efforts[0].status == "open"
        assert "guild-feature" in new_efforts[0].summary.lower()
    
    def test_new_effort_file_created_in_efforts_directory(self, tmp_path):
        """The assistant creates a new effort file for Y"""
        # Arrange
        from oi.models import ConversationState, Artifact
        from oi.efforts import start_new_effort
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        
        # Create empty manifest
        (session_dir / "manifest.yaml").write_text(yaml.dump({"efforts": []}))
        
        state = ConversationState(artifacts=[])
        
        # Act
        start_new_effort(
            state=state,
            session_dir=session_dir,
            user_message="Let's debug the rate limiting issue",
            assistant_response="Opening effort: rate-limiting"
        )
        
        # Assert
        effort_file = efforts_dir / "rate-limiting.jsonl"
        assert effort_file.exists()
        
        # File should contain the exchange
        with open(effort_file) as f:
            lines = f.readlines()
        assert len(lines) == 2
        
        user_msg = json.loads(lines[0])
        assert user_msg["role"] == "user"
        assert "rate limiting" in user_msg["content"].lower()
        
        assistant_msg = json.loads(lines[1])
        assert assistant_msg["role"] == "assistant"
        assert "rate-limiting" in assistant_msg["content"].lower()
    
    def test_manifest_updated_with_new_open_effort(self, tmp_path):
        """The new effort is marked as 'open' in the manifest"""
        # Arrange
        from oi.models import ConversationState, Artifact
        from oi.efforts import start_new_effort
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Initial manifest with concluded effort
        manifest_path = session_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed auth",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))
        
        state = ConversationState(
            artifacts=[
                Artifact(
                    id="auth-bug",
                    artifact_type="effort",
                    summary="Fixed auth",
                    status="resolved"
                )
            ]
        )
        
        # Act
        start_new_effort(
            state=state,
            session_dir=session_dir,
            user_message="Let's work on database-indexing",
            assistant_response="Opening effort: database-indexing"
        )
        
        # Assert
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        efforts = updated_manifest.get("efforts", [])
        
        # Should have 2 efforts
        assert len(efforts) == 2
        
        # Find the new one
        new_effort = next(e for e in efforts if e["id"] == "database-indexing")
        assert new_effort["status"] == "open"
        assert "efforts/database-indexing.jsonl" == new_effort["raw_file"]
    
    def test_context_includes_ambient_summaries_and_new_effort_raw(self, tmp_path):
        """The context includes: ambient + all summaries (including the just-concluded effort) + new effort's raw log"""
        # Arrange
        from oi.models import ConversationState, Artifact
        from oi.context import build_turn_context  # New function, ImportError = red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # Create ambient raw.jsonl
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}),
            json.dumps({"role": "user", "content": "Quick question - what's the weather?"}),
            json.dumps({"role": "assistant", "content": "72°F and sunny."})
        ]) + '\n')
        
        # Create concluded effort log
        concluded_log = efforts_dir / "auth-bug.jsonl"
        concluded_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}),
            json.dumps({"role": "user", "content": "I implemented the interceptor"}),
            json.dumps({"role": "assistant", "content": "Concluding effort: auth-bug"})
        ]) + '\n')
        
        # Create new effort log
        new_log = efforts_dir / "guild-feature.jsonl"
        new_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's work on guild-feature"}),
            json.dumps({"role": "assistant", "content": "Opening effort: guild-feature"})
        ]) + '\n')
        
        # Create manifest with both efforts
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Fixed by adding axios interceptor.",
                    "raw_file": "efforts/auth-bug.jsonl"
                },
                {
                    "id": "guild-feature",
                    "status": "open",
                    "raw_file": "efforts/guild-feature.jsonl"
                }
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest_data))
        
        # Create state with both artifacts
        state = ConversationState(
            artifacts=[
                Artifact(
                    id="auth-bug",
                    artifact_type="effort",
                    summary="Debugged 401 errors",
                    status="resolved",
                    resolution="Added axios interceptor"
                ),
                Artifact(
                    id="guild-feature",
                    artifact_type="effort",
                    summary="guild-feature",
                    status="open"
                )
            ]
        )
        
        # Act
        context = build_turn_context(state, session_dir)
        
        # Assert
        # Should include ambient content
        assert "how's it going" in context
        assert "weather" in context
        
        # Should include concluded effort summary (not raw)
        assert "401 errors" in context
        assert "axios interceptor" in context
        # Should NOT include raw concluded effort messages
        assert "Let's debug the auth bug" not in context
        assert "Opening effort: auth-bug" not in context
        
        # Should include NEW effort raw messages
        assert "Let's work on guild-feature" in context
        assert "Opening effort: guild-feature" in context