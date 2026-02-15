"""Unit tests for tool functions (no LLM needed)."""

import json
import pytest
from pathlib import Path

from oi.tools import open_effort, close_effort, effort_status, get_open_effort


@pytest.fixture
def session_dir(tmp_path):
    """Create a clean session directory."""
    return tmp_path / "session"


def test_open_effort_creates_manifest(session_dir):
    result = json.loads(open_effort(session_dir, "auth-bug"))
    assert result["status"] == "opened"
    assert result["effort_id"] == "auth-bug"

    manifest = (session_dir / "manifest.yaml").read_text()
    assert "auth-bug" in manifest
    assert "open" in manifest


def test_open_effort_fails_when_one_already_open(session_dir):
    open_effort(session_dir, "first")
    result = json.loads(open_effort(session_dir, "second"))
    assert "error" in result
    assert "first" in result["error"]


def test_get_open_effort_returns_none_when_empty(session_dir):
    assert get_open_effort(session_dir) is None


def test_get_open_effort_returns_open(session_dir):
    open_effort(session_dir, "test-effort")
    effort = get_open_effort(session_dir)
    assert effort is not None
    assert effort["id"] == "test-effort"
    assert effort["status"] == "open"


def test_close_effort_fails_when_none_open(session_dir):
    result = json.loads(close_effort(session_dir))
    assert "error" in result


def test_effort_status_empty(session_dir):
    result = json.loads(effort_status(session_dir))
    assert result["efforts"] == []


def test_effort_status_shows_open(session_dir):
    open_effort(session_dir, "my-effort")
    result = json.loads(effort_status(session_dir))
    assert len(result["efforts"]) == 1
    assert result["efforts"][0]["id"] == "my-effort"
    assert result["efforts"][0]["status"] == "open"


def test_open_effort_raw_file_path(session_dir):
    open_effort(session_dir, "auth-bug")
    effort = get_open_effort(session_dir)
    assert effort["raw_file"] == "efforts/auth-bug.jsonl"
