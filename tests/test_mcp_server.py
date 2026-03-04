"""Tests for MCP server tool wrappers."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY

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

    def test_fmt_effort_status_shows_description(self):
        from oi.mcp_server import _fmt_effort_status
        raw = json.dumps({"efforts": [
            {"id": "typed-conflicts", "status": "open", "active": True,
             "description": "Explore conflict subtypes"},
        ]})
        result = _fmt_effort_status(raw)
        assert "Goal: Explore conflict subtypes" in result
        assert "typed-conflicts" in result

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
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=None), \
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
                reasoning=None,
                provenance_uri=None,
            )
            assert "fact-001" in result

    def test_add_knowledge_with_related_to(self, tmp_path):
        from oi.mcp_server import mcp_add_knowledge

        fake_json = '{"status":"added","node_id":"fact-001","node_type":"fact","summary":"test","confidence":{"level":"low"}}'
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=None), \
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
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=None), \
             patch("oi.mcp_server.add_knowledge", return_value=fake_json) as mock:
            mcp_add_knowledge(node_type="fact", summary="test")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["source"] is None
            assert call_kwargs["related_to"] is None
            assert call_kwargs["supersedes"] is None
            assert call_kwargs["reasoning"] is None

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
                sort_by=None,
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
             patch("oi.mcp_server.open_effort", return_value='{"status":"opened","effort_id":"test-effort"}') as mock, \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value="chatlog://claude-code/abc:L10"):
            result = mcp_open_effort(name="test-effort")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["session_dir"] == tmp_path
            assert call_kwargs["name"] == "test-effort"
            assert call_kwargs["provenance_uri"] == "chatlog://claude-code/abc:L10"
            assert "opened" in result

    def test_close_effort_no_id(self, tmp_path):
        from oi.mcp_server import mcp_close_effort

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.close_effort", return_value='{"status":"concluded","effort_id":"x","summary":"done"}') as mock, \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value="chatlog://claude-code/abc:L50"):
            result = mcp_close_effort()
            call_kwargs = mock.call_args[1]
            assert call_kwargs["session_dir"] == tmp_path
            assert call_kwargs["effort_id"] is None
            assert call_kwargs["provenance_uri"] == "chatlog://claude-code/abc:L50"
            assert "concluded" in result

    def test_close_effort_with_id(self, tmp_path):
        from oi.mcp_server import mcp_close_effort

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.close_effort", return_value='{"status":"concluded","effort_id":"my-effort","summary":"done"}') as mock, \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=None):
            mcp_close_effort(id="my-effort")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["effort_id"] == "my-effort"
            assert call_kwargs["provenance_uri"] is None

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
             patch("oi.mcp_server.reopen_effort", return_value='{"status":"reopened","effort_id":"old-effort","prior_summary":"did stuff"}') as mock, \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value="chatlog://claude-code/abc:L99"):
            result = mcp_reopen_effort(id="old-effort")
            call_kwargs = mock.call_args[1]
            assert call_kwargs["effort_id"] == "old-effort"
            assert call_kwargs["provenance_uri"] == "chatlog://claude-code/abc:L99"
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

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=None):
            result = mcp_open_effort(name="integration-test")
            assert "opened" in result

            status = mcp_effort_status()
            assert "integration-test" in status
            assert "active" in status

    def test_open_effort_with_description_shows_in_status(self, tmp_path):
        """Description flows from open_effort through to effort_status display."""
        from oi.mcp_server import mcp_open_effort, mcp_effort_status

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value="chatlog://claude-code/test:L5"):
            mcp_open_effort(name="my-effort", description="Fix the login bug")
            status = mcp_effort_status()
            assert "Goal: Fix the login bug" in status
            assert "my-effort" in status

    def test_add_and_query_knowledge(self, tmp_path):
        """Add knowledge via MCP wrapper, query it back."""
        from oi.mcp_server import mcp_add_knowledge, mcp_query_knowledge

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=None), \
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


class TestProvenance:
    """Provenance linking: reasoning field, chatlog URI, tool call log."""

    def test_discover_claude_code_chatlog_no_dir(self, tmp_path):
        """Returns None when ~/.claude/projects/ doesn't exist."""
        from oi.provenance import discover_claude_code_chatlog

        with patch("oi.provenance.Path.home", return_value=tmp_path):
            assert discover_claude_code_chatlog() is None

    def test_discover_claude_code_chatlog_finds_most_recent(self, tmp_path):
        """Finds the most recently modified .jsonl file."""
        from oi.provenance import discover_claude_code_chatlog
        import time

        projects_dir = tmp_path / ".claude" / "projects"
        project_dir = projects_dir / "test-project"
        project_dir.mkdir(parents=True)

        # Create two jsonl files with different mtimes
        old_file = project_dir / "old-session.jsonl"
        old_file.write_text('{"type":"user"}\n')

        time.sleep(0.05)  # ensure different mtime

        new_file = project_dir / "new-session.jsonl"
        new_file.write_text('{"type":"user"}\n{"type":"assistant"}\n{"type":"user"}\n')

        with patch("oi.provenance.Path.home", return_value=tmp_path):
            uri = discover_claude_code_chatlog()

        assert uri is not None
        assert "chatlog://claude-code/new-session" in uri
        assert ":L3" in uri  # 3 lines in the newer file

    def test_resolve_chatlog_uri_valid(self, tmp_path):
        """Parses a valid chatlog:// URI into components."""
        from oi.provenance import resolve_chatlog_uri

        result = resolve_chatlog_uri("chatlog://claude-code/abc123:L42")
        assert result["client"] == "claude-code"
        assert result["session_id"] == "abc123"
        assert result["line"] == 42

    def test_resolve_chatlog_uri_no_line(self):
        """Parses URI without line number."""
        from oi.provenance import resolve_chatlog_uri

        result = resolve_chatlog_uri("chatlog://claude-code/abc123")
        assert result["client"] == "claude-code"
        assert result["session_id"] == "abc123"
        assert result["line"] is None

    def test_resolve_chatlog_uri_invalid(self):
        """Returns None for non-chatlog URIs."""
        from oi.provenance import resolve_chatlog_uri

        assert resolve_chatlog_uri("https://example.com") is None
        assert resolve_chatlog_uri("") is None

    def test_reasoning_field_stored_on_node(self, tmp_path):
        """Reasoning is stored on the node and returned in queries."""
        from oi.mcp_server import mcp_add_knowledge, mcp_query_knowledge

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=None), \
             patch("oi.linker.run_linking", return_value=[]):
            add_result = mcp_add_knowledge(
                node_type="fact",
                summary="Temperature=0 gives deterministic results",
                reasoning="Tested 5 times: 3/5 inconsistent without, 5/5 consistent with temp=0",
            )
            assert "Reasoning:" in add_result
            assert "Tested 5 times" in add_result

            query_result = mcp_query_knowledge(query="temperature deterministic")
            assert "reasoning:" in query_result
            assert "Tested 5 times" in query_result

    def test_provenance_uri_auto_stamped(self, tmp_path):
        """Chatlog URI is auto-discovered and stamped on the node."""
        from oi.mcp_server import mcp_add_knowledge

        fake_uri = "chatlog://claude-code/test-session:L100"
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.mcp_server._get_session_id", return_value="test-session"), \
             patch("oi.mcp_server.discover_claude_code_chatlog", return_value=fake_uri), \
             patch("oi.linker.run_linking", return_value=[]):
            add_result = mcp_add_knowledge(
                node_type="fact",
                summary="Test provenance",
            )
            assert "Provenance:" in add_result
            assert "chatlog://claude-code/test-session:L100" in add_result

    def test_tool_call_log_written(self, tmp_path):
        """_log_tool_call writes JSONL to mcp_sessions/."""
        from oi.mcp_server import _log_tool_call, _get_session_id

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            _log_tool_call("mcp_add_knowledge", {"summary": "test"}, "fact-001")

            log_dir = tmp_path / "mcp_sessions"
            assert log_dir.exists()
            log_files = list(log_dir.glob("*.jsonl"))
            assert len(log_files) == 1

            with open(log_files[0]) as f:
                entry = json.loads(f.readline())
            assert entry["tool"] == "mcp_add_knowledge"
            assert entry["input"]["summary"] == "test"
            assert entry["result"] == "fact-001"
            assert "ts" in entry

    def test_tool_call_log_appends(self, tmp_path):
        """Multiple tool calls append to the same log file."""
        from oi.mcp_server import _log_tool_call

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            _log_tool_call("mcp_add_knowledge", {"summary": "first"})
            _log_tool_call("mcp_query_knowledge", {"query": "test"})

            log_dir = tmp_path / "mcp_sessions"
            log_files = list(log_dir.glob("*.jsonl"))
            assert len(log_files) == 1

            with open(log_files[0]) as f:
                lines = f.readlines()
            assert len(lines) == 2

    def test_fmt_add_shows_provenance(self):
        """_fmt_add includes reasoning and provenance when present."""
        from oi.mcp_server import _fmt_add

        raw = json.dumps({
            "status": "added", "node_id": "fact-001", "node_type": "fact",
            "summary": "Test node", "confidence": {"level": "low"},
            "reasoning": "Because I said so",
            "provenance_uri": "chatlog://claude-code/abc:L42",
        })
        result = _fmt_add(raw)
        assert "Reasoning: Because I said so" in result
        assert "Provenance: chatlog://claude-code/abc:L42" in result

    def test_fmt_query_shows_provenance(self):
        """_fmt_query includes reasoning and provenance when present."""
        from oi.mcp_server import _fmt_query

        raw = json.dumps({
            "results": [{
                "node_id": "fact-001", "type": "fact", "summary": "Test",
                "source": "test", "confidence": {"level": "low"}, "edges": [],
                "reasoning": "Important because X",
                "provenance_uri": "chatlog://claude-code/abc:L42",
            }],
            "total_active": 1,
        })
        result = _fmt_query(raw)
        assert "reasoning: Important because X" in result
        assert "provenance: chatlog://claude-code/abc:L42" in result


