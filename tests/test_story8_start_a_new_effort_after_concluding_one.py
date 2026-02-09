"""Tests for Story 8: Start a New Effort After Concluding One"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch


class TestStory8StartNewEffort:
    """Story 8: Start a New Effort After Concluding One"""

    def test_detect_new_effort_start_phrase(self):
        """AC: After concluding an effort, I can say "Let's work on Y" to start a new effort"""
        from oi.detection import detect_effort_start_phrase  # New function - ImportError
        
        # Test different ways user might start a new effort
        test_cases = [
            ("Let's work on the guild feature", True),
            ("let's debug the login issue", True),
            ("Can we look at the performance problem?", True),
            ("I want to start a new effort about caching", True),
            ("What's the weather like?", False),  # Not effort-related
            ("The auth bug is fixed", False),  # Conclusion, not start
        ]
        
        for message, expected_result in test_cases:
            result = detect_effort_start_phrase(message)
            assert result == expected_result, f"Failed for: {message}"

    def test_create_new_effort_file_in_efforts_directory(self, tmp_path):
        """AC: The assistant creates a new effort file for Y"""
        from oi.storage import create_new_effort_file  # New function - ImportError
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # Create manifest with concluded effort first
        manifest_file = session_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed auth token expiration"
                }
            ]
        }
        manifest_file.write_text(yaml.dump(manifest_data))
        
        effort_id = "guild-feature"
        create_new_effort_file(session_dir, effort_id, "Let's work on the guild feature")
        
        # Check effort file was created with correct name and content
        effort_file = efforts_dir / f"{effort_id}.jsonl"
        assert effort_file.exists()
        
        with open(effort_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            message = json.loads(lines[0])
            assert message["role"] == "user"
            assert "guild feature" in message["content"].lower()

    def test_manifest_updated_with_new_open_effort(self, tmp_path):
        """AC: The new effort is marked as 'open' in the manifest"""
        from oi.storage import update_manifest_for_new_effort  # New function - ImportError
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Start with manifest containing concluded effort
        manifest_file = session_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors"
                }
            ]
        }
        manifest_file.write_text(yaml.dump(manifest_data))
        
        effort_id = "guild-feature"
        effort_summary = "Add member limit to guilds"
        
        update_manifest_for_new_effort(session_dir, effort_id, effort_summary)
        
        # Load updated manifest
        updated_manifest = yaml.safe_load(manifest_file.read_text())
        efforts = updated_manifest.get("efforts", [])
        
        # Should have 2 efforts now
        assert len(efforts) == 2
        
        # Find the new effort
        new_effort = next(effort for effort in efforts if effort["id"] == effort_id)
        assert new_effort["status"] == "open"
        assert new_effort["summary"] == effort_summary
        
        # Old effort should still be concluded
        old_effort = next(effort for effort in efforts if effort["id"] == "auth-bug")
        assert old_effort["status"] == "concluded"

    def test_context_includes_ambient_summaries_and_new_effort_raw(self, tmp_path):
        """AC: The context includes: ambient + all summaries (including the just-concluded effort) + new effort's raw log"""
        from oi.context import build_turn_context  # Stub function - NotImplementedError
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # 1. Create ambient log with some messages
        ambient_log = session_dir / "raw.jsonl"
        ambient_messages = [
            {"role": "user", "content": "Hey, how's it going?"},
            {"role": "assistant", "content": "Good! Ready to help."}
        ]
        ambient_log.write_text("\n".join(json.dumps(msg) for msg in ambient_messages))
        
        # 2. Create manifest with concluded effort and new open effort
        manifest_file = session_dir / "manifest.yaml"
        manifest_data = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed refresh token issue"
                },
                {
                    "id": "guild-feature",
                    "status": "open",
                    "summary": "Add member limit"
                }
            ]
        }
        manifest_file.write_text(yaml.dump(manifest_data))
        
        # 3. Create effort logs
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # Concluded effort log (should NOT be in context)
        concluded_log = efforts_dir / "auth-bug.jsonl"
        concluded_messages = [
            {"role": "user", "content": "Let's debug the auth bug"},
            {"role": "assistant", "content": "Opening effort: auth-bug"},
            {"role": "user", "content": "The token expires after 1 hour"},
            {"role": "assistant", "content": "Need to add refresh interceptor"}
        ]
        concluded_log.write_text("\n".join(json.dumps(msg) for msg in concluded_messages))
        
        # New open effort log (SHOULD be in context)
        new_effort_log = efforts_dir / "guild-feature.jsonl"
        new_effort_messages = [
            {"role": "user", "content": "Let's work on guild member limits"},
            {"role": "assistant", "content": "Opening effort: guild-feature"}
        ]
        new_effort_log.write_text("\n".join(json.dumps(msg) for msg in new_effort_messages))
        
        # 4. Build context
        context = build_turn_context(session_dir)
        
        # Assert ambient content is included
        assert "Hey, how's it going?" in context
        assert "Good! Ready to help." in context
        
        # Assert concluded effort SUMMARY is included (not raw messages)
        assert "Fixed refresh token issue" in context  # Summary
        assert "Let's debug the auth bug" not in context  # Raw messages from concluded effort
        
        # Assert NEW effort's RAW log is included (since it's open)
        assert "Let's work on guild member limits" in context
        assert "Opening effort: guild-feature" in context