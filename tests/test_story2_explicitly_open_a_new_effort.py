"""Tests for Story 2: Explicitly Open a New Effort"""

import json
import yaml
import pytest
from pathlib import Path


class TestStory2ExplicitlyOpenNewEffort:
    """Story 2: Explicitly Open a New Effort"""

    def test_effort_opening_detected_from_user_message(self):
        """When user says 'Let's work on X', extract effort name"""
        # Arrange
        from oi.detection import extract_effort_opening  # Will fail - doesn't exist yet

        # Act
        result = extract_effort_opening("Let's work on auth-bug - users are getting 401s")

        # Assert
        assert result == "auth-bug"

    def test_effort_opening_detected_from_variations(self):
        """When user says similar phrases, extract effort name"""
        # Arrange
        from oi.detection import extract_effort_opening

        # Act & Assert
        assert extract_effort_opening("I want to work on payment integration") == "payment integration"
        assert extract_effort_opening("Let's debug the login issue") == "login issue"
        assert extract_effort_opening("Can we work on the guild feature?") == "guild feature"

    def test_new_effort_file_created_in_efforts_directory(self, tmp_path):
        """When opening new effort, create file efforts/X.jsonl"""
        # Arrange
        from oi.efforts import open_new_effort  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Act
        open_new_effort(session_dir, "auth-bug", "Let's debug the auth bug")

        # Assert
        effort_file = session_dir / "efforts" / "auth-bug.jsonl"
        assert effort_file.exists()
        assert effort_file.is_file()

    def test_effort_marked_open_in_manifest_yaml(self, tmp_path):
        """When opening new effort, manifest.yaml gets entry with status: open"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Act
        open_new_effort(session_dir, "auth-bug", "Let's debug the auth bug")

        # Assert
        manifest_path = session_dir / "manifest.yaml"
        assert manifest_path.exists()

        manifest = yaml.safe_load(manifest_path.read_text())
        assert "efforts" in manifest

        effort_entry = next((e for e in manifest["efforts"] if e["id"] == "auth-bug"), None)
        assert effort_entry is not None
        assert effort_entry["status"] == "open"
        assert "created" in effort_entry
        assert "updated" in effort_entry

    def test_opening_message_saved_to_effort_log(self, tmp_path):
        """User's opening message saved to new effort's JSONL log"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        user_message = "Let's debug the auth bug - users are getting 401s after about an hour"

        # Act
        open_new_effort(session_dir, "auth-bug", user_message)

        # Assert
        effort_file = session_dir / "efforts" / "auth-bug.jsonl"
        lines = effort_file.read_text().strip().split('\n')
        assert len(lines) == 1

        saved_message = json.loads(lines[0])
        assert saved_message["role"] == "user"
        assert saved_message["content"] == user_message
        assert "timestamp" in saved_message

    def test_assistant_confirmation_included_in_effort_log(self, tmp_path):
        """Assistant's confirmation message saved to effort log after user message"""
        # Arrange
        from oi.efforts import add_assistant_confirmation_to_effort  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()

        # Create initial effort file with user message
        effort_file = efforts_dir / "auth-bug.jsonl"
        effort_file.write_text(json.dumps({
            "role": "user",
            "content": "Let's debug the auth bug",
            "timestamp": "2024-01-01T00:00:00"
        }) + "\n")

        # Act
        add_assistant_confirmation_to_effort(session_dir, "auth-bug", "Opening effort: auth-bug")

        # Assert
        lines = effort_file.read_text().strip().split('\n')
        assert len(lines) == 2

        saved_message = json.loads(lines[1])
        assert saved_message["role"] == "assistant"
        assert "auth-bug" in saved_message["content"]
        assert "Opening" in saved_message["content"]
        assert "timestamp" in saved_message

    def test_manifest_preserves_existing_efforts_when_adding_new(self, tmp_path):
        """When adding new effort, existing efforts in manifest are preserved"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create manifest with existing effort
        manifest_path = session_dir / "manifest.yaml"
        manifest_data = {
            "ambient_messages": [],
            "efforts": [
                {"id": "old-effort", "status": "concluded", "created": "2024-01-01", "updated": "2024-01-01"}
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Act
        open_new_effort(session_dir, "auth-bug", "Let's debug")

        # Assert
        manifest = yaml.safe_load(manifest_path.read_text())
        effort_ids = [e["id"] for e in manifest["efforts"]]
        assert "old-effort" in effort_ids
        assert "auth-bug" in effort_ids
        assert len(manifest["efforts"]) == 2

    def test_duplicate_effort_id_updates_existing_entry(self, tmp_path):
        """When opening effort with existing ID, update manifest entry instead of creating duplicate"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create manifest with existing effort (resolved)
        manifest_path = session_dir / "manifest.yaml"
        manifest_data = {
            "ambient_messages": [],
            "efforts": [
                {"id": "auth-bug", "status": "resolved", "created": "2024-01-01", "updated": "2024-01-01"}
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Create existing effort file
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_file = efforts_dir / "auth-bug.jsonl"
        effort_file.write_text("existing content\n")

        # Act
        open_new_effort(session_dir, "auth-bug", "Let's debug auth again")

        # Assert
        manifest = yaml.safe_load(manifest_path.read_text())
        assert len(manifest["efforts"]) == 1
        effort = manifest["efforts"][0]
        assert effort["id"] == "auth-bug"
        assert effort["status"] == "open"  # Status updated from resolved to open
        assert effort["updated"] != "2024-01-01"  # Updated timestamp changed

        # Effort log should have new message appended
        lines = effort_file.read_text().strip().split('\n')
        assert len(lines) > 1  # At least original line + new message

    def test_effort_directory_created_if_not_exists(self, tmp_path):
        """efforts/ directory created if it doesn't exist when opening effort"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Act
        open_new_effort(session_dir, "auth-bug", "Let's debug")

        # Assert
        efforts_dir = session_dir / "efforts"
        assert efforts_dir.exists()
        assert efforts_dir.is_dir()

    def test_manifest_created_if_not_exists(self, tmp_path):
        """manifest.yaml created if it doesn't exist when opening effort"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Act
        open_new_effort(session_dir, "auth-bug", "Let's debug")

        # Assert
        manifest_path = session_dir / "manifest.yaml"
        assert manifest_path.exists()

        manifest = yaml.safe_load(manifest_path.read_text())
        assert "efforts" in manifest
        assert isinstance(manifest["efforts"], list)

    def test_parse_llm_response_for_effort_name(self):
        """When LLM response indicates effort opening, extract effort name from response"""
        # Arrange
        from oi.detection import extract_effort_name_from_llm_response  # New focused function

        # Act & Assert
        result = extract_effort_name_from_llm_response("I see you want to work on 'auth-bug'. Let me open that effort.")
        assert result == "auth-bug"

        result2 = extract_effort_name_from_llm_response("Opening effort 'payment integration' now.")
        assert result2 == "payment integration"

        result3 = extract_effort_name_from_llm_response("Let's work on the login issue together.")
        assert result3 == "login issue"

    def test_multiple_efforts_can_be_open_concurrently_in_manifest(self, tmp_path):
        """Manifest can contain multiple efforts with open status"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Act - open first effort
        open_new_effort(session_dir, "auth-bug", "Debug auth")

        # Open second effort
        open_new_effort(session_dir, "payment-feature", "Work on payments")

        # Assert
        manifest_path = session_dir / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text())

        open_efforts = [e for e in manifest["efforts"] if e["status"] == "open"]
        assert len(open_efforts) == 2

        effort_ids = [e["id"] for e in open_efforts]
        assert "auth-bug" in effort_ids
        assert "payment-feature" in effort_ids

    def test_effort_opening_does_not_affect_ambient_messages(self, tmp_path):
        """Opening effort doesn't modify ambient messages in manifest"""
        # Arrange
        from oi.efforts import open_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Create manifest with ambient messages
        manifest_path = session_dir / "manifest.yaml"
        manifest_data = {
            "ambient_messages": [
                {"role": "user", "content": "Hey, how's it going?", "timestamp": "2024-01-01T00:00:00"}
            ],
            "efforts": []
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Act
        open_new_effort(session_dir, "auth-bug", "Let's debug")

        # Assert
        manifest = yaml.safe_load(manifest_path.read_text())
        assert "ambient_messages" in manifest
        assert len(manifest["ambient_messages"]) == 1
        assert manifest["ambient_messages"][0]["content"] == "Hey, how's it going?"
