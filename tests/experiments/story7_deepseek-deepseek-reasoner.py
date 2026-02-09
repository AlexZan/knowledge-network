"""Tests for Story 7: Assemble Context from Multiple Sources"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, Mock


class TestStory7AssembleContext:
    """Story 7: Assemble Context from Multiple Sources"""

    def test_context_includes_ambient_effort_summaries_and_open_effort_raw_logs(self, tmp_path):
        """Context includes ambient messages, all effort summaries, and full raw logs of open efforts"""
        # Arrange: Create a session with ambient, concluded effort (summary only), and open effort (raw log)
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()

        # Create ambient messages (not in any effort)
        ambient_log = state_dir / "raw.jsonl"
        ambient_log.write_text('\n'.join([
            json.dumps({"turn": 1, "role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"turn": 2, "role": "assistant", "content": "Good! Ready to help."}),
            json.dumps({"turn": 11, "role": "user", "content": "Quick question - what's the weather in Seattle?"}),
            json.dumps({"turn": 12, "role": "assistant", "content": "72°F and sunny in Seattle today."})
        ]))

        # Create manifest with concluded and open efforts
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called.",
                    "raw_file": "efforts/auth-bug.jsonl"
                },
                {
                    "id": "guild-feature",
                    "status": "open"
                }
            ]
        }
        manifest_path = state_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))

        # Create concluded effort raw log (should NOT be in context)
        concluded_log = efforts_dir / "auth-bug.jsonl"
        concluded_log.write_text('\n'.join([
            json.dumps({"turn": 3, "role": "user", "content": "Let's debug the auth bug"}),
            json.dumps({"turn": 4, "role": "assistant", "content": "Opening effort: auth-bug"}),
            json.dumps({"turn": 13, "role": "user", "content": "Back to auth - I implemented the interceptor and it works."}),
            json.dumps({"turn": 14, "role": "assistant", "content": "Concluding effort: auth-bug"})
        ]))

        # Create open effort raw log (SHOULD be in context)
        open_log = efforts_dir / "guild-feature.jsonl"
        open_log.write_text('\n'.join([
            json.dumps({"turn": 15, "role": "user", "content": "Now let's work on the guild feature"}),
            json.dumps({"turn": 16, "role": "assistant", "content": "Opening effort: guild-feature"})
        ]))

        # Act: Load state and build context
        from oi.storage import load_state
        from oi.context import build_context

        state = load_state(state_dir)
        context = build_context(state, recent_messages=[])

        # Assert: Context includes all required components
        # Ambient messages
        assert "Hey, how's it going?" in context
        assert "72°F and sunny in Seattle today." in context
        
        # Concluded effort summary (but NOT raw log)
        assert "Debugged 401 errors after 1 hour" in context
        assert "auth-bug" in context  # Effort ID should be referenced
        # Raw log of concluded effort should NOT be in context
        assert "Let's debug the auth bug" not in context  # From raw log
        assert "Opening effort: auth-bug" not in context  # From raw log
        
        # Full raw log of open effort
        assert "Now let's work on the guild feature" in context
        assert "Opening effort: guild-feature" in context

    def test_context_excludes_raw_logs_of_concluded_efforts(self, tmp_path):
        """Context does NOT include the raw logs of concluded efforts"""
        # Arrange: Create a session with only concluded efforts
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()

        # Minimal ambient
        ambient_log = state_dir / "raw.jsonl"
        ambient_log.write_text(json.dumps({"turn": 1, "role": "user", "content": "test"}))

        # Manifest with only concluded efforts
        manifest = {
            "efforts": [
                {
                    "id": "effort1",
                    "status": "concluded",
                    "summary": "Summary 1",
                    "raw_file": "efforts/effort1.jsonl"
                },
                {
                    "id": "effort2",
                    "status": "concluded",
                    "summary": "Summary 2",
                    "raw_file": "efforts/effort2.jsonl"
                }
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        # Raw logs for concluded efforts
        (efforts_dir / "effort1.jsonl").write_text(
            json.dumps({"turn": 2, "role": "user", "content": "raw content 1 - SHOULD NOT BE IN CONTEXT"})
        )
        (efforts_dir / "effort2.jsonl").write_text(
            json.dumps({"turn": 3, "role": "user", "content": "raw content 2 - SHOULD NOT BE IN CONTEXT"})
        )

        # Act
        from oi.storage import load_state
        from oi.context import build_context

        state = load_state(state_dir)
        context = build_context(state, recent_messages=[])

        # Assert: Only summaries are in context, not raw logs
        assert "Summary 1" in context
        assert "Summary 2" in context
        assert "raw content 1 - SHOULD NOT BE IN CONTEXT" not in context
        assert "raw content 2 - SHOULD NOT BE IN CONTEXT" not in context

    def test_context_for_new_effort_after_concluding_one_includes_all_components(self, tmp_path):
        """When opening a new effort after concluding one, context includes: ambient + all summaries + new effort's raw log"""
        # Arrange: Simulate the exact scenario from the story
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()

        # Ambient only (turns 1-2, 11-12)
        ambient_log = state_dir / "raw.jsonl"
        ambient_log.write_text('\n'.join([
            json.dumps({"turn": 1, "role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"turn": 2, "role": "assistant", "content": "Good! Ready to help."}),
            json.dumps({"turn": 11, "role": "user", "content": "Quick weather question"}),
            json.dumps({"turn": 12, "role": "assistant", "content": "72°F and sunny"})
        ]))

        # Manifest with concluded auth-bug and open guild-feature
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause was refresh tokens never auto-called. Fixed by adding axios interceptor.",
                    "raw_file": "efforts/auth-bug.jsonl"
                },
                {
                    "id": "guild-feature",
                    "status": "open"
                }
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        # Concluded effort raw log (exists but not in context)
        (efforts_dir / "auth-bug.jsonl").write_text(
            json.dumps({"turn": 3, "role": "user", "content": "Let's debug the auth bug"}) + "\n" +
            json.dumps({"turn": 13, "role": "user", "content": "Back to auth - bug is fixed!"})
        )

        # New open effort raw log (in context)
        (efforts_dir / "guild-feature.jsonl").write_text(
            json.dumps({"turn": 15, "role": "user", "content": "Now let's work on the guild feature - I want to add a member limit"}) + "\n" +
            json.dumps({"turn": 16, "role": "assistant", "content": "Opening effort: guild-feature. For member limits, what's the max?"})
        )

        # Act
        from oi.storage import load_state
        from oi.context import build_context

        state = load_state(state_dir)
        context = build_context(state, recent_messages=[])

        # Assert: All three components present
        # Ambient
        assert "Quick weather question" in context
        assert "72°F and sunny" in context
        
        # Concluded effort summary
        assert "Debugged 401 errors after 1 hour" in context
        assert "axios interceptor" in context
        
        # New effort raw log
        assert "Now let's work on the guild feature" in context
        assert "member limit" in context
        assert "Opening effort: guild-feature" in context
        
        # Concluded effort raw log NOT present
        assert "Let's debug the auth bug" not in context

    def test_build_context_returns_formatted_string_with_sections(self, tmp_path):
        """build_context returns a formatted string with clear sections for each context source"""
        # Arrange
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()

        # Create minimal test data
        (state_dir / "raw.jsonl").write_text(
            json.dumps({"turn": 1, "role": "user", "content": "ambient user"}) + "\n" +
            json.dumps({"turn": 2, "role": "assistant", "content": "ambient assistant"})
        )
        
        manifest = {
            "efforts": [
                {
                    "id": "effort1",
                    "status": "concluded",
                    "summary": "Concluded effort summary",
                    "raw_file": "efforts/effort1.jsonl"
                },
                {
                    "id": "effort2",
                    "status": "open"
                }
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        (efforts_dir / "effort2.jsonl").write_text(
            json.dumps({"turn": 3, "role": "user", "content": "open effort user"}) + "\n" +
            json.dumps({"turn": 4, "role": "assistant", "content": "open effort assistant"})
        )

        # Act
        from oi.storage import load_state
        from oi.context import build_context

        state = load_state(state_dir)
        context = build_context(state, recent_messages=[])

        # Assert: Context is a string with reasonable structure
        assert isinstance(context, str)
        assert len(context) > 0
        
        # Should contain the ambient messages
        assert "ambient user" in context
        assert "ambient assistant" in context
        
        # Should contain concluded effort summary
        assert "Concluded effort summary" in context
        
        # Should contain open effort raw log
        assert "open effort user" in context
        assert "open effort assistant" in context

    def test_recent_messages_are_included_in_context(self, tmp_path):
        """Recent messages (not yet saved to log) are included in the built context"""
        # Arrange: Create a state with some saved content
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        (state_dir / "raw.jsonl").write_text(
            json.dumps({"turn": 1, "role": "user", "content": "saved ambient"})
        )
        
        (state_dir / "manifest.yaml").write_text(yaml.dump({"efforts": []}))

        # Recent messages that haven't been saved yet
        recent_messages = [
            {"role": "user", "content": "unsaved user message"},
            {"role": "assistant", "content": "unsaved assistant response"}
        ]

        # Act
        from oi.storage import load_state
        from oi.context import build_context

        state = load_state(state_dir)
        context = build_context(state, recent_messages=recent_messages)

        # Assert: Both saved and unsaved messages are in context
        assert "saved ambient" in context
        assert "unsaved user message" in context
        assert "unsaved assistant response" in context