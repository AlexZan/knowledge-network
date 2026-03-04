"""Tests for LLM reasoning log (JSONL audit trail)."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from oi.llm import _log_llm_call, chat


@pytest.fixture(autouse=True)
def _no_embed():
    with patch("oi.embed.get_embedding", return_value=None):
        yield


class TestLogLlmCall:
    """Tests for the _log_llm_call helper."""

    def test_writes_valid_jsonl(self, tmp_path):
        """_log_llm_call writes a valid JSON line to the correct path."""
        os.environ["OI_SESSION_DIR"] = str(tmp_path)
        try:
            messages = [{"role": "user", "content": "hello"}]
            _log_llm_call("extract", "test-model", messages, "response text", {"key": "val"})

            log_path = tmp_path / "llm_log.jsonl"
            assert log_path.exists()

            line = log_path.read_text().strip()
            entry = json.loads(line)
            assert entry["phase"] == "extract"
            assert entry["model"] == "test-model"
            assert entry["prompt"] == messages
            assert entry["response"] == "response text"
            assert entry["meta"] == {"key": "val"}
            assert "ts" in entry
        finally:
            os.environ.pop("OI_SESSION_DIR", None)

    def test_no_session_dir_falls_back_to_home(self, tmp_path, monkeypatch):
        """Falls back to ~/.oi when OI_SESSION_DIR is not set."""
        monkeypatch.delenv("OI_SESSION_DIR", raising=False)
        # Redirect home to tmp_path so we don't pollute real ~/.oi
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        _log_llm_call("extract", "m", [], "r")
        assert (tmp_path / ".oi" / "llm_log.jsonl").exists()

    def test_meta_omitted_when_none(self, tmp_path):
        """meta key absent from entry when log_meta is None."""
        os.environ["OI_SESSION_DIR"] = str(tmp_path)
        try:
            _log_llm_call("link", "m", [], "r", meta=None)
            entry = json.loads((tmp_path / "llm_log.jsonl").read_text().strip())
            assert "meta" not in entry
        finally:
            os.environ.pop("OI_SESSION_DIR", None)

    def test_appends_multiple_entries(self, tmp_path):
        """Multiple calls append to the same file."""
        os.environ["OI_SESSION_DIR"] = str(tmp_path)
        try:
            _log_llm_call("a", "m", [], "r1")
            _log_llm_call("b", "m", [], "r2")
            lines = (tmp_path / "llm_log.jsonl").read_text().strip().split("\n")
            assert len(lines) == 2
            assert json.loads(lines[0])["phase"] == "a"
            assert json.loads(lines[1])["phase"] == "b"
        finally:
            os.environ.pop("OI_SESSION_DIR", None)

    def test_write_failure_does_not_crash(self):
        """Bad path silently fails without raising."""
        os.environ["OI_SESSION_DIR"] = "/nonexistent/readonly/path"
        try:
            # Should not raise
            _log_llm_call("extract", "m", [], "r")
        finally:
            os.environ.pop("OI_SESSION_DIR", None)

    def test_creates_parent_dirs(self, tmp_path):
        """Creates parent directories if they don't exist."""
        nested = tmp_path / "a" / "b" / "c"
        os.environ["OI_SESSION_DIR"] = str(nested)
        try:
            _log_llm_call("extract", "m", [], "r")
            assert (nested / "llm_log.jsonl").exists()
        finally:
            os.environ.pop("OI_SESSION_DIR", None)


class TestChatLogging:
    """Tests that chat() integrates with _log_llm_call correctly."""

    def _mock_completion(self, content="mock response"):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = content
        return mock_resp

    @patch("oi.llm.completion")
    def test_chat_with_phase_logs(self, mock_completion, tmp_path):
        """chat() with phase kwarg produces a log entry."""
        mock_completion.return_value = self._mock_completion("the answer")
        os.environ["OI_SESSION_DIR"] = str(tmp_path)
        try:
            messages = [{"role": "user", "content": "test"}]
            result = chat(messages, model="test-model", phase="extract", log_meta={"k": 1})

            assert result == "the answer"
            log_path = tmp_path / "llm_log.jsonl"
            assert log_path.exists()
            entry = json.loads(log_path.read_text().strip())
            assert entry["phase"] == "extract"
            assert entry["response"] == "the answer"
            assert entry["meta"] == {"k": 1}
        finally:
            os.environ.pop("OI_SESSION_DIR", None)

    @patch("oi.llm.completion")
    def test_chat_without_phase_no_log(self, mock_completion, tmp_path):
        """chat() without phase produces no log entry (backward compat)."""
        mock_completion.return_value = self._mock_completion()
        os.environ["OI_SESSION_DIR"] = str(tmp_path)
        try:
            chat([{"role": "user", "content": "test"}], model="test-model")
            assert not (tmp_path / "llm_log.jsonl").exists()
        finally:
            os.environ.pop("OI_SESSION_DIR", None)

    @patch("oi.llm.completion")
    def test_log_failure_doesnt_crash_chat(self, mock_completion):
        """If logging fails, chat() still returns the response."""
        mock_completion.return_value = self._mock_completion("works")
        os.environ["OI_SESSION_DIR"] = "/nonexistent/path"
        try:
            result = chat(
                [{"role": "user", "content": "test"}],
                model="m",
                phase="extract",
            )
            assert result == "works"
        finally:
            os.environ.pop("OI_SESSION_DIR", None)
