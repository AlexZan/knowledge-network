"""Tests for Story 5: Explicitly Conclude an Effort"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestStory5ExplicitlyConcludeEffort:
    """Story 5: Explicitly Conclude an Effort"""

    def test_user_says_x_is_done_triggers_conclusion_tool_call(self):
        """When I say 'X is done' about an open effort, the assistant creates a summary of the effort via tool call."""
        from oi.tools import should_conclude_effort

        message = "auth-bug is done"
        state_artifacts = [
            {"id": "auth-bug", "artifact_type": "effort", "summary": "Auth bug", "status": "open"}
        ]

        result = should_conclude_effort(message, state_artifacts)
        assert result == "auth-bug"

    def test_assistant_confirms_effort_concluded_by_name_in_response(self):
        """The assistant confirms the effort has been concluded by name."""
        from oi.tools import generate_conclusion_response

        effort_id = "auth-bug"
        summary = "Fixed the auth bug"
        response = generate_conclusion_response(effort_id, summary)

        assert "auth-bug" in response.lower()
        assert "concluding" in response.lower() or "concluded" in response.lower()

    def test_effort_status_changes_from_open_to_concluded_in_manifest(self):
        """The effort's status in the manifest changes from 'open' to 'concluded'."""
        from oi.storage import conclude_effort
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            manifest_path = session_dir / "manifest.yaml"
            manifest_path.write_text(yaml.dump({
                "efforts": [
                    {"id": "auth-bug", "status": "open", "summary": "Auth bug", "created": "2024-01-01T00:00:00", "updated": "2024-01-01T00:00:00"}
                ]
            }))

            conclude_effort("auth-bug", session_dir, "Debugged 401 errors after 1 hour.")

            manifest = yaml.safe_load(manifest_path.read_text())
            effort = next(e for e in manifest["efforts"] if e["id"] == "auth-bug")
            assert effort["status"] == "concluded"
            assert effort["updated"] != "2024-01-01T00:00:00"

    def test_summary_is_added_to_manifest_on_conclusion(self):
        """The summary is added to the manifest."""
        from oi.storage import conclude_effort
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            manifest_path = session_dir / "manifest.yaml"
            manifest_path.write_text(yaml.dump({
                "efforts": [
                    {"id": "auth-bug", "status": "open", "summary": "Auth bug", "created": "2024-01-01T00:00:00", "updated": "2024-01-01T00:00:00"}
                ]
            }))

            new_summary = "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh."
            conclude_effort("auth-bug", session_dir, new_summary)

            manifest = yaml.safe_load(manifest_path.read_text())
            effort = next(e for e in manifest["efforts"] if e["id"] == "auth-bug")
            assert effort["summary"] == new_summary

    def test_user_says_looks_good_triggers_conclusion_tool_call(self):
        """When I say 'looks good' about an open effort, the assistant creates a summary."""
        from oi.tools import should_conclude_effort

        message = "guild-feature looks good"
        state_artifacts = [
            {"id": "guild-feature", "artifact_type": "effort", "summary": "Guild member limit", "status": "open"}
        ]

        result = should_conclude_effort(message, state_artifacts)
        assert result == "guild-feature"