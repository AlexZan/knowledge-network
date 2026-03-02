"""Tests for MCP server tool wrappers."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestSessionDir:
    """_get_session_dir resolution."""

    def test_default_session_dir(self):
        from oi.mcp_server import _get_session_dir

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OI_SESSION_DIR", None)
            result = _get_session_dir()
            assert result == Path.home() / ".oi"

    def test_env_var_override(self, tmp_path):
        from oi.mcp_server import _get_session_dir

        with patch.dict(os.environ, {"OI_SESSION_DIR": str(tmp_path)}):
            result = _get_session_dir()
            assert result == tmp_path


class TestSessionId:
    """_get_session_id creates once and reuses."""

    def test_created_once_and_reused(self):
        import oi.mcp_server as mod

        old = mod._session_id
        mod._session_id = None  # reset
        try:
            first = mod._get_session_id()
            second = mod._get_session_id()
            assert first == second
            assert len(first) == 36  # UUID format
        finally:
            mod._session_id = old


class TestOrNone:
    """Empty-string optional params converted to None."""

    def test_empty_string_to_none(self):
        from oi.mcp_server import _or_none

        assert _or_none("") is None

    def test_non_empty_passes_through(self):
        from oi.mcp_server import _or_none

        assert _or_none("hello") == "hello"

    def test_whitespace_passes_through(self):
        from oi.mcp_server import _or_none

        # Whitespace is truthy — intentional pass-through
        assert _or_none(" ") == " "


class TestFormatting:
    """Output formatting helpers produce human-readable text."""

    def test_fmt_add_success(self):
        from oi.mcp_server import _fmt_add
        raw = '{"status":"added","node_id":"fact-001","node_type":"fact","summary":"Python is great","confidence":{"level":"low"}}'
        result = _fmt_add(raw)
        assert "fact-001" in result
        assert "[fact]" in result
        assert "Python is great" in result
        assert "low" in result

    def test_fmt_add_with_edges(self):
        from oi.mcp_server import _fmt_add
        raw = json.dumps({
            "status": "added", "node_id": "fact-002", "node_type": "fact",
            "summary": "RS256 signing", "confidence": {"level": "low"},
            "edges_created": [{"edge_type": "supports", "target_id": "fact-001", "reasoning": "related"}],
        })
        result = _fmt_add(raw)
        assert "supports" in result
        assert "fact-001" in result

    def test_fmt_add_error(self):
        from oi.mcp_server import _fmt_add
        result = _fmt_add('{"error":"Invalid node_type"}')
        assert "Error" in result

    def test_fmt_query_no_results(self):
        from oi.mcp_server import _fmt_query
        result = _fmt_query('{"results":[],"total_active":5}')
        assert "No matches" in result
        assert "5" in result

    def test_fmt_query_with_results(self):
        from oi.mcp_server import _fmt_query
        raw = json.dumps({
            "results": [{"node_id": "fact-001", "type": "fact", "summary": "Python is great",
                         "source": "test", "confidence": {"level": "high"}, "edges": []}],
            "total_active": 3,
        })
        result = _fmt_query(raw)
        assert "fact-001" in result
        assert "high" in result
        assert "Python is great" in result

    def test_fmt_effort_status_empty(self):
        from oi.mcp_server import _fmt_effort_status
        result = _fmt_effort_status('{"efforts":[]}')
        assert "No efforts" in result

    def test_fmt_effort_status_with_efforts(self):
        from oi.mcp_server import _fmt_effort_status
        raw = json.dumps({"efforts": [
            {"id": "auth-bug", "status": "open", "active": True, "raw_tokens": 500},
            {"id": "old-work", "status": "concluded", "summary": "Did some stuff"},
        ]})
        result = _fmt_effort_status(raw)
        assert "auth-bug" in result
        assert "active" in result
        assert "old-work" in result
        assert "Did some stuff" in result

    def test_fmt_simple_error(self):
        from oi.mcp_server import _fmt_simple
        result = _fmt_simple('{"error":"No active effort"}')
        assert "Error" in result

    def test_fmt_simple_search_no_results(self):
        from oi.mcp_server import _fmt_simple
        result = _fmt_simple('{"results":[],"query":"auth"}')
        assert "No matches" in result


class TestToolDelegation:
    """Each MCP tool delegates to the correct underlying function."""

    def test_add_knowledge_calls_correctly(self, tmp_path):
        from oi.mcp_server import mcp_add_knowledge

        fake_json = '{"status":"added","node_id":"fact-001","node_type":"fact","summary":"test","confidence":{"level":"low"}}'
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.add_knowledge", return_value=fake_json) as mock:
            result = mcp_add_knowledge(
                node_type="fact",
                summary="Python is great",
                source="test",
            )
            mock.assert_called_once_with(
                session_dir=tmp_path,
                node_type="fact",
                summary="Python is great",
                source="test",
                related_to=None,
                edge_type="supports",
                model="test-model",
                supersedes=None,
                session_id="test-session",
            )
            assert "fact-001" in result

    def test_add_knowledge_with_related_to(self, tmp_path):
        from oi.mcp_server import mcp_add_knowledge

        fake_json = '{"status":"added","node_id":"fact-001","node_type":"fact","summary":"test","confidence":{"level":"low"}}'
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.add_knowledge", return_value=fake_json) as mock:
            mcp_add_knowledge(
                node_type="fact",
                summary="test",
                related_to="fact-001, fact-002",
                edge_type="supports",
            )
            call_kwargs = mock.call_args[1]
            assert call_kwargs["related_to"] == ["fact-001", "fact-002"]
            assert call_kwargs["edge_type"] == "supports"

    def test_add_knowledge_empty_optionals_become_none(self, tmp_path):
        from oi.mcp_server import mcp_add_knowledge

        fake_json = '{"status":"added","node_id":"fact-001","node_type":"fact","summary":"test","confidence":{"level":"low"}}'
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.add_knowledge", return_value=fake_json) as mock:
            mcp_add_knowledge(node_type="fact", summary="test")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["source"] is None
            assert call_kwargs["related_to"] is None
            assert call_kwargs["supersedes"] is None

    def test_query_knowledge_calls_correctly(self, tmp_path):
        from oi.mcp_server import mcp_query_knowledge

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.query_knowledge", return_value='{"results":[],"total_active":0}') as mock:
            result = mcp_query_knowledge(query="python")
            mock.assert_called_once_with(
                session_dir=tmp_path,
                query="python",
                node_type=None,
                min_confidence=None,
            )
            assert "No matches" in result

    def test_query_knowledge_with_filters(self, tmp_path):
        from oi.mcp_server import mcp_query_knowledge

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.query_knowledge", return_value='{"results":[],"total_active":0}') as mock:
            mcp_query_knowledge(query="python", node_type="fact", min_confidence="high")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["node_type"] == "fact"
            assert call_kwargs["min_confidence"] == "high"

    def test_open_effort(self, tmp_path):
        from oi.mcp_server import mcp_open_effort

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.open_effort", return_value='{"status":"opened","effort_id":"test-effort"}') as mock:
            result = mcp_open_effort(name="test-effort")
            mock.assert_called_once_with(session_dir=tmp_path, name="test-effort")
            assert "opened" in result

    def test_close_effort_no_id(self, tmp_path):
        from oi.mcp_server import mcp_close_effort

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.close_effort", return_value='{"status":"concluded","effort_id":"x","summary":"done"}') as mock:
            result = mcp_close_effort()
            mock.assert_called_once_with(
                session_dir=tmp_path,
                model="test-model",
                effort_id=None,
                session_id="test-session",
            )
            assert "concluded" in result

    def test_close_effort_with_id(self, tmp_path):
        from oi.mcp_server import mcp_close_effort

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.close_effort", return_value='{"status":"concluded","effort_id":"my-effort","summary":"done"}') as mock:
            mcp_close_effort(id="my-effort")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["effort_id"] == "my-effort"

    def test_effort_status(self, tmp_path):
        from oi.mcp_server import mcp_effort_status

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.effort_status", return_value='{"efforts":[]}') as mock:
            result = mcp_effort_status()
            mock.assert_called_once_with(session_dir=tmp_path)
            assert "No efforts" in result

    def test_search_efforts(self, tmp_path):
        from oi.mcp_server import mcp_search_efforts

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.search_efforts", return_value='{"results":[],"query":"auth"}') as mock:
            result = mcp_search_efforts(query="auth")
            mock.assert_called_once_with(session_dir=tmp_path, query="auth")
            assert "No matches" in result

    def test_reopen_effort(self, tmp_path):
        from oi.mcp_server import mcp_reopen_effort

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.reopen_effort", return_value='{"status":"reopened","effort_id":"old-effort","prior_summary":"did stuff"}') as mock:
            result = mcp_reopen_effort(id="old-effort")
            mock.assert_called_once_with(session_dir=tmp_path, effort_id="old-effort")
            assert "reopened" in result

    def test_switch_effort(self, tmp_path):
        from oi.mcp_server import mcp_switch_effort

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.switch_effort", return_value='{"status":"switched","effort_id":"other-effort"}') as mock:
            result = mcp_switch_effort(id="other-effort")
            mock.assert_called_once_with(session_dir=tmp_path, effort_id="other-effort")
            assert "switched" in result


class TestIntegration:
    """Integration tests with real session_dir (no mock LLM needed for these)."""

    def test_open_and_query_effort(self, tmp_path):
        """Open an effort via MCP wrapper, verify with effort_status."""
        from oi.mcp_server import mcp_open_effort, mcp_effort_status

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            result = mcp_open_effort(name="integration-test")
            assert "opened" in result

            status = mcp_effort_status()
            assert "integration-test" in status
            assert "active" in status

    def test_add_and_query_knowledge(self, tmp_path):
        """Add knowledge via MCP wrapper, query it back."""
        from oi.mcp_server import mcp_add_knowledge, mcp_query_knowledge

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.linker.run_linking", return_value=[]):
            add_result = mcp_add_knowledge(
                node_type="fact",
                summary="Python uses indentation for blocks",
                source="test",
            )
            assert "fact-001" in add_result
            assert "Python uses indentation" in add_result

            query_result = mcp_query_knowledge(query="Python indentation")
            assert "fact-001" in query_result
            assert "Python uses indentation" in query_result