class TestRemoveEdge:
    """Edge removal for correcting false positive links."""

    def test_remove_edge_success(self, tmp_path):
        """Remove a specific edge between two nodes."""
        from oi.knowledge import add_knowledge, remove_edge
        from unittest.mock import patch as _patch

        with _patch("oi.linker.run_linking", return_value=[]):
            add_knowledge(session_dir=tmp_path, node_type="fact", summary="Node A")
            add_knowledge(
                session_dir=tmp_path, node_type="fact", summary="Node B",
                related_to=["fact-001"], edge_type="contradicts",
            )
            # Verify edge exists
            result = json.loads(remove_edge(
                session_dir=tmp_path, source_id="fact-002", target_id="fact-001",
                edge_type="contradicts",
            ))
            assert result["status"] == "removed"
            assert result["removed_count"] == 1
            assert result["edges_removed"][0]["type"] == "contradicts"

    def test_remove_edge_clears_has_contradiction(self, tmp_path):
        """Removing the last contradicts edge clears has_contradiction flag."""
        from oi.knowledge import add_knowledge, remove_edge
        from oi.state import _load_knowledge
        from unittest.mock import patch as _patch

        with _patch("oi.linker.run_linking", return_value=[]):
            add_knowledge(session_dir=tmp_path, node_type="fact", summary="Node A")
            add_knowledge(
                session_dir=tmp_path, node_type="fact", summary="Node B",
                related_to=["fact-001"], edge_type="contradicts",
            )
            remove_edge(session_dir=tmp_path, source_id="fact-002", target_id="fact-001")

            kg = _load_knowledge(tmp_path)
            for node in kg["nodes"]:
                assert "has_contradiction" not in node

    def test_remove_edge_not_found(self, tmp_path):
        """Returns error when edge doesn't exist."""
        from oi.knowledge import add_knowledge, remove_edge
        from unittest.mock import patch as _patch

        with _patch("oi.linker.run_linking", return_value=[]):
            add_knowledge(session_dir=tmp_path, node_type="fact", summary="Node A")
            result = json.loads(remove_edge(
                session_dir=tmp_path, source_id="fact-001", target_id="fact-999",
            ))
            assert "error" in result

    def test_mcp_remove_edge_wrapper(self, tmp_path):
        """MCP wrapper formats output correctly."""
        from oi.mcp_server import mcp_remove_edge

        fake_result = json.dumps({
            "status": "removed", "removed_count": 1,
            "edges_removed": [{"source": "d-012", "target": "d-007", "type": "contradicts"}],
        })
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server.remove_edge", return_value=fake_result):
            result = mcp_remove_edge(source_id="d-012", target_id="d-007", edge_type="contradicts")
            assert "Removed 1 edge(s)" in result
            assert "contradicts" in result


