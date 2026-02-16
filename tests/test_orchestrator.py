"""Unit tests for orchestrator (LLM mocked)."""

import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from helpers import setup_concluded_effort
from oi.orchestrator import _build_messages, _log_message, process_turn
from oi.tools import open_effort, expand_effort, get_active_effort
from oi.decay import AMBIENT_WINDOW, SUMMARY_EVICTION_THRESHOLD, update_summary_references
from oi.state import _save_summary_references


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

    def test_expanded_effort_raw_in_messages(self, session_dir):
        """Expanded effort's raw log appears in context."""
        session_dir.mkdir(parents=True)
        manifest = {
            "efforts": [{
                "id": "old-effort",
                "status": "concluded",
                "summary": "Fixed the auth bug"
            }]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "old-effort.jsonl").write_text(
            json.dumps({"role": "user", "content": "EXPANDED_RAW_CONTENT", "ts": "t1"}) + "\n"
        )

        # Expand the effort
        expand_effort(session_dir, "old-effort")

        messages = _build_messages(session_dir)
        all_content = " ".join(m["content"] for m in messages)
        assert "EXPANDED_RAW_CONTENT" in all_content

    def test_expanded_effort_summary_not_duplicated(self, session_dir):
        """When expanded, summary is excluded (raw replaces it)."""
        session_dir.mkdir(parents=True)
        manifest = {
            "efforts": [{
                "id": "old-effort",
                "status": "concluded",
                "summary": "UNIQUE_SUMMARY_TEXT"
            }]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "old-effort.jsonl").write_text(
            json.dumps({"role": "user", "content": "raw data", "ts": "t1"}) + "\n"
        )

        # Expand it
        expand_effort(session_dir, "old-effort")

        messages = _build_messages(session_dir)
        system_content = messages[0]["content"]
        # Summary should NOT be in system prompt when expanded
        assert "UNIQUE_SUMMARY_TEXT" not in system_content

    def test_multiple_open_efforts_in_messages(self, session_dir):
        """Both open effort logs appear in context."""
        open_effort(session_dir, "effort-a")
        open_effort(session_dir, "effort-b")  # effort-b is active

        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True, exist_ok=True)
        (efforts_dir / "effort-a.jsonl").write_text(
            json.dumps({"role": "user", "content": "MSG_FROM_A", "ts": "t1"}) + "\n"
        )
        (efforts_dir / "effort-b.jsonl").write_text(
            json.dumps({"role": "user", "content": "MSG_FROM_B", "ts": "t1"}) + "\n"
        )

        messages = _build_messages(session_dir)
        all_content = " ".join(m["content"] for m in messages)
        assert "MSG_FROM_A" in all_content
        assert "MSG_FROM_B" in all_content

        # Active effort (B) should be last in messages
        content_messages = [m for m in messages if m["role"] != "system"]
        assert content_messages[-1]["content"] == "MSG_FROM_B"

    # === Slice 4: Bounded context tests ===

    def test_ambient_windowed_to_last_n_exchanges(self, session_dir):
        """Only last AMBIENT_WINDOW exchanges appear in context."""
        session_dir.mkdir(parents=True)
        raw = session_dir / "raw.jsonl"
        lines = ""
        for i in range(30):  # 30 exchanges = 60 messages
            lines += json.dumps({"role": "user", "content": f"msg-{i}", "ts": f"t{i*2}"}) + "\n"
            lines += json.dumps({"role": "assistant", "content": f"reply-{i}", "ts": f"t{i*2+1}"}) + "\n"
        raw.write_text(lines)

        messages = _build_messages(session_dir)
        non_system = [m for m in messages if m["role"] != "system"]
        # Should only have last AMBIENT_WINDOW exchanges (AMBIENT_WINDOW * 2 messages)
        assert len(non_system) == AMBIENT_WINDOW * 2
        # First message should be from exchange 20 (30-10=20)
        assert non_system[0]["content"] == "msg-20"
        assert non_system[-1]["content"] == "reply-29"

    def test_ambient_window_with_fewer_messages_than_limit(self, session_dir):
        """If fewer messages than limit, all are included."""
        session_dir.mkdir(parents=True)
        raw = session_dir / "raw.jsonl"
        lines = ""
        for i in range(3):
            lines += json.dumps({"role": "user", "content": f"msg-{i}", "ts": f"t{i}"}) + "\n"
            lines += json.dumps({"role": "assistant", "content": f"reply-{i}", "ts": f"t{i}"}) + "\n"
        raw.write_text(lines)

        messages = _build_messages(session_dir)
        non_system = [m for m in messages if m["role"] != "system"]
        assert len(non_system) == 6  # All 3 exchanges

    def test_evicted_summary_excluded_from_system_prompt(self, session_dir):
        """Evicted effort summaries don't appear in system prompt."""
        setup_concluded_effort(session_dir, "old-effort", "Fixed the old bug")
        # Track reference at turn 1
        _save_summary_references(session_dir, {"old-effort": 1})

        # At turn 1 + SUMMARY_EVICTION_THRESHOLD, it should be evicted
        messages = _build_messages(session_dir, current_turn=1 + SUMMARY_EVICTION_THRESHOLD)
        system_content = messages[0]["content"]
        assert "old-effort" not in system_content
        assert "Fixed the old bug" not in system_content

    def test_evicted_summary_still_in_manifest_on_disk(self, session_dir):
        """Eviction is filtering only — manifest is untouched."""
        setup_concluded_effort(session_dir, "old-effort", "Fixed the old bug")
        _save_summary_references(session_dir, {"old-effort": 1})

        # Build messages with eviction
        _build_messages(session_dir, current_turn=1 + SUMMARY_EVICTION_THRESHOLD)

        # Manifest should still have the effort
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        effort_ids = [e["id"] for e in manifest["efforts"]]
        assert "old-effort" in effort_ids

    def test_memory_section_in_system_prompt(self, session_dir):
        """System prompt includes memory section when concluded efforts exist."""
        setup_concluded_effort(session_dir, "some-effort", "Did some work")
        messages = _build_messages(session_dir)
        system_content = messages[0]["content"]
        assert "## Memory" in system_content
        assert "search_efforts" in system_content


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

    @patch("oi.orchestrator.chat_with_tools")
    def test_messages_route_to_active_effort(self, mock_chat, session_dir):
        """Messages go to the active effort, not other open efforts."""
        # Open two efforts — second becomes active
        open_effort(session_dir, "effort-a")
        open_effort(session_dir, "effort-b")

        mock_chat.return_value = self._mock_response("Working on B.")
        process_turn(session_dir, "Do something for B")

        # Message should be in effort-b log
        b_file = session_dir / "efforts" / "effort-b.jsonl"
        assert b_file.exists()
        lines = b_file.read_text().strip().split("\n")
        user_msgs = [json.loads(l) for l in lines if json.loads(l)["role"] == "user"]
        assert any("Do something for B" in m["content"] for m in user_msgs)

        # effort-a should NOT have this message
        a_file = session_dir / "efforts" / "effort-a.jsonl"
        if a_file.exists():
            a_content = a_file.read_text()
            assert "Do something for B" not in a_content
