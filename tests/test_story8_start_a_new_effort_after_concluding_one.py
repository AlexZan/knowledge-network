"""Tests for Story 8: Start a New Effort After Concluding One"""

import json
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStory8StartNewEffortAfterConcludingOne:
    """Story 8: Start a New Effort After Concluding One"""

    def test_new_effort_after_conclusion_works_same_as_story2(self, tmp_path):
        """After concluding an effort, starting a new effort works the same as Story 2"""
        from oi.storage import create_new_effort_file, update_manifest_for_new_effort
        from oi.tools import generate_effort_opening_response, handle_open_effort_tool

        # Arrange: Simulate a concluded effort in manifest
        manifest_path = tmp_path / "manifest.yaml"
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed auth token refresh",
                    "created": "2024-01-01T00:00:00",
                    "updated": "2024-01-01T01:00:00"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest))

        # Act: Start a new effort using Story 2 functions
        new_effort_id = "guild-feature"
        user_message = "Let's add a member limit to guilds"
        create_new_effort_file(tmp_path, new_effort_id, user_message)
        update_manifest_for_new_effort(tmp_path, new_effort_id, "Add member limit to guilds")

        # Assert: New effort file created with user message
        effort_file = tmp_path / "efforts" / f"{new_effort_id}.jsonl"
        assert effort_file.exists()
        with open(effort_file) as f:
            first_line = json.loads(f.readline())
        assert first_line["role"] == "user"
        assert first_line["content"] == user_message

        # Assert: Manifest updated with new open effort
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        new_efforts = [e for e in updated_manifest["efforts"] if e["id"] == new_effort_id]
        assert len(new_efforts) == 1
        assert new_efforts[0]["status"] == "open"
        assert new_efforts[0]["summary"] == "Add member limit to guilds"

        # Assert: Concluded effort remains unchanged
        concluded_efforts = [e for e in updated_manifest["efforts"] if e["id"] == "auth-bug"]
        assert len(concluded_efforts) == 1
        assert concluded_efforts[0]["status"] == "concluded"

    def test_context_includes_concluded_summary_and_new_effort_raw_log(self, tmp_path):
        """The context includes the just-concluded effort's summary alongside the new effort's raw log"""
        from oi.context import build_turn_context
        from oi.models import ConversationState, Artifact

        # Arrange: Create a concluded effort artifact and a new open effort artifact
        concluded_artifact = Artifact(
            id="auth-bug",
            artifact_type="effort",
            summary="Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh.",
            status="resolved",
            resolution="Fixed by adding axios interceptor"
        )
        new_artifact = Artifact(
            id="guild-feature",
            artifact_type="effort",
            summary="Add member limit to guilds",
            status="open"
        )
        state = ConversationState(artifacts=[concluded_artifact, new_artifact])

        # Arrange: Create raw log for new effort
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        new_effort_log = efforts_dir / "guild-feature.jsonl"
        new_effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's add a member limit to guilds"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: guild-feature"}) + "\n"
        )

        # Arrange: Create ambient raw log
        raw_log = tmp_path / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )

        # Act: Build context
        context = build_turn_context(state, tmp_path)

        # Assert: Context includes concluded effort summary
        assert "auth-bug" in context
        assert "401 errors" in context
        assert "axios interceptor" in context

        # Assert: Context includes new effort raw messages
        assert "guild-feature" in context
        assert "member limit" in context
        assert "Opening effort" in context

        # Assert: Context includes ambient messages
        assert "how's it going" in context.lower()
        assert "Ready to help" in context

    def test_llm_tool_call_for_new_effort_after_conclusion(self, tmp_path):
        """LLM can call open_effort tool after a previous effort is concluded"""
        from oi.tools import handle_open_effort_tool

        # Arrange: Mock litellm response with tool call for opening new effort
        mock_response = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "open_effort"
        mock_tool_call.function.arguments = '{"name": "guild-feature"}'
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        mock_response.choices[0].message.content = "Sure, let's work on guild member limits."

        # Arrange: Create concluded effort in manifest
        manifest_path = tmp_path / "manifest.yaml"
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed auth",
                    "created": "2024-01-01T00:00:00",
                    "updated": "2024-01-01T01:00:00"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest))

        # Act: Handle the tool call
        with patch('oi.tools.litellm.completion', return_value=mock_response):
            # This test verifies the orchestrator would process the tool call
            # We test handle_open_effort_tool directly (the function that would be called)
            result = handle_open_effort_tool("guild-feature", "Let's add member limits", tmp_path)

        # Assert: New effort file created
        effort_file = tmp_path / "efforts" / "guild-feature.jsonl"
        assert effort_file.exists()

        # Assert: Manifest updated with new open effort
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        effort_ids = [e["id"] for e in updated_manifest["efforts"]]
        assert "guild-feature" in effort_ids
        assert "auth-bug" in effort_ids

        # Find the new effort
        new_effort = next(e for e in updated_manifest["efforts"] if e["id"] == "guild-feature")
        assert new_effort["status"] == "open"
        assert "member limits" in new_effort["summary"].lower()