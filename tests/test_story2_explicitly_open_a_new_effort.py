"""Tests for Story 2: Explicitly Open a New Effort"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestStory2ExplicitlyOpenNewEffort:
    """Story 2: Explicitly Open a New Effort"""

    def test_open_effort_tool_call_creates_effort_file(self, tmp_path):
        """When LLM calls open_effort tool, creates new effort file with opening user message."""
        from oi.storage import create_new_effort_file  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        effort_id = "auth-bug"
        user_message = "Let's debug the auth bug - users are getting 401s after about an hour"
        
        create_new_effort_file(session_dir, effort_id, user_message)
        
        effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"
        assert effort_file.exists()
        with open(effort_file) as f:
            lines = f.readlines()
        assert len(lines) == 1
        saved = json.loads(lines[0])
        assert saved["role"] == "user"
        assert saved["content"] == user_message
        assert "timestamp" in saved

    def test_open_effort_tool_call_updates_manifest(self, tmp_path):
        """When LLM calls open_effort tool, updates manifest.yaml with new open effort."""
        from oi.storage import update_manifest_for_new_effort  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        effort_id = "auth-bug"
        effort_summary = "Debug auth 401 errors after 1 hour"
        
        update_manifest_for_new_effort(session_dir, effort_id, effort_summary)
        
        manifest_path = session_dir / "manifest.yaml"
        assert manifest_path.exists()
        manifest = yaml.safe_load(manifest_path.read_text())
        assert "efforts" in manifest
        efforts = manifest["efforts"]
        assert len(efforts) == 1
        effort = efforts[0]
        assert effort["id"] == effort_id
        assert effort["status"] == "open"
        assert effort["summary"] == effort_summary
        assert "created" in effort
        assert "updated" in effort

    def test_open_effort_tool_call_updates_existing_effort_in_manifest(self, tmp_path):
        """When LLM calls open_effort for an existing effort, updates its status to open."""
        from oi.storage import update_manifest_for_new_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        manifest_path = session_dir / "manifest.yaml"
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Old summary",
                    "created": "2024-01-01T00:00:00",
                    "updated": "2024-01-01T00:00:00"
                }
            ]
        }
        manifest_path.write_text(yaml.dump(manifest))
        
        update_manifest_for_new_effort(session_dir, "auth-bug", "New summary for reopened effort")
        
        updated_manifest = yaml.safe_load(manifest_path.read_text())
        effort = updated_manifest["efforts"][0]
        assert effort["status"] == "open"
        assert effort["summary"] == "New summary for reopened effort"
        assert effort["updated"] != "2024-01-01T00:00:00"

    def test_orchestrator_processes_open_effort_tool_call(self, tmp_path):
        """Orchestrator processes LLM tool call to open_effort and invokes storage functions."""
        from oi.tools import handle_open_effort_tool  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        effort_id = "auth-bug"
        user_message = "Let's debug the auth bug"
        
        result = handle_open_effort_tool(effort_id, user_message, session_dir)
        
        assert result["status"] == "opened"
        assert result["effort_id"] == effort_id
        effort_file = session_dir / "efforts" / f"{effort_id}.jsonl"
        assert effort_file.exists()
        manifest_path = session_dir / "manifest.yaml"
        assert manifest_path.exists()

    def test_llm_response_includes_confirmation_when_opening_effort(self, tmp_path):
        """When LLM calls open_effort tool, its text response includes confirmation."""
        from oi.tools import generate_effort_opening_response  # Will fail - doesn't exist yet
        effort_id = "auth-bug"
        
        response = generate_effort_opening_response(effort_id)
        
        assert "auth-bug" in response
        assert "opened" in response.lower() or "created" in response.lower() or "starting" in response.lower()

    def test_opening_message_and_confirmation_saved_to_effort_log(self, tmp_path):
        """Opening user message and assistant confirmation saved to effort's raw log."""
        from oi.storage import save_to_effort_log  # Will fail - doesn't exist yet
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_id = "auth-bug"
        
        save_to_effort_log(effort_id, session_dir, "user", "Let's debug the auth bug")
        save_to_effort_log(effort_id, session_dir, "assistant", "Opening effort: auth-bug")
        
        effort_file = efforts_dir / f"{effort_id}.jsonl"
        assert effort_file.exists()
        with open(effort_file) as f:
            lines = f.readlines()
        assert len(lines) == 2
        user_entry = json.loads(lines[0])
        assert user_entry["role"] == "user"
        assert user_entry["content"] == "Let's debug the auth bug"
        assistant_entry = json.loads(lines[1])
        assert assistant_entry["role"] == "assistant"
        assert assistant_entry["content"] == "Opening effort: auth-bug"