"""Unit tests for session audit logs."""

import json
import pytest

from oi.session_log import (
    create_session_log, log_event, read_session_log,
    extract_node_context, NODE_CONTEXT_WINDOW,
)


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


class TestExtractNodeContext:
    def _build_session_with_node(self, session_dir, session_id, num_messages=3):
        """Helper: log messages then a node-created event."""
        for i in range(num_messages):
            log_event(session_dir, session_id, "user-message", {"content": f"user msg {i}"})
            log_event(session_dir, session_id, "assistant-message", {"content": f"assistant msg {i}"})
        log_event(session_dir, session_id, "node-created", {
            "node_id": "fact-001", "node_type": "fact",
        })

    def test_extracts_preceding_messages(self, session_dir):
        """extract_node_context returns messages before the node-created event."""
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)
        self._build_session_with_node(session_dir, sid, num_messages=3)

        context = extract_node_context(session_dir, sid, "fact-001")
        assert len(context) == NODE_CONTEXT_WINDOW
        # All entries should have role and content
        for msg in context:
            assert "role" in msg
            assert "content" in msg
        # Chronological order — 6 messages total, window=5, so starts at assistant msg 0
        assert context[0]["content"] == "assistant msg 0"
        assert context[-1]["content"] == "assistant msg 2"

    def test_returns_correct_roles(self, session_dir):
        """Extracted messages have correct role mapping."""
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)
        log_event(session_dir, sid, "user-message", {"content": "question"})
        log_event(session_dir, sid, "assistant-message", {"content": "answer"})
        log_event(session_dir, sid, "node-created", {"node_id": "fact-001", "node_type": "fact"})

        context = extract_node_context(session_dir, sid, "fact-001")
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "question"
        assert context[1]["role"] == "assistant"
        assert context[1]["content"] == "answer"

    def test_respects_window_limit(self, session_dir):
        """Only up to `window` messages are returned."""
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)
        # Log 10 exchanges (20 messages)
        for i in range(10):
            log_event(session_dir, sid, "user-message", {"content": f"user {i}"})
            log_event(session_dir, sid, "assistant-message", {"content": f"assistant {i}"})
        log_event(session_dir, sid, "node-created", {"node_id": "fact-001", "node_type": "fact"})

        context = extract_node_context(session_dir, sid, "fact-001", window=3)
        assert len(context) == 3

    def test_returns_empty_for_missing_node(self, session_dir):
        """Returns empty list if node_id not found in session log."""
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)
        log_event(session_dir, sid, "user-message", {"content": "hello"})

        context = extract_node_context(session_dir, sid, "nonexistent-node")
        assert context == []

    def test_returns_empty_for_missing_session(self, session_dir):
        """Returns empty list if session doesn't exist."""
        session_dir.mkdir(parents=True, exist_ok=True)
        context = extract_node_context(session_dir, "nonexistent-session", "fact-001")
        assert context == []

    def test_skips_non_message_events(self, session_dir):
        """Tool-call events are skipped, only user/assistant messages collected."""
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)
        log_event(session_dir, sid, "user-message", {"content": "question"})
        log_event(session_dir, sid, "tool-call", {"tool": "read_file", "args": {"path": "/tmp/x"}})
        log_event(session_dir, sid, "assistant-message", {"content": "answer"})
        log_event(session_dir, sid, "node-created", {"node_id": "fact-001", "node_type": "fact"})

        context = extract_node_context(session_dir, sid, "fact-001")
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