class TestIngestDocument:
    """MCP ingest document tool."""

    def test_mcp_ingest_document_delegates(self, tmp_path):
        """mcp_ingest_document delegates to ingest_pipeline and formats output."""
        from oi.mcp_server import mcp_ingest_document
        from oi.ingest import PipelineResult

        fake_result = PipelineResult(
            source_path="docs/test.md",
            nodes_created=["fact-001", "fact-002"],
            chunks_total=3,
            chunks_processed=2,
            chunks_failed=1,
            claims_extracted=2,
            edges_created=1,
            contradictions_found=0,
            conflicts={"total": 0, "auto_resolvable": 0, "strong_recommendations": 0, "ambiguous": 0},
            errors=[],
            dry_run=False,
        )
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.ingest.ingest_pipeline", return_value=fake_result) as mock_pipeline:
            result = mcp_ingest_document(file_path="/path/to/docs/test.md")
            call_kwargs = mock_pipeline.call_args[1]
            assert call_kwargs["file_path"] == "/path/to/docs/test.md"
            assert call_kwargs["session_dir"] == tmp_path
            assert call_kwargs["model"] == "test-model"
            assert call_kwargs["dry_run"] is False
            assert call_kwargs["skip_linking"] is False
            assert call_kwargs["source_id"] is None
            assert "Nodes created: 2" in result
            assert "docs/test.md" in result
            assert "Claims extracted: 2" in result
            assert "Chunks failed: 1" in result

    def test_mcp_ingest_document_dry_run(self, tmp_path):
        """Dry-run mode shows preview without writing."""
        from oi.mcp_server import mcp_ingest_document
        from oi.ingest import PipelineResult

        fake_result = PipelineResult(
            source_path="docs/paper.md",
            chunks_total=5,
            chunks_processed=4,
            claims_extracted=10,
            dry_run=True,
        )
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.ingest.ingest_pipeline", return_value=fake_result):
            result = mcp_ingest_document(file_path="/path/to/paper.md", dry_run=True)
            assert "DRY RUN" in result
            assert "10 would be extracted" in result

    def test_fmt_ingest_with_errors(self):
        """_fmt_ingest shows errors."""
        from oi.mcp_server import _fmt_ingest
        from oi.ingest import PipelineResult

        result = PipelineResult(
            source_path="bad.md",
            errors=["Parse failed: bad format", "Extra error"],
            dry_run=False,
        )
        formatted = _fmt_ingest(result)
        assert "Errors (2)" in formatted
        assert "Parse failed" in formatted

    def test_mcp_ingest_document_passes_source_id(self, tmp_path):
        """source_id is forwarded to ingest_pipeline."""
        from oi.mcp_server import mcp_ingest_document
        from oi.ingest import PipelineResult

        fake_result = PipelineResult(source_path="test.md", dry_run=False)
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.ingest.ingest_pipeline", return_value=fake_result) as mock_pipeline:
            mcp_ingest_document(file_path="/path/to/test.md", source_id="my-source")
            assert mock_pipeline.call_args[1]["source_id"] == "my-source"


class TestSourceTools:
    """mcp_add_source and mcp_list_sources."""

    def test_add_source_registers(self, tmp_path):
        from oi.mcp_server import mcp_add_source

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            result = mcp_add_source(id="my-docs", type="doc_root", path=str(tmp_path))
            assert "Registered source 'my-docs'" in result

    def test_add_source_idempotent(self, tmp_path):
        from oi.mcp_server import mcp_add_source

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            mcp_add_source(id="my-docs", type="doc_root", path=str(tmp_path))
            result = mcp_add_source(id="my-docs", type="doc_root", path=str(tmp_path))
            assert "already registered" in result

    def test_add_source_conflict(self, tmp_path):
        from oi.mcp_server import mcp_add_source
        other = tmp_path / "other"; other.mkdir()

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            mcp_add_source(id="my-docs", type="doc_root", path=str(tmp_path))
            result = mcp_add_source(id="my-docs", type="doc_root", path=str(other))
            assert result.startswith("Error:")

    def test_list_sources_empty(self, tmp_path):
        from oi.mcp_server import mcp_list_sources

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            result = mcp_list_sources()
            assert "No sources registered" in result

    def test_list_sources_shows_entries(self, tmp_path):
        from oi.mcp_server import mcp_add_source, mcp_list_sources

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            mcp_add_source(id="my-docs", type="doc_root", path=str(tmp_path), label="My Docs")
            result = mcp_list_sources()
            assert "my-docs" in result
            assert "doc_root" in result

    def test_list_sources_checks_path_existence(self, tmp_path):
        from oi.mcp_server import mcp_add_source, mcp_list_sources

        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path):
            mcp_add_source(id="gone", type="doc_root", path="/nonexistent/path/here")
            result = mcp_list_sources()
            assert "NOT FOUND" in result


class TestIngestChatGPTExport:
    """mcp_ingest_chatgpt_export tool."""

    def test_mcp_ingest_chatgpt_export_dry_run(self, tmp_path):
        """Dry-run returns formatted result with no graph changes."""
        from oi.mcp_server import mcp_ingest_chatgpt_export
        from oi.ingest import PipelineResult

        fake_result = PipelineResult(
            source_path="physics-chatgpt (5 conversations)",
            chunks_total=10,
            chunks_processed=9,
            claims_extracted=20,
            dry_run=True,
        )
        with patch("oi.mcp_server._get_session_dir", return_value=tmp_path), \
             patch("oi.mcp_server._get_model", return_value="test-model"), \
             patch("oi.ingest.ingest_chatgpt_export", return_value=fake_result) as mock_fn:
            result = mcp_ingest_chatgpt_export(
                source_id="physics-chatgpt",
                title_filter="quantum",
                dry_run=True,
            )
            call_kwargs = mock_fn.call_args[1]
            assert call_kwargs["source_id"] == "physics-chatgpt"
            assert call_kwargs["title_filter"] == "quantum"
            assert call_kwargs["dry_run"] is True
            assert "DRY RUN" in result
            assert "20 would be extracted" in result
            assert "physics-chatgpt" in result
