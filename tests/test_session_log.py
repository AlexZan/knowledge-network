"""Unit tests for session audit logs."""

import json
import pytest

from oi.session_log import create_session_log, log_event, read_session_log


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


class TestSessionLog:
    def test_create_session_log_returns_session_id(self, session_dir):
        """create_session_log returns a timestamp-based session_id."""
        session_dir.mkdir(parents=True, exist_ok=True)
        session_id = create_session_log(session_dir)
        assert session_id  # non-empty
        # Format: YYYY-MM-DDTHH-MM-SS
        parts = session_id.split("T")
        assert len(parts) == 2
        assert len(parts[0].split("-")) == 3  # date parts

    def test_create_session_log_creates_file(self, session_dir):
        """Session log file is created in sessions/ directory."""
        session_dir.mkdir(parents=True, exist_ok=True)
        session_id = create_session_log(session_dir)
        log_path = session_dir / "sessions" / f"{session_id}.jsonl"
        assert log_path.exists()

    def test_log_event_appends_entry(self, session_dir):
        """log_event appends a timestamped JSONL entry."""
        session_dir.mkdir(parents=True, exist_ok=True)
        session_id = create_session_log(session_dir)
        log_event(session_dir, session_id, "user-message", {"content": "hello"})

        events = read_session_log(session_dir, session_id)
        assert len(events) == 1
        assert events[0]["type"] == "user-message"
        assert events[0]["data"]["content"] == "hello"
        assert "ts" in events[0]

    def test_log_multiple_events(self, session_dir):
        """Multiple events are logged in chronological order."""
        session_dir.mkdir(parents=True, exist_ok=True)
        session_id = create_session_log(session_dir)
        log_event(session_dir, session_id, "user-message", {"content": "hello"})
        log_event(session_dir, session_id, "assistant-message", {"content": "hi"})
        log_event(session_dir, session_id, "tool-call", {"tool": "open_effort", "args": {"name": "test"}})

        events = read_session_log(session_dir, session_id)
        assert len(events) == 3
        assert events[0]["type"] == "user-message"
        assert events[1]["type"] == "assistant-message"
        assert events[2]["type"] == "tool-call"

    def test_read_empty_session_log(self, session_dir):
        """Reading an empty session log returns empty list."""
        session_dir.mkdir(parents=True, exist_ok=True)
        session_id = create_session_log(session_dir)
        events = read_session_log(session_dir, session_id)
        assert events == []

    def test_read_nonexistent_session_returns_empty(self, session_dir):
        """Reading a non-existent session returns empty list."""
        session_dir.mkdir(parents=True, exist_ok=True)
        events = read_session_log(session_dir, "nonexistent")
        assert events == []

    def test_log_event_to_nonexistent_session_is_noop(self, session_dir):
        """Logging to a non-existent session doesn't crash."""
        session_dir.mkdir(parents=True, exist_ok=True)
        # Should not raise
        log_event(session_dir, "nonexistent", "user-message", {"content": "hello"})

    def test_node_created_event(self, session_dir):
        """node-created events are loggable."""
        session_dir.mkdir(parents=True, exist_ok=True)
        session_id = create_session_log(session_dir)
        log_event(session_dir, session_id, "node-created", {
            "node_id": "fact-001",
            "node_type": "fact",
        })

        events = read_session_log(session_dir, session_id)
        assert len(events) == 1
        assert events[0]["type"] == "node-created"
        assert events[0]["data"]["node_id"] == "fact-001"
