"""Tests for Story 7: Assemble Context from Multiple Sources"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestStory7AssembleContextFromMultipleSources:
    """Story 7: Assemble Context from Multiple Sources"""

    def test_context_includes_ambient_messages(self, tmp_path):
        """Context includes all ambient messages from raw.jsonl"""
        # Arrange
        from oi.context import build_context
        from oi.models import ConversationState
        from oi.storage import save_state, load_state

        # Create raw.jsonl with ambient messages
        raw_path = tmp_path / "raw.jsonl"
        raw_path.write_text("""{"role": "user", "content": "Hey, how's it going?"}
{"role": "assistant", "content": "Good! Ready to help."}
{"role": "user", "content": "Quick question - weather?"}
{"role": "assistant", "content": "72°F and sunny."}
""")

        # Create manifest.yaml with concluded effort
        manifest_path = tmp_path / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour."
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Create state directory structure
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        (state_dir / "raw.jsonl").write_text(raw_path.read_text())
        (state_dir / "manifest.yaml").write_text(manifest_path.read_text())

        # Create a concluded effort file (should NOT be in context)
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text("""{"role": "user", "content": "Let's debug auth"}
{"role": "assistant", "content": "Opening effort: auth-bug"}
""")

        # Create state object
        state = ConversationState()
        # Will fail - ConversationState doesn't have these attributes yet
        # This is correct for TDD red phase

        # Act
        context = build_context(state, recent_messages=[])

        # Assert: ambient messages should be in context
        # Since build_context doesn't exist with this signature, this will fail
        # But we assert the expected behavior
        assert "Hey, how's it going?" in context
        assert "Good! Ready to help." in context
        assert "Quick question - weather?" in context
        assert "72°F and sunny." in context

    def test_context_includes_effort_summaries_from_manifest(self, tmp_path):
        """Context includes all effort summaries from manifest.yaml"""
        # Arrange
        from oi.context import build_context
        from oi.models import ConversationState
        from oi.storage import save_state, load_state

        # Create raw.jsonl with minimal ambient
        raw_path = tmp_path / "raw.jsonl"
        raw_path.write_text("""{"role": "user", "content": "Hi"}
{"role": "assistant", "content": "Hello"}
""")

        # Create manifest.yaml with multiple concluded efforts
        manifest_path = tmp_path / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called."
                },
                {
                    "id": "payment-fix",
                    "status": "concluded",
                    "summary": "Fixed Stripe webhook verification. Added signature validation."
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Create state directory
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        (state_dir / "raw.jsonl").write_text(raw_path.read_text())
        (state_dir / "manifest.yaml").write_text(manifest_path.read_text())

        # Create concluded effort files (should NOT have raw logs in context)
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text("raw log for auth-bug")
        (efforts_dir / "payment-fix.jsonl").write_text("raw log for payment-fix")

        state = ConversationState()

        # Act
        context = build_context(state, recent_messages=[])

        # Assert: effort summaries should be in context
        assert "Debugged 401 errors after 1 hour" in context
        assert "Root cause: refresh tokens never auto-called" in context
        assert "Fixed Stripe webhook verification" in context
        assert "Added signature validation" in context

    def test_context_includes_full_raw_logs_of_open_efforts(self, tmp_path):
        """Context includes full raw logs of all open efforts"""
        # Arrange
        from oi.context import build_context
        from oi.models import ConversationState
        from oi.storage import save_state, load_state

        # Create raw.jsonl with ambient
        raw_path = tmp_path / "raw.jsonl"
        raw_path.write_text("""{"role": "user", "content": "Ambient message"}
{"role": "assistant", "content": "Ambient reply"}
""")

        # Create manifest.yaml with one open effort
        manifest_path = tmp_path / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "guild-feature",
                    "status": "open"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Create state directory
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        (state_dir / "raw.jsonl").write_text(raw_path.read_text())
        (state_dir / "manifest.yaml").write_text(manifest_path.read_text())

        # Create open effort file with detailed conversation
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        open_effort_path = efforts_dir / "guild-feature.jsonl"
        open_effort_path.write_text("""{"role": "user", "content": "Let's work on guild feature - add member limit"}
{"role": "assistant", "content": "Opening effort: guild-feature. What's the max limit?"}
{"role": "user", "content": "I'm thinking 100 members max"}
{"role": "assistant", "content": "100 sounds reasonable. Should it be configurable?"}
{"role": "user", "content": "Yes, per guild configuration with default 100"}
""")

        state = ConversationState()

        # Act
        context = build_context(state, recent_messages=[])

        # Assert: open effort's full raw log should be in context
        assert "Let's work on guild feature - add member limit" in context
        assert "Opening effort: guild-feature" in context
        assert "What's the max limit?" in context
        assert "I'm thinking 100 members max" in context
        assert "100 sounds reasonable" in context
        assert "Should it be configurable?" in context
        assert "Yes, per guild configuration with default 100" in context

    def test_context_excludes_raw_logs_of_concluded_efforts(self, tmp_path):
        """Context does NOT include raw logs of concluded efforts"""
        # Arrange
        from oi.context import build_context
        from oi.models import ConversationState
        from oi.storage import save_state, load_state

        # Create raw.jsonl
        raw_path = tmp_path / "raw.jsonl"
        raw_path.write_text("""{"role": "user", "content": "Ambient"}
{"role": "assistant", "content": "Reply"}
""")

        # Create manifest.yaml with concluded effort
        manifest_path = tmp_path / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors."
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Create state directory
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        (state_dir / "raw.jsonl").write_text(raw_path.read_text())
        (state_dir / "manifest.yaml").write_text(manifest_path.read_text())

        # Create concluded effort file with sensitive/verbose content
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        concluded_effort_path = efforts_dir / "auth-bug.jsonl"
        concluded_effort_path.write_text("""{"role": "user", "content": "DEBUG DETAILS: Let's debug the auth bug"}
{"role": "assistant", "content": "Here are 50 lines of detailed token analysis..."}
{"role": "user", "content": "More debug details about JWT headers..."}
{"role": "assistant", "content": "Even more verbose implementation details..."}
""")

        state = ConversationState()

        # Act
        context = build_context(state, recent_messages=[])

        # Assert: concluded effort's raw log should NOT be in context
        # Only the summary should be present
        assert "Debugged 401 errors." in context  # Summary is present
        assert "DEBUG DETAILS: Let's debug the auth bug" not in context  # Raw log excluded
        assert "Here are 50 lines of detailed token analysis" not in context
        assert "More debug details about JWT headers" not in context
        assert "Even more verbose implementation details" not in context

    def test_context_includes_ambient_summaries_and_new_effort_when_opening_new_after_concluding(self, tmp_path):
        """When opening new effort after concluding one, context includes: ambient + all summaries + new effort's raw log"""
        # Arrange
        from oi.context import build_context
        from oi.models import ConversationState
        from oi.storage import save_state, load_state

        # Create raw.jsonl with ambient messages
        raw_path = tmp_path / "raw.jsonl"
        raw_path.write_text("""{"role": "user", "content": "Hey there"}
{"role": "assistant", "content": "Hello!"}
{"role": "user", "content": "Quick weather check"}
{"role": "assistant", "content": "Sunny"}
""")

        # Create manifest.yaml with concluded effort AND new open effort
        manifest_path = tmp_path / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed token refresh issue with axios interceptor."
                },
                {
                    "id": "guild-feature",
                    "status": "open"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest_data))

        # Create state directory
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        (state_dir / "raw.jsonl").write_text(raw_path.read_text())
        (state_dir / "manifest.yaml").write_text(manifest_path.read_text())

        # Create effort files
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        
        # Concluded effort file (should NOT have raw in context)
        (efforts_dir / "auth-bug.jsonl").write_text("""{"role": "user", "content": "Old debug details"}
{"role": "assistant", "content": "Old verbose response"}
""")
        
        # New open effort file (SHOULD have raw in context)
        (efforts_dir / "guild-feature.jsonl").write_text("""{"role": "user", "content": "Now let's work on guild feature"}
{"role": "assistant", "content": "Opening effort: guild-feature. Member limits?"}
{"role": "user", "content": "Yes, need to add max members per guild"}
""")

        state = ConversationState()

        # Act
        context = build_context(state, recent_messages=[])

        # Assert 1: Ambient messages are present
        assert "Hey there" in context
        assert "Hello!" in context
        assert "Quick weather check" in context
        assert "Sunny" in context
        
        # Assert 2: Concluded effort summary is present
        assert "Fixed token refresh issue with axios interceptor" in context
        
        # Assert 3: New open effort's raw log is present
        assert "Now let's work on guild feature" in context
        assert "Opening effort: guild-feature" in context
        assert "Member limits?" in context
        assert "Yes, need to add max members per guild" in context
        
        # Assert 4: Old concluded effort's raw log is NOT present
        assert "Old debug details" not in context
        assert "Old verbose response" not in context

    def test_context_structure_matches_expected_format(self, tmp_path):
        """Context is assembled in the expected format (ambient + summaries + open efforts)"""
        # Arrange
        from oi.context import build_context
        from oi.models import ConversationState
        from oi.storage import save_state, load_state

        # Create test data
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Simple ambient
        (state_dir / "raw.jsonl").write_text("""{"role": "user", "content": "A1"}
{"role": "assistant", "content": "A2"}
""")
        
        # Manifest with mixed efforts
        manifest_data = {
            "efforts": [
                {"id": "done1", "status": "concluded", "summary": "Summary1"},
                {"id": "open1", "status": "open"},
                {"id": "done2", "status": "concluded", "summary": "Summary2"}
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest_data))
        
        # Effort files
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "done1.jsonl").write_text("Raw1 - should not be in context")
        (efforts_dir / "open1.jsonl").write_text("""{"role": "user", "content": "Open effort raw log"}
{"role": "assistant", "content": "This should be in context"}
""")
        (efforts_dir / "done2.jsonl").write_text("Raw2 - should not be in context")

        state = ConversationState()

        # Act
        context = build_context(state, recent_messages=[])

        # Assert: Verify all required parts are present
        # This test is more about the composition than exact string matching
        assert "A1" in context  # Ambient
        assert "A2" in context  # Ambient
        assert "Summary1" in context  # Concluded effort summary
        assert "Summary2" in context  # Concluded effort summary
        assert "Open effort raw log" in context  # Open effort raw
        assert "This should be in context" in context  # Open effort raw
        
        # Assert: Verify excluded parts are NOT present
        assert "Raw1 - should not be in context" not in context
        assert "Raw2 - should not be in context" not in context
        
        # Optional: Assert on structure markers if they exist in implementation
        # This depends on how build_context formats the output
        # For now, just verify the content inclusion/exclusion

    def test_build_context_uses_state_dir_from_conversation_state(self, tmp_path):
        """build_context reads from the state directory specified in ConversationState"""
        # Arrange
        from oi.context import build_context
        from oi.models import ConversationState
        from oi.storage import save_state, load_state

        # Create a mock state with state_dir attribute
        state = ConversationState()
        # Will fail - ConversationState doesn't have state_dir yet
        # This is correct for TDD
        
        state_dir = tmp_path / "test_session"
        state_dir.mkdir()
        
        # Create test files
        (state_dir / "raw.jsonl").write_text("""{"role": "user", "content": "Test ambient"}""")
        (state_dir / "manifest.yaml").write_text(yaml.dump({
            "efforts": [{"id": "test", "status": "concluded", "summary": "Test summary"}]
        }))
        
        # Mock the state to have state_dir (this will be implemented later)
        # For now, the test will fail because state_dir doesn't exist on ConversationState
        # This is the correct TDD red phase
        
        # Act
        context = build_context(state, recent_messages=[])
        
        # Assert: The context should include content from state_dir
        # This will fail because build_context doesn't read from state_dir yet
        assert "Test ambient" in context
        assert "Test summary" in context