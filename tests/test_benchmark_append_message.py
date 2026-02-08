"""Benchmark test: Single unit test for dev-agent model comparison.

Tests ONE function (append_message) with ONE behavior (writes JSON line).
Used to benchmark dev-agent models on a proper unit test.
"""

import json
from pathlib import Path


class TestAppendMessage:
    """Story 1 AC1: message saved to raw log."""

    def test_append_message_writes_role_and_content(self, tmp_path):
        """When a message is appended, it is saved as a JSON line with role and content."""
        # Arrange
        from oi.chatlog import append_message

        log_file = tmp_path / "raw.jsonl"

        # Act
        append_message("user", "hello world", log_file)

        # Assert
        entry = json.loads(log_file.read_text().strip())
        assert entry["role"] == "user"
        assert entry["content"] == "hello world"
