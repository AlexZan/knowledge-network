"""Tests for Story 6: Remove Concluded Effort from Active Context"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestStory6RemoveConcludedEffortFromActiveContext:
    """Story 6: Remove Concluded Effort from Active Context"""

    def test_concluded_effort_raw_log_not_in_context(self, tmp_path):
        """After an effort is concluded, its raw log is no longer included in the context for subsequent turns"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: Create a concluded effort with raw log
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "debug auth"}) + "\n" +
            json.dumps({"role": "assistant", "content": "check token TTL"}) + "\n"
        )

        # Create manifest with concluded effort
        manifest_path = tmp_path / "manifest.yaml"
        manifest_content = """efforts:
  - id: auth-bug
    status: concluded
    summary: "Debugged 401 errors"
    created: "2024-01-01T00:00:00"
    updated: "2024-01-01T00:00:00"
"""
        manifest_path.write_text(manifest_content)

        # State has concluded artifact
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Debugged 401 errors", status="resolved")
        ])

        # Act: Build context
        context = build_turn_context(state, tmp_path)

        # Assert: Raw log content NOT in context
        assert "debug auth" not in context
        assert "check token TTL" not in context

    def test_concluded_effort_summary_in_context(self, tmp_path):
        """Only the summary of the concluded effort (from the manifest) is included in the context"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: Create concluded effort with summary
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "debug auth"}) + "\n"
        )

        manifest_path = tmp_path / "manifest.yaml"
        manifest_content = """efforts:
  - id: auth-bug
    status: concluded
    summary: "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor."
    created: "2024-01-01T00:00:00"
    updated: "2024-01-01T00:00:00"
"""
        manifest_path.write_text(manifest_content)

        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Debugged 401 errors", status="resolved")
        ])

        # Act
        context = build_turn_context(state, tmp_path)

        # Assert: Summary IS in context
        assert "Debugged 401 errors after 1 hour" in context
        assert "refresh tokens never auto-called" in context
        assert "axios interceptor" in context

    def test_concluded_effort_raw_log_preserved_on_disk(self, tmp_path):
        """The raw log file for the concluded effort is preserved on disk for potential future reference"""
        from oi.storage import conclude_effort
        from oi.models import ConversationState, Artifact

        # Arrange: Create an open effort with raw log
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        original_content = (
            json.dumps({"role": "user", "content": "debug auth"}) + "\n" +
            json.dumps({"role": "assistant", "content": "check token TTL"}) + "\n"
        )
        effort_log.write_text(original_content)

        manifest_path = tmp_path / "manifest.yaml"
        manifest_content = """efforts:
  - id: auth-bug
    status: open
    summary: "Debugging auth"
    created: "2024-01-01T00:00:00"
    updated: "2024-01-01T00:00:00"
"""
        manifest_path.write_text(manifest_content)

        # Act: Conclude the effort
        conclude_effort("auth-bug", tmp_path, "Debugged 401 errors after 1 hour")

        # Assert: Raw log file still exists with original content
        assert effort_log.exists()
        assert effort_log.read_text() == original_content

    def test_context_includes_open_effort_raw_but_not_concluded(self, tmp_path):
        """Context includes raw logs for open efforts but only summaries for concluded efforts"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: One open effort, one concluded effort
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()

        # Open effort raw log
        open_log = efforts_dir / "guild-feature.jsonl"
        open_log.write_text(
            json.dumps({"role": "user", "content": "add member limit"}) + "\n" +
            json.dumps({"role": "assistant", "content": "what max limit?"}) + "\n"
        )

        # Concluded effort raw log
        concluded_log = efforts_dir / "auth-bug.jsonl"
        concluded_log.write_text(
            json.dumps({"role": "user", "content": "debug auth"}) + "\n" +
            json.dumps({"role": "assistant", "content": "check token TTL"}) + "\n"
        )

        # Manifest with both
        manifest_path = tmp_path / "manifest.yaml"
        manifest_content = """efforts:
  - id: auth-bug
    status: concluded
    summary: "Debugged 401 errors"
    created: "2024-01-01T00:00:00"
    updated: "2024-01-01T00:00:00"
  - id: guild-feature
    status: open
    summary: "Add member limit to guilds"
    created: "2024-01-01T00:00:00"
    updated: "2024-01-01T00:00:00"
"""
        manifest_path.write_text(manifest_content)

        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Debugged 401 errors", status="resolved"),
            Artifact(id="guild-feature", artifact_type="effort", summary="Add member limit to guilds", status="open")
        ])

        # Act
        context = build_turn_context(state, tmp_path)

        # Assert: Open effort raw content IS in context
        assert "add member limit" in context
        assert "what max limit?" in context

        # Assert: Concluded effort raw content NOT in context
        assert "debug auth" not in context
        assert "check token TTL" not in context

        # Assert: Concluded effort summary IS in context
        assert "Debugged 401 errors" in context