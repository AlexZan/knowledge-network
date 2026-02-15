"""Unit tests for orchestrator (LLM mocked)."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from oi.orchestrator import _build_messages, _log_message, process_turn
from oi.tools import open_effort


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


class TestBuildMessages:
    def test_empty_session_has_system_prompt(self, session_dir):
        messages = _build_messages(session_dir)
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "effort management tools" in messages[0]["content"]

    def test_includes_ambient_messages(self, session_dir):
        session_dir.mkdir(parents=True)
        raw = session_dir / "raw.jsonl"
        raw.write_text(
            json.dumps({"role": "user", "content": "hello", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "hi", "ts": "t2"}) + "\n"
        )
        messages = _build_messages(session_dir)
        assert len(messages) == 3  # system + 2 ambient
        assert messages[1]["content"] == "hello"
        assert messages[2]["content"] == "hi"

    def test_includes_open_effort_messages(self, session_dir):
        open_effort(session_dir, "test-effort")
        # Write some effort messages
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "work msg", "ts": "t1"}) + "\n"
        )
        messages = _build_messages(session_dir)
        assert any(m["content"] == "work msg" for m in messages)

    def test_concluded_effort_in_system_prompt(self, session_dir):
        import yaml
        session_dir.mkdir(parents=True)
        manifest = {
            "efforts": [{
                "id": "old-effort",
                "status": "concluded",
                "summary": "Fixed the auth bug"
            }]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        messages = _build_messages(session_dir)
        assert "old-effort" in messages[0]["content"]
        assert "Fixed the auth bug" in messages[0]["content"]

    def test_concluded_effort_raw_log_not_in_messages(self, session_dir):
        import yaml
        session_dir.mkdir(parents=True)
        manifest = {
            "efforts": [{
                "id": "old-effort",
                "status": "concluded",
                "summary": "Fixed the auth bug"
            }]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        # Create the raw log file — should NOT appear in messages
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "old-effort.jsonl").write_text(
            json.dumps({"role": "user", "content": "SECRET_RAW_CONTENT", "ts": "t1"}) + "\n"
        )
        messages = _build_messages(session_dir)
        all_content = " ".join(m["content"] for m in messages)
        assert "SECRET_RAW_CONTENT" not in all_content


class TestLogMessage:
    def test_log_to_ambient(self, session_dir):
        _log_message(session_dir, None, "user", "hello")
        raw = session_dir / "raw.jsonl"
        assert raw.exists()
        entry = json.loads(raw.read_text().strip())
        assert entry["role"] == "user"
        assert entry["content"] == "hello"

    def test_log_to_effort(self, session_dir):
        _log_message(session_dir, "auth-bug", "user", "debug this")
        effort_file = session_dir / "efforts" / "auth-bug.jsonl"
        assert effort_file.exists()
        entry = json.loads(effort_file.read_text().strip())
        assert entry["content"] == "debug this"


class TestProcessTurn:
    def _mock_response(self, content, tool_calls=None):
        """Create a mock LLM response message."""
        msg = MagicMock()
        msg.content = content
        msg.tool_calls = tool_calls
        return msg

    @patch("oi.orchestrator.chat_with_tools")
    def test_ambient_turn_logs_to_raw(self, mock_chat, session_dir):
        mock_chat.return_value = self._mock_response("Hi there!")
        result = process_turn(session_dir, "Hello")
        assert result == "Hi there!"
        # Check ambient log
        raw = session_dir / "raw.jsonl"
        assert raw.exists()
        lines = raw.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["content"] == "Hello"
        assert json.loads(lines[1])["content"] == "Hi there!"

    @patch("oi.orchestrator.chat_with_tools")
    def test_effort_open_logs_to_effort(self, mock_chat, session_dir):
        # First call: LLM returns tool call to open effort
        tool_call = MagicMock()
        tool_call.function.name = "open_effort"
        tool_call.function.arguments = json.dumps({"name": "auth-bug"})
        tool_call.id = "call_123"

        # Second call: LLM returns natural response
        mock_chat.side_effect = [
            self._mock_response(None, tool_calls=[tool_call]),
            self._mock_response("Got it, tracking auth-bug work.")
        ]

        result = process_turn(session_dir, "Let's debug the auth bug")
        assert "auth-bug" in result or "tracking" in result

        # Check effort log exists with messages
        effort_file = session_dir / "efforts" / "auth-bug.jsonl"
        assert effort_file.exists()
        lines = effort_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["role"] == "user"
        assert json.loads(lines[1])["role"] == "assistant"

        # Ambient should be empty
        raw = session_dir / "raw.jsonl"
        assert not raw.exists()
