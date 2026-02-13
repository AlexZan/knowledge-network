"""Tests for Story 7: Assemble Context from Multiple Sources"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock


class TestStory7AssembleContext:
    """Story 7: Assemble Context from Multiple Sources"""

    def test_build_turn_context_includes_ambient_raw_jsonl(self, tmp_path):
        """The context for each turn includes all ambient messages (raw.jsonl)"""
        from oi.context import build_turn_context
        from oi.models import ConversationState

        # Arrange
        raw_log = tmp_path / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )
        state = ConversationState(artifacts=[])

        # Act
        context = build_turn_context(state, tmp_path)

        # Assert
        assert "Hey, how's it going?" in context
        assert "Good! Ready to help." in context

    def test_build_turn_context_includes_effort_summaries_from_manifest(self, tmp_path):
        """The context for each turn includes all effort summaries (from manifest.yaml)"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange
        manifest_path = tmp_path / "manifest.yaml"
        manifest_content = """efforts:
  - id: auth-bug
    status: concluded
    summary: Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called.
  - id: guild-feature
    status: open
    summary: Adding member limit to guilds."""
        manifest_path.write_text(manifest_content)

        # Mock yaml.safe_load to return parsed manifest
        with patch('yaml.safe_load') as mock_yaml_load:
            mock_yaml_load.return_value = {
                "efforts": [
                    {"id": "auth-bug", "status": "concluded", "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called."},
                    {"id": "guild-feature", "status": "open", "summary": "Adding member limit to guilds."}
                ]
            }
            state = ConversationState(artifacts=[])
            # Act
            context = build_turn_context(state, tmp_path)

        # Assert
        assert "auth-bug" in context
        assert "Debugged 401 errors after 1 hour" in context
        assert "guild-feature" in context
        assert "Adding member limit to guilds" in context

    def test_build_turn_context_includes_full_raw_logs_of_open_efforts(self, tmp_path):
        """The context for each turn includes the full raw logs of all open efforts"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()

        # Create an open effort log
        open_effort_log = efforts_dir / "guild-feature.jsonl"
        open_effort_log.write_text(
            json.dumps({"role": "user", "content": "Now let's work on the guild feature - I want to add a member limit"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: guild-feature. For member limits, a few questions:"}) + "\n"
        )

        # Create a concluded effort log (should NOT be included in full raw)
        concluded_effort_log = efforts_dir / "auth-bug.jsonl"
        concluded_effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n"
        )

        # Mock manifest to have one open and one concluded effort
        with patch('yaml.safe_load') as mock_yaml_load:
            mock_yaml_load.return_value = {
                "efforts": [
                    {"id": "auth-bug", "status": "concluded", "summary": "Debugged auth"},
                    {"id": "guild-feature", "status": "open", "summary": "Adding member limit"}
                ]
            }
            state = ConversationState(artifacts=[])
            # Act
            context = build_turn_context(state, tmp_path)

        # Assert
        assert "Now let's work on the guild feature" in context
        assert "Opening effort: guild-feature" in context
        # Concluded effort raw log should NOT be in context (only summary)
        assert "Let's debug the auth bug" not in context
        assert "Opening effort: auth-bug" not in context

    def test_build_turn_context_combines_all_sources(self, tmp_path):
        """The context includes ambient messages, effort summaries, and open effort raw logs combined"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange
        # 1. Ambient raw.jsonl
        raw_log = tmp_path / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )

        # 2. Efforts directory with open effort
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        open_effort_log = efforts_dir / "guild-feature.jsonl"
        open_effort_log.write_text(
            json.dumps({"role": "user", "content": "Now let's work on the guild feature"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: guild-feature"}) + "\n"
        )

        # 3. Mock manifest with open and concluded efforts
        with patch('yaml.safe_load') as mock_yaml_load:
            mock_yaml_load.return_value = {
                "efforts": [
                    {"id": "auth-bug", "status": "concluded", "summary": "Debugged 401 errors"},
                    {"id": "guild-feature", "status": "open", "summary": "Adding member limit"}
                ]
            }
            state = ConversationState(artifacts=[])
            # Act
            context = build_turn_context(state, tmp_path)

        # Assert - all three sources should be present
        assert "Hey, how's it going?" in context  # Ambient
        assert "Good! Ready to help." in context  # Ambient
        assert "Debugged 401 errors" in context  # Concluded effort summary
        assert "Adding member limit" in context  # Open effort summary
        assert "Now let's work on the guild feature" in context  # Open effort raw log
        assert "Opening effort: guild-feature" in context  # Open effort raw log

    def test_build_turn_context_handles_missing_manifest_gracefully(self, tmp_path):
        """Context assembly works when manifest.yaml doesn't exist"""
        from oi.context import build_turn_context
        from oi.models import ConversationState

        # Arrange - no manifest.yaml file
        raw_log = tmp_path / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hello"}) + "\n"
        )
        state = ConversationState(artifacts=[])

        # Act
        context = build_turn_context(state, tmp_path)

        # Assert - should still include ambient messages
        assert "Hello" in context
        # Should not crash due to missing manifest

    def test_build_turn_context_handles_missing_efforts_directory_gracefully(self, tmp_path):
        """Context assembly works when efforts directory doesn't exist"""
        from oi.context import build_turn_context
        from oi.models import ConversationState

        # Arrange - no efforts directory
        raw_log = tmp_path / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hello"}) + "\n"
        )
        # Mock manifest with open effort but no corresponding file
        with patch('yaml.safe_load') as mock_yaml_load:
            mock_yaml_load.return_value = {
                "efforts": [
                    {"id": "some-effort", "status": "open", "summary": "Test effort"}
                ]
            }
            state = ConversationState(artifacts=[])
            # Act
            context = build_turn_context(state, tmp_path)

        # Assert - should include ambient and summary, skip missing raw log
        assert "Hello" in context
        assert "Test effort" in context
        # Should not crash due to missing efforts directory

    def test_build_turn_context_only_includes_open_effort_raw_logs(self, tmp_path):
        """Only open efforts have their full raw logs included; concluded efforts only show summaries"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()

        # Open effort log
        open_log = efforts_dir / "open-effort.jsonl"
        open_log.write_text(
            json.dumps({"role": "user", "content": "This is open effort raw content"}) + "\n"
        )

        # Concluded effort log
        concluded_log = efforts_dir / "concluded-effort.jsonl"
        concluded_log.write_text(
            json.dumps({"role": "user", "content": "This is concluded effort raw content"}) + "\n"
        )

        # Mock manifest
        with patch('yaml.safe_load') as mock_yaml_load:
            mock_yaml_load.return_value = {
                "efforts": [
                    {"id": "open-effort", "status": "open", "summary": "Open effort summary"},
                    {"id": "concluded-effort", "status": "concluded", "summary": "Concluded effort summary"}
                ]
            }
            state = ConversationState(artifacts=[])
            # Act
            context = build_turn_context(state, tmp_path)

        # Assert
        assert "This is open effort raw content" in context  # Raw log included
        assert "Open effort summary" in context  # Summary included
        assert "Concluded effort summary" in context  # Summary included
        assert "This is concluded effort raw content" not in context  # Raw log NOT included