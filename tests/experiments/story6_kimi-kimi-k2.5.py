"""Tests for Story 6: Remove Concluded Effort from Active Context"""

import pytest
import yaml
import json
from pathlib import Path
from unittest.mock import patch

from oi.conversation import conclude_effort
from oi.context import build_context_from_manifest


class TestStory6RemoveConcludedEffortFromActiveContext:
    """Story 6: Remove Concluded Effort from Active Context"""

    def test_concluded_effort_raw_log_not_in_context(self, tmp_path):
        """After an effort is concluded, its raw log is no longer included in the context for subsequent turns"""
        # Arrange: Set up file-based session structure
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called."
                }
            ]
        }
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create effort raw log file with conversation turns
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n" +
            json.dumps({"role": "user", "content": "Users getting 401s after an hour"}) + "\n"
        )
        
        # Create ambient raw log
        ambient_log = tmp_path / "raw.jsonl"
        ambient_log.write_text(
            json.dumps({"role": "user", "content": "Hey how's it going?"}) + "\n"
        )
        
        # Act: Build context for next turn
        context = build_context_from_manifest(tmp_path)
        context_str = json.dumps(context)
        
        # Assert: Raw effort messages should NOT be in context
        assert "Let's debug the auth bug" not in context_str
        assert "Opening effort: auth-bug" not in context_str
        assert "Users getting 401s after an hour" not in context_str

    def test_concluded_effort_summary_included_in_context(self, tmp_path):
        """Only the summary of the concluded effort (from the manifest) is included in the context"""
        # Arrange: Create manifest with concluded effort summary
        summary = "Debugged 401 errors. Root cause: refresh tokens never auto-called."
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": summary
                }
            ]
        }
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create empty efforts dir (file might not exist or be empty, only manifest matters for summary)
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        
        # Act: Build context
        context = build_context_from_manifest(tmp_path)
        context_str = json.dumps(context)
        
        # Assert: Summary should be present in context
        assert summary in context_str
        # But full conversation should not be
        assert "401s after an hour" not in context_str

    def test_concluded_effort_file_preserved_on_disk(self, tmp_path):
        """The raw log file for the concluded effort is preserved on disk for potential future reference"""
        # Arrange: Create effort file and manifest with open effort
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_file = efforts_dir / "auth-bug.jsonl"
        original_content = json.dumps({"role": "user", "content": "debugging content"})
        effort_file.write_text(original_content + "\n")
        
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open"
                }
            ]
        }
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Act: Conclude the effort
        conclude_effort("auth-bug", tmp_path)
        
        # Assert: File still exists with original content
        assert effort_file.exists()
        assert original_content in effort_file.read_text()
        
        # Assert: Manifest is updated to concluded
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        assert updated_manifest["efforts"][0]["status"] == "concluded"

    def test_open_effort_raw_log_included_in_context(self, tmp_path):
        """Open efforts should still have their raw logs included in context (contrast test)"""
        # Arrange: Create manifest with open effort
        manifest = {
            "efforts": [
                {
                    "id": "guild-feature",
                    "status": "open"
                }
            ]
        }
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create effort raw log
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "guild-feature.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's add member limits"}) + "\n"
        )
        
        # Act: Build context
        context = build_context_from_manifest(tmp_path)
        context_str = json.dumps(context)
        
        # Assert: Open effort messages SHOULD be in context
        assert "Let's add member limits" in context_str

    def test_context_includes_ambient_plus_manifest_plus_open_efforts(self, tmp_path):
        """Context composition: ambient + manifest summaries + open effort raw logs"""
        # Arrange: Mix of ambient, concluded effort, and open effort
        ambient_log = tmp_path / "raw.jsonl"
        ambient_log.write_text(
            json.dumps({"role": "user", "content": "Hello there"}) + "\n"
        )
        
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Auth bug fixed"
                },
                {
                    "id": "guild-feature",
                    "status": "open"
                }
            ]
        }
        (tmp_path / "manifest.yaml").write_text(yaml.dump(manifest))
        
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        
        # Concluded effort file (should be excluded)
        (efforts_dir / "auth-bug.jsonl").write_text(
            json.dumps({"role": "user", "content": "auth debug"}) + "\n"
        )
        
        # Open effort file (should be included)
        (efforts_dir / "guild-feature.jsonl").write_text(
            json.dumps({"role": "user", "content": "guild work"}) + "\n"
        )
        
        # Act
        context = build_context_from_manifest(tmp_path)
        context_str = json.dumps(context)
        
        # Assert: All three sources present in context
        assert "Hello there" in context_str  # Ambient
        assert "Auth bug fixed" in context_str  # Manifest summary of concluded
        assert "guild work" in context_str  # Open effort raw
        assert "auth debug" not in context_str  # Concluded effort raw excluded