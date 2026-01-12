"""Tests for raw chat log."""

import pytest
from pathlib import Path
import tempfile
import shutil

from oi.chatlog import append_exchange, read_recent, search, get_chatlog_path


@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for state storage."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestChatLog:
    def test_append_exchange_creates_file(self, temp_state_dir):
        append_exchange("Hello", "Hi there!", state_dir=temp_state_dir)
        chatlog_path = get_chatlog_path(temp_state_dir)
        assert chatlog_path.exists()

    def test_append_and_read_recent(self, temp_state_dir):
        append_exchange("First", "Response 1", state_dir=temp_state_dir)
        append_exchange("Second", "Response 2", state_dir=temp_state_dir)
        append_exchange("Third", "Response 3", state_dir=temp_state_dir)

        recent = read_recent(limit=2, state_dir=temp_state_dir)
        assert len(recent) == 2
        assert recent[0]["user"] == "Second"
        assert recent[1]["user"] == "Third"

    def test_read_recent_empty(self, temp_state_dir):
        recent = read_recent(state_dir=temp_state_dir)
        assert recent == []

    def test_append_with_metadata(self, temp_state_dir):
        append_exchange(
            "Question",
            "Answer",
            metadata={"artifact_id": "abc123"},
            state_dir=temp_state_dir
        )
        recent = read_recent(limit=1, state_dir=temp_state_dir)
        assert recent[0]["metadata"]["artifact_id"] == "abc123"

    def test_search_finds_matches(self, temp_state_dir):
        append_exchange("Why is the sky blue?", "Rayleigh scattering", state_dir=temp_state_dir)
        append_exchange("Hello", "Hi there", state_dir=temp_state_dir)
        append_exchange("What color is grass?", "Green", state_dir=temp_state_dir)

        results = search("color", state_dir=temp_state_dir)
        assert len(results) == 1
        assert "grass" in results[0]["user"]

    def test_search_case_insensitive(self, temp_state_dir):
        append_exchange("HELLO", "hi", state_dir=temp_state_dir)
        results = search("hello", state_dir=temp_state_dir)
        assert len(results) == 1

    def test_search_no_matches(self, temp_state_dir):
        append_exchange("Hello", "Hi", state_dir=temp_state_dir)
        results = search("xyz123", state_dir=temp_state_dir)
        assert results == []
