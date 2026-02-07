"""Tests for Story 5: Explicitly Conclude an Effort"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestStory5ExplicitlyConcludeEffort:
    """Story 5: Explicitly Conclude an Effort"""

    def test_user_says_x_is_done_triggers_conclusion(self, tmp_path):
        """When I say 'X is done' about an open effort, the assistant creates a summary of the effort"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        # Create a state with an open effort
        state = ConversationState()
        # The state should have an open effort named "auth-bug"
        # This will fail because ConversationState doesn't have open efforts yet
        # That's correct for TDD red phase

        # Create manifest.yaml with open effort
        manifest = {
            "efforts": [
                {"id": "auth-bug", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        # Create effort raw log
        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        (effort_dir / "auth-bug.jsonl").write_text(json.dumps({"role": "user", "content": "Let's debug auth"}) + "\n")

        # Save state
        save_state(state, state_dir)

        # Mock the LLM to return a summary
        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = "Summary: Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor."

            # Act
            # This will fail because process_turn doesn't handle effort conclusion yet
            result_state = process_turn(state, "auth-bug is done", "gpt-4", state_dir)

        # Assert
        # Load manifest to check effort status changed
        manifest_after = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        auth_effort = next(e for e in manifest_after["efforts"] if e["id"] == "auth-bug")
        assert auth_effort["status"] == "concluded"
        assert "summary" in auth_effort
        assert "Debugged 401 errors" in auth_effort["summary"]

    def test_user_says_looks_good_triggers_conclusion(self, tmp_path):
        """When I say 'looks good' about an open effort, the assistant creates a summary of the effort"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        # Create a state with an open effort
        state = ConversationState()

        # Create manifest.yaml with open effort
        manifest = {
            "efforts": [
                {"id": "payment-fix", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        # Create effort raw log
        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        (effort_dir / "payment-fix.jsonl").write_text(json.dumps({"role": "user", "content": "Let's fix payments"}) + "\n")

        save_state(state, state_dir)

        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = "Summary: Fixed payment processing bug. Issue was currency conversion rounding."

            # Act
            result_state = process_turn(state, "payment-fix looks good", "gpt-4", state_dir)

        # Assert
        manifest_after = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        payment_effort = next(e for e in manifest_after["efforts"] if e["id"] == "payment-fix")
        assert payment_effort["status"] == "concluded"
        assert "summary" in payment_effort
        assert "currency conversion" in payment_effort["summary"]

    def test_assistant_confirms_effort_concluded_by_name(self, tmp_path):
        """The assistant confirms the effort has been concluded by name"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        state = ConversationState()

        manifest = {
            "efforts": [
                {"id": "ui-redesign", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        (effort_dir / "ui-redesign.jsonl").write_text(json.dumps({"role": "user", "content": "Redesign UI"}) + "\n")

        save_state(state, state_dir)

        with patch("oi.conversation.chat") as mock_chat:
            # Mock chat to return a response that includes the effort name
            mock_chat.return_value = "Concluding effort: ui-redesign\n\nSummary: Redesigned user interface with new component library."

            # Act
            result_state = process_turn(state, "ui-redesign is done", "gpt-4", state_dir)

            # Get the assistant's response from the chatlog
            from oi.chatlog import read_recent
            recent = read_recent(1, state_dir)
            assistant_response = recent[0]["content"] if recent else ""

        # Assert the response contains the effort name
        assert "ui-redesign" in assistant_response.lower()
        assert "concluding" in assistant_response.lower() or "concluded" in assistant_response.lower()

    def test_effort_status_changes_from_open_to_concluded_in_manifest(self, tmp_path):
        """The effort's status in the manifest changes from 'open' to 'concluded'"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        state = ConversationState()

        # Start with open effort
        manifest = {
            "efforts": [
                {"id": "database-migration", "status": "open", "created_at": "2024-01-01T00:00:00Z"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        (effort_dir / "database-migration.jsonl").write_text(json.dumps({"role": "user", "content": "Migrate DB"}) + "\n")

        save_state(state, state_dir)

        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = "Summary: Migrated database from MySQL to PostgreSQL."

            # Act
            result_state = process_turn(state, "database-migration is complete", "gpt-4", state_dir)

        # Assert
        manifest_after = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        effort = manifest_after["efforts"][0]
        assert effort["status"] == "concluded"
        assert effort["id"] == "database-migration"
        # Original fields should be preserved
        assert effort["created_at"] == "2024-01-01T00:00:00Z"

    def test_summary_is_added_to_manifest(self, tmp_path):
        """The summary is added to the manifest"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        state = ConversationState()

        manifest = {
            "efforts": [
                {"id": "api-security", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        (effort_dir / "api-security.jsonl").write_text(json.dumps({"role": "user", "content": "Secure API"}) + "\n")

        save_state(state, state_dir)

        expected_summary = "Summary: Implemented API security with JWT tokens and rate limiting."

        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = expected_summary

            # Act
            result_state = process_turn(state, "api-security looks good", "gpt-4", state_dir)

        # Assert
        manifest_after = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        effort = manifest_after["efforts"][0]
        assert "summary" in effort
        assert effort["summary"] == expected_summary
        # Check that summary is a string field
        assert isinstance(effort["summary"], str)
        assert len(effort["summary"]) > 0

    def test_concluding_message_and_confirmation_saved_to_effort_raw_log(self, tmp_path):
        """My concluding message and the assistant's confirmation are saved to the effort's raw log"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state
        from oi.chatlog import read_recent

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        state = ConversationState()

        manifest = {
            "efforts": [
                {"id": "performance-optimization", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        effort_log = effort_dir / "performance-optimization.jsonl"
        # Start with some existing messages
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's optimize performance"}) + "\n" +
            json.dumps({"role": "assistant", "content": "What metrics are slow?"}) + "\n"
        )

        save_state(state, state_dir)

        user_concluding_message = "performance-optimization is done, all tests pass"
        assistant_confirmation = "Concluding effort: performance-optimization\n\nSummary: Optimized database queries and added caching."

        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = assistant_confirmation

            # Act
            result_state = process_turn(state, user_concluding_message, "gpt-4", state_dir)

        # Assert
        # Read the effort log
        with open(effort_log) as f:
            lines = f.readlines()
            messages = [json.loads(line) for line in lines]

        # Should have original messages plus concluding exchange
        assert len(messages) >= 4

        # Last two messages should be user concluding and assistant confirmation
        last_user = messages[-2]
        last_assistant = messages[-1]

        assert last_user["role"] == "user"
        assert user_concluding_message in last_user["content"]

        assert last_assistant["role"] == "assistant"
        assert "performance-optimization" in last_assistant["content"].lower()
        assert "concluding" in last_assistant["content"].lower() or "concluded" in last_assistant["content"].lower()

    def test_only_concludes_specific_effort_when_multiple_open(self, tmp_path):
        """When multiple efforts are open, only concludes the one mentioned"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        state = ConversationState()

        manifest = {
            "efforts": [
                {"id": "effort-a", "status": "open"},
                {"id": "effort-b", "status": "open"},
                {"id": "effort-c", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        for effort_id in ["effort-a", "effort-b", "effort-c"]:
            (effort_dir / f"{effort_id}.jsonl").write_text(json.dumps({"role": "user", "content": f"Start {effort_id}"}) + "\n")

        save_state(state, state_dir)

        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = "Summary: Completed effort-b work."

            # Act
            result_state = process_turn(state, "effort-b is done", "gpt-4", state_dir)

        # Assert
        manifest_after = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        
        # Find each effort
        effort_a = next(e for e in manifest_after["efforts"] if e["id"] == "effort-a")
        effort_b = next(e for e in manifest_after["efforts"] if e["id"] == "effort-b")
        effort_c = next(e for e in manifest_after["efforts"] if e["id"] == "effort-c")

        # Only effort-b should be concluded
        assert effort_a["status"] == "open"
        assert effort_b["status"] == "concluded"
        assert "summary" in effort_b
        assert effort_c["status"] == "open"

    def test_concluding_effort_does_not_affect_ambient_chatlog(self, tmp_path):
        """Concluding an effort doesn't modify the ambient raw.jsonl"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state
        from oi.chatlog import read_recent

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        state = ConversationState()

        # Create ambient chatlog with some messages
        raw_log = state_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hello"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Hi there!"}) + "\n"
        )

        manifest = {
            "efforts": [
                {"id": "test-effort", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        (effort_dir / "test-effort.jsonl").write_text(json.dumps({"role": "user", "content": "Start test"}) + "\n")

        save_state(state, state_dir)

        # Record ambient log before conclusion
        with open(raw_log) as f:
            ambient_before = f.read()

        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = "Summary: Test effort completed."

            # Act
            result_state = process_turn(state, "test-effort is done", "gpt-4", state_dir)

        # Assert ambient log unchanged
        with open(raw_log) as f:
            ambient_after = f.read()

        assert ambient_after == ambient_before
        # The concluding exchange should NOT be in ambient log
        assert "test-effort is done" not in ambient_after
        assert "Summary: Test effort completed" not in ambient_after

    def test_concluded_effort_has_raw_file_reference_in_manifest(self, tmp_path):
        """Concluded effort manifest entry includes reference to raw log file"""
        # Arrange
        from oi.conversation import process_turn
        from oi.models import ConversationState
        from oi.storage import load_state, save_state

        state_dir = tmp_path / "session"
        state_dir.mkdir()

        state = ConversationState()

        manifest = {
            "efforts": [
                {"id": "logical-effort", "status": "open"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        effort_dir = state_dir / "efforts"
        effort_dir.mkdir()
        effort_file = effort_dir / "logical-effort.jsonl"
        effort_file.write_text(json.dumps({"role": "user", "content": "Logical start"}) + "\n")

        save_state(state, state_dir)

        with patch("oi.conversation.chat") as mock_chat:
            mock_chat.return_value = "Summary: Logical work done."

            # Act
            result_state = process_turn(state, "logical-effort looks good", "gpt-4", state_dir)

        # Assert
        manifest_after = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        effort = manifest_after["efforts"][0]
        
        assert effort["status"] == "concluded"
        assert "raw_file" in effort
        # Should reference the effort's raw log file
        assert effort["raw_file"] == "efforts/logical-effort.jsonl"
        # File should still exist
        assert (state_dir / effort["raw_file"]).exists()