"""Unit tests for tool functions (no LLM needed)."""

import json
import pytest

from helpers import setup_concluded_effort
from oi.tools import (
    open_effort, close_effort, effort_status,
    get_open_effort, get_active_effort, get_all_open_efforts,
    expand_effort, collapse_effort, switch_effort, search_efforts,
    reopen_effort, read_file, run_command, write_file, append_file,
    expand_knowledge, collapse_knowledge,
    execute_tool,
    READ_FILE_MAX_CHARS, RUN_COMMAND_MAX_CHARS,
)
from oi.knowledge import add_knowledge
from oi.state import (
    _load_expanded, _save_expanded, _load_expanded_state,
    _load_session_state, _save_session_state, increment_turn,
    increment_session_count, _load_efforts,
    _load_knowledge, _save_knowledge,
    _load_expanded_knowledge, _save_expanded_knowledge,
)
from oi.cli import _append_session_marker, _show_startup


@pytest.fixture
def session_dir(tmp_path):
    """Create a clean session directory."""
    return tmp_path / "session"


# === Slice 1 tests (updated for multi-effort) ===

class TestOpenEffort:
    def test_open_effort_creates_knowledge_entry(self, session_dir):
        result = json.loads(open_effort(session_dir, "auth-bug"))
        assert result["status"] == "opened"
        assert result["effort_id"] == "auth-bug"

        knowledge = (session_dir / "knowledge.yaml").read_text()
        assert "auth-bug" in knowledge
        assert "open" in knowledge

    def test_multi_open_efforts(self, session_dir):
        """Opening a second effort succeeds (no error)."""
        result1 = json.loads(open_effort(session_dir, "first"))
        assert result1["status"] == "opened"
        result2 = json.loads(open_effort(session_dir, "second"))
        assert result2["status"] == "opened"
        assert "error" not in result2

        all_open = get_all_open_efforts(session_dir)
        assert len(all_open) == 2

    def test_new_effort_becomes_active(self, session_dir):
        """Opening a new effort sets it as active, deactivates the previous."""
        open_effort(session_dir, "first")
        active = get_active_effort(session_dir)
        assert active["id"] == "first"

        open_effort(session_dir, "second")
        active = get_active_effort(session_dir)
        assert active["id"] == "second"

        # First is still open but not active
        all_open = get_all_open_efforts(session_dir)
        first = [e for e in all_open if e["id"] == "first"][0]
        assert first.get("active") is False

    def test_open_effort_raw_file_path(self, session_dir):
        open_effort(session_dir, "auth-bug")
        effort = get_open_effort(session_dir)
        assert effort["raw_file"] == "efforts/auth-bug.jsonl"

    def test_open_effort_with_description(self, session_dir):
        open_effort(session_dir, "typed-conflicts", description="Explore conflict subtypes beyond binary contradicts edges")
        effort = get_active_effort(session_dir)
        assert effort["description"] == "Explore conflict subtypes beyond binary contradicts edges"

    def test_open_effort_with_provenance(self, session_dir):
        open_effort(session_dir, "auth-bug", provenance_uri="chatlog://claude-code/abc:L42")
        effort = get_active_effort(session_dir)
        assert effort["provenance_uri"] == "chatlog://claude-code/abc:L42"

    def test_open_effort_description_persists_through_save_load(self, session_dir):
        """Description and provenance survive save/load cycle."""
        open_effort(session_dir, "test-effort",
                    description="Test persistence",
                    provenance_uri="chatlog://claude-code/xyz:L10")
        # Load again from disk
        effort = get_active_effort(session_dir)
        assert effort["description"] == "Test persistence"
        assert effort["provenance_uri"] == "chatlog://claude-code/xyz:L10"


class TestGetEffort:
    def test_get_open_effort_returns_none_when_empty(self, session_dir):
        assert get_open_effort(session_dir) is None

    def test_get_open_effort_returns_open(self, session_dir):
        open_effort(session_dir, "test-effort")
        effort = get_open_effort(session_dir)
        assert effort is not None
        assert effort["id"] == "test-effort"
        assert effort["status"] == "open"

    def test_get_active_effort_returns_none_when_empty(self, session_dir):
        assert get_active_effort(session_dir) is None

    def test_get_active_effort_returns_active(self, session_dir):
        open_effort(session_dir, "test-effort")
        active = get_active_effort(session_dir)
        assert active is not None
        assert active["id"] == "test-effort"


class TestCloseEffort:
    def test_close_effort_fails_when_none_open(self, session_dir):
        result = json.loads(close_effort(session_dir))
        assert "error" in result

    def test_close_effort_by_id(self, session_dir):
        """Close a specific effort by ID, not just the active one."""
        open_effort(session_dir, "first")
        open_effort(session_dir, "second")

        # Close "first" by ID (not the active one)
        from unittest.mock import patch
        with patch("oi.llm.summarize_effort", return_value="Summary of first."):
            result = json.loads(close_effort(session_dir, effort_id="first"))
        assert result["status"] == "concluded"
        assert result["effort_id"] == "first"

        # "second" should still be open and active
        active = get_active_effort(session_dir)
        assert active["id"] == "second"

    def test_close_active_activates_next(self, session_dir):
        """Closing the active effort activates the next open one."""
        open_effort(session_dir, "first")
        open_effort(session_dir, "second")
        # "second" is active, "first" is backgrounded

        from unittest.mock import patch
        with patch("oi.llm.summarize_effort", return_value="Summary of second."):
            result = json.loads(close_effort(session_dir))  # closes active = "second"
        assert result["effort_id"] == "second"

        # "first" should now be active
        active = get_active_effort(session_dir)
        assert active is not None
        assert active["id"] == "first"


class TestEffortStatus:
    def test_effort_status_empty(self, session_dir):
        result = json.loads(effort_status(session_dir))
        assert result["efforts"] == []

    def test_effort_status_shows_open(self, session_dir):
        open_effort(session_dir, "my-effort")
        result = json.loads(effort_status(session_dir))
        assert len(result["efforts"]) == 1
        assert result["efforts"][0]["id"] == "my-effort"
        assert result["efforts"][0]["status"] == "open"
        assert result["efforts"][0]["active"] is True

    def test_effort_status_shows_description(self, session_dir):
        open_effort(session_dir, "my-effort", description="Investigate auth flow")
        result = json.loads(effort_status(session_dir))
        assert result["efforts"][0]["description"] == "Investigate auth flow"

    def test_effort_status_shows_expanded(self, session_dir):
        """Expanded efforts are marked in status."""
        setup_concluded_effort(session_dir, "old", "Done.")
        expand_effort(session_dir, "old")
        result = json.loads(effort_status(session_dir))
        old_entry = [e for e in result["efforts"] if e["id"] == "old"][0]
        assert old_entry.get("expanded") is True


# === Slice 2: Expansion tests ===

class TestExpandEffort:
    def test_expand_concluded_effort(self, session_dir):
        setup_concluded_effort(session_dir, "auth-bug", "Fixed auth-bug.")
        result = json.loads(expand_effort(session_dir, "auth-bug"))
        assert result["status"] == "expanded"
        assert result["effort_id"] == "auth-bug"
        assert result["tokens_loaded"] > 0

        expanded = _load_expanded(session_dir)
        assert "auth-bug" in expanded

    def test_expand_non_concluded_fails(self, session_dir):
        """Can't expand an open effort."""
        open_effort(session_dir, "active-work")
        result = json.loads(expand_effort(session_dir, "active-work"))
        assert "error" in result
        assert "open" in result["error"]

    def test_expand_already_expanded_fails(self, session_dir):
        setup_concluded_effort(session_dir, "auth-bug", "Fixed auth-bug.")
        expand_effort(session_dir, "auth-bug")
        result = json.loads(expand_effort(session_dir, "auth-bug"))
        assert "error" in result
        assert "already expanded" in result["error"]

    def test_expand_nonexistent_fails(self, session_dir):
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "knowledge.yaml").write_text("nodes: []\nedges: []\n")
        result = json.loads(expand_effort(session_dir, "nope"))
        assert "error" in result


class TestCollapseEffort:
    def test_collapse_expanded_effort(self, session_dir):
        """Collapse succeeds and removes from expanded.json."""
        setup_concluded_effort(session_dir, "old", "Done.")
        expand_effort(session_dir, "old")
        assert "old" in _load_expanded(session_dir)

        result = json.loads(collapse_effort(session_dir, "old"))
        assert result["status"] == "collapsed"
        assert "old" not in _load_expanded(session_dir)

    def test_collapse_non_expanded_fails(self, session_dir):
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(collapse_effort(session_dir, "not-expanded"))
        assert "error" in result
        assert "not currently expanded" in result["error"]


# === Slice 2: Switch tests ===

class TestSwitchEffort:
    def test_switch_effort(self, session_dir):
        """Switch changes the active flag."""
        open_effort(session_dir, "first")
        open_effort(session_dir, "second")  # second is now active

        result = json.loads(switch_effort(session_dir, "first"))
        assert result["status"] == "switched"
        assert result["effort_id"] == "first"

        active = get_active_effort(session_dir)
        assert active["id"] == "first"

    def test_switch_to_concluded_fails(self, session_dir):
        setup_concluded_effort(session_dir, "old", "Done.")
        result = json.loads(switch_effort(session_dir, "old"))
        assert "error" in result
        assert "concluded" in result["error"]

    def test_switch_nonexistent_fails(self, session_dir):
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "knowledge.yaml").write_text("nodes: []\nedges: []\n")
        result = json.loads(switch_effort(session_dir, "nope"))
        assert "error" in result


# === Slice 3: Session state tests ===

class TestSessionState:
    def test_increment_turn(self, session_dir):
        """Turn counter increments correctly and persists."""
        assert increment_turn(session_dir) == 1
        assert increment_turn(session_dir) == 2
        assert increment_turn(session_dir) == 3

        state = _load_session_state(session_dir)
        assert state["turn_count"] == 3

    def test_session_state_default(self, session_dir):
        """Fresh session returns turn_count 0."""
        state = _load_session_state(session_dir)
        assert state["turn_count"] == 0

    def test_session_state_round_trip(self, session_dir):
        """Save and load preserves data."""
        _save_session_state(session_dir, {"turn_count": 42})
        state = _load_session_state(session_dir)
        assert state["turn_count"] == 42
        assert "updated" in state


class TestExpandedFormat:
    def test_expanded_json_has_last_referenced_turn(self, session_dir):
        """New expanded.json format includes last_referenced_turn."""
        setup_concluded_effort(session_dir, "old", "Done.")

        # Set turn count before expanding
        _save_session_state(session_dir, {"turn_count": 5})
        expand_effort(session_dir, "old")

        state = _load_expanded_state(session_dir)
        assert "last_referenced_turn" in state
        assert state["last_referenced_turn"]["old"] == 5

    def test_save_expanded_preserves_timestamps(self, session_dir):
        """Saving expanded set preserves existing expanded_at timestamps."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _save_expanded(session_dir, {"a"}, last_referenced_turn={"a": 1})
        state1 = _load_expanded_state(session_dir)
        ts_a = state1["expanded_at"]["a"]

        # Save again with a added — timestamp should be preserved
        _save_expanded(session_dir, {"a", "b"}, last_referenced_turn={"a": 1, "b": 2})
        state2 = _load_expanded_state(session_dir)
        assert state2["expanded_at"]["a"] == ts_a  # preserved
        assert "b" in state2["expanded_at"]  # new one added


# === Slice 4: search_efforts tests ===

class TestSearchEfforts:
    def test_search_finds_matching_effort(self, session_dir):
        """Search by keywords finds matching concluded effort."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        result = json.loads(search_efforts(session_dir, "refresh tokens 401"))
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "auth-bug"

    def test_search_by_effort_id(self, session_dir):
        """Search by effort ID finds the effort."""
        setup_concluded_effort(session_dir, "auth-bug", "Fixed something.")
        result = json.loads(search_efforts(session_dir, "auth-bug"))
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "auth-bug"

    def test_search_no_match_returns_empty(self, session_dir):
        """Search with no matching terms returns empty results."""
        setup_concluded_effort(session_dir, "auth-bug", "Fixed 401 errors.")
        result = json.loads(search_efforts(session_dir, "pizza recipe cooking"))
        assert len(result["results"]) == 0

    def test_search_multiple_matches(self, session_dir):
        """Search returns multiple matching efforts."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens expired."
        )
        setup_concluded_effort(
            session_dir, "token-rotation",
            "Implemented automatic refresh tokens rotation."
        )
        result = json.loads(search_efforts(session_dir, "refresh tokens"))
        assert len(result["results"]) == 2
        ids = {r["id"] for r in result["results"]}
        assert "auth-bug" in ids
        assert "token-rotation" in ids

    def test_search_ignores_open_efforts(self, session_dir):
        """Search only returns concluded efforts, not open ones."""
        setup_concluded_effort(session_dir, "auth-bug", "Fixed authentication errors.")
        open_effort(session_dir, "auth-new")
        result = json.loads(search_efforts(session_dir, "auth-bug"))
        ids = {r["id"] for r in result["results"]}
        assert "auth-bug" in ids
        assert "auth-new" not in ids


# === Slice 5: Reopen effort tests ===

class TestReopenEffort:
    def test_reopen_concluded_effort(self, session_dir):
        """Reopen flips a concluded effort back to open and active."""
        setup_concluded_effort(session_dir, "auth-bug", "Fixed 401 errors.")
        result = json.loads(reopen_effort(session_dir, "auth-bug"))
        assert result["status"] == "reopened"
        assert result["effort_id"] == "auth-bug"
        assert result["prior_summary"] == "Fixed 401 errors."

        active = get_active_effort(session_dir)
        assert active["id"] == "auth-bug"
        assert active["status"] == "open"

    def test_reopen_deactivates_other_open_efforts(self, session_dir):
        """Reopening sets the reopened effort as active, deactivates others."""
        open_effort(session_dir, "current-work")
        setup_concluded_effort(session_dir, "old-bug", "Fixed old bug.")

        reopen_effort(session_dir, "old-bug")
        active = get_active_effort(session_dir)
        assert active["id"] == "old-bug"

        # current-work is still open but not active
        all_open = get_all_open_efforts(session_dir)
        current = [e for e in all_open if e["id"] == "current-work"][0]
        assert current.get("active") is False

    def test_reopen_preserves_raw_log(self, session_dir):
        """Reopening preserves the existing raw log content."""
        raw = (
            json.dumps({"role": "user", "content": "Original message", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Original reply", "ts": "t2"}) + "\n"
        )
        setup_concluded_effort(session_dir, "auth-bug", "Fixed it.", raw_content=raw)
        reopen_effort(session_dir, "auth-bug")

        log_file = session_dir / "efforts" / "auth-bug.jsonl"
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        # Original 2 lines + 1 separator line
        assert len(lines) == 3
        assert "Original message" in lines[0]
        assert "Original reply" in lines[1]

    def test_reopen_appends_separator(self, session_dir):
        """Reopening appends a separator line to the raw log."""
        setup_concluded_effort(session_dir, "auth-bug", "Fixed it.")
        reopen_effort(session_dir, "auth-bug")

        log_file = session_dir / "efforts" / "auth-bug.jsonl"
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        separator = json.loads(lines[-1])
        assert separator["role"] == "system"
        assert "reopened" in separator["content"].lower()

    def test_reopen_non_concluded_fails(self, session_dir):
        """Can't reopen an effort that's still open."""
        open_effort(session_dir, "active-work")
        result = json.loads(reopen_effort(session_dir, "active-work"))
        assert "error" in result

    def test_reopen_nonexistent_fails(self, session_dir):
        """Can't reopen an effort that doesn't exist."""
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "knowledge.yaml").write_text("nodes: []\nedges: []\n")
        result = json.loads(reopen_effort(session_dir, "nope"))
        assert "error" in result

    def test_reopen_removes_from_expanded(self, session_dir):
        """If effort was expanded (read-only view), reopening removes it from expanded set."""
        setup_concluded_effort(session_dir, "auth-bug", "Fixed it.")
        expand_effort(session_dir, "auth-bug")
        assert "auth-bug" in _load_expanded(session_dir)

        reopen_effort(session_dir, "auth-bug")
        assert "auth-bug" not in _load_expanded(session_dir)

    def test_reconclusion_updates_summary(self, session_dir):
        """Re-concluding a reopened effort produces an updated summary."""
        setup_concluded_effort(session_dir, "auth-bug", "Fixed 401 errors.")
        reopen_effort(session_dir, "auth-bug")

        from unittest.mock import patch
        with patch("oi.llm.summarize_effort", return_value="Fixed 401 errors and added retry logic."):
            result = json.loads(close_effort(session_dir, effort_id="auth-bug"))

        assert result["status"] == "concluded"
        assert "retry logic" in result["summary"]


# === Slice 6: Cross-session persistence tests ===

class TestSessionMarker:
    def test_session_marker_appended_to_raw(self, session_dir):
        """Session marker is appended to raw.jsonl on startup."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _append_session_marker(session_dir)

        raw_file = session_dir / "raw.jsonl"
        assert raw_file.exists()
        lines = raw_file.read_text(encoding="utf-8").strip().split("\n")
        marker = json.loads(lines[-1])
        assert marker["role"] == "system"
        assert "New session started" in marker["content"]
        assert "ts" in marker

    def test_multiple_session_markers(self, session_dir):
        """Multiple launches append multiple markers."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _append_session_marker(session_dir)
        _append_session_marker(session_dir)

        raw_file = session_dir / "raw.jsonl"
        lines = raw_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            entry = json.loads(line)
            assert entry["role"] == "system"
            assert "New session started" in entry["content"]


class TestSessionCount:
    def test_session_count_increments(self, session_dir):
        """Session count increments across restarts."""
        assert increment_session_count(session_dir) == 1
        assert increment_session_count(session_dir) == 2
        assert increment_session_count(session_dir) == 3

        state = _load_session_state(session_dir)
        assert state["session_count"] == 3

    def test_session_count_independent_of_turn(self, session_dir):
        """Session count and turn count are independent."""
        increment_turn(session_dir)
        increment_turn(session_dir)
        assert increment_session_count(session_dir) == 1

        state = _load_session_state(session_dir)
        assert state["turn_count"] == 2
        assert state["session_count"] == 1


class TestCrossSessionPersistence:
    def test_efforts_persist_across_sessions(self, session_dir):
        """Efforts created in one session are visible after reload."""
        open_effort(session_dir, "my-task")
        effort = get_open_effort(session_dir)
        assert effort is not None
        assert effort["id"] == "my-task"

        # Simulate restart: reload efforts from same dir
        efforts = _load_efforts(session_dir)
        open_efforts = [e for e in efforts if e.get("status") == "open"]
        assert len(open_efforts) == 1
        assert open_efforts[0]["id"] == "my-task"

    def test_concluded_efforts_persist(self, session_dir):
        """Concluded efforts with summaries persist across sessions."""
        setup_concluded_effort(session_dir, "old-bug", "Fixed the old bug.")

        efforts = _load_efforts(session_dir)
        concluded = [e for e in efforts if e.get("status") == "concluded"]
        assert len(concluded) == 1
        assert concluded[0]["summary"] == "Fixed the old bug."

    def test_turn_counter_persists(self, session_dir):
        """Turn counter survives across sessions."""
        increment_turn(session_dir)
        increment_turn(session_dir)
        increment_turn(session_dir)

        # Simulate restart: reload from same dir
        state = _load_session_state(session_dir)
        assert state["turn_count"] == 3

        # Continue counting
        assert increment_turn(session_dir) == 4


class TestStartupDisplay:
    def test_startup_shows_open_efforts(self, session_dir, capsys):
        """Startup display lists open efforts."""
        open_effort(session_dir, "quantum")
        open_effort(session_dir, "gravity")
        _show_startup(session_dir)
        output = capsys.readouterr().out
        assert "2 open effort(s)" in output
        assert "quantum" in output
        assert "gravity" in output

    def test_startup_shows_concluded_count(self, session_dir, capsys):
        """Startup display shows concluded effort count."""
        setup_concluded_effort(session_dir, "old-a", "Done A")
        setup_concluded_effort(session_dir, "old-b", "Done B")
        _show_startup(session_dir)
        output = capsys.readouterr().out
        assert "2 concluded effort(s) searchable" in output

    def test_startup_empty_session(self, session_dir, capsys):
        """Startup display works with empty session."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _show_startup(session_dir)
        output = capsys.readouterr().out
        assert "open effort" not in output
        assert "concluded" not in output


# === Slice 7a: read_file tests ===

class TestReadFile:
    def test_read_existing_file(self, tmp_path):
        """read_file returns content, path, and size for an existing file."""
        f = tmp_path / "hello.txt"
        f.write_text("Hello, world!", encoding="utf-8")

        result = json.loads(read_file(str(f)))
        assert result["content"] == "Hello, world!"
        assert result["size"] == 13
        assert "error" not in result
        assert "truncated" not in result

    def test_read_nonexistent_file(self, tmp_path):
        """read_file returns error for a nonexistent file."""
        result = json.loads(read_file(str(tmp_path / "nope.txt")))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_read_large_file_truncated(self, tmp_path):
        """read_file truncates content beyond READ_FILE_MAX_CHARS."""
        f = tmp_path / "big.txt"
        content = "x" * (READ_FILE_MAX_CHARS + 500)
        f.write_text(content, encoding="utf-8")

        result = json.loads(read_file(str(f)))
        assert len(result["content"]) == READ_FILE_MAX_CHARS
        assert result["truncated"] is True
        assert result["size"] == READ_FILE_MAX_CHARS + 500

    def test_read_file_resolves_path(self, tmp_path, monkeypatch):
        """read_file resolves relative paths against CWD."""
        f = tmp_path / "data.txt"
        f.write_text("data", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = json.loads(read_file("data.txt"))
        assert result["content"] == "data"

    def test_read_file_via_execute_tool(self, tmp_path, session_dir):
        """read_file is dispatched correctly through execute_tool."""
        f = tmp_path / "test.txt"
        f.write_text("via dispatch", encoding="utf-8")

        result = json.loads(execute_tool(session_dir, "read_file", {"path": str(f)}))
        assert result["content"] == "via dispatch"


# === Slice 7a: run_command tests ===

class TestRunCommand:
    def test_run_simple_command(self):
        """run_command returns stdout for a simple command."""
        result = json.loads(run_command("echo hello"))
        assert "hello" in result["stdout"]
        assert result["exit_code"] == 0

    def test_run_failing_command(self):
        """run_command returns stderr and non-zero exit code for failing commands."""
        result = json.loads(run_command("python -c \"import sys; print('err', file=sys.stderr); sys.exit(1)\""))
        assert result["exit_code"] == 1
        assert "err" in result["stderr"]

    def test_run_command_timeout(self):
        """run_command returns error on timeout."""
        result = json.loads(run_command("python -c \"import time; time.sleep(10)\"", timeout=1))
        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_run_command_confirmation_denied(self):
        """run_command returns error when user denies confirmation."""
        deny_callback = lambda cmd: False
        result = json.loads(run_command("echo hello", confirmation_callback=deny_callback))
        assert "error" in result
        assert "denied" in result["error"].lower()

    def test_run_command_confirmation_approved(self):
        """run_command executes when user approves confirmation."""
        approve_callback = lambda cmd: True
        result = json.loads(run_command("echo approved", confirmation_callback=approve_callback))
        assert "approved" in result["stdout"]
        assert result["exit_code"] == 0

    def test_run_command_no_callback_executes(self):
        """run_command executes without confirmation when no callback provided."""
        result = json.loads(run_command("echo no-callback"))
        assert "no-callback" in result["stdout"]

    def test_run_command_truncates_long_output(self):
        """run_command truncates stdout beyond RUN_COMMAND_MAX_CHARS."""
        # Generate output longer than the limit
        result = json.loads(run_command(
            f"python -c \"print('x' * {RUN_COMMAND_MAX_CHARS + 500})\""
        ))
        assert len(result["stdout"]) <= RUN_COMMAND_MAX_CHARS + 1  # +1 for trailing newline before truncation
        assert result.get("stdout_truncated") is True

    def test_run_command_via_execute_tool(self, session_dir):
        """run_command is dispatched correctly through execute_tool with callback."""
        approve = lambda cmd: True
        result = json.loads(execute_tool(
            session_dir, "run_command",
            {"command": "echo dispatch-test"},
            confirmation_callback=approve,
        ))
        assert "dispatch-test" in result["stdout"]


# === Slice 7b: write_file tests ===

class TestWriteFile:
    def test_write_new_file(self, tmp_path):
        """write_file creates a new file and returns status/path/size."""
        target = tmp_path / "hello.txt"
        approve = lambda desc: True
        result = json.loads(write_file(str(target), "Hello World", confirmation_callback=approve))
        assert result["status"] == "written"
        assert result["size"] == 11
        assert target.read_text(encoding="utf-8") == "Hello World"

    def test_write_overwrites_existing(self, tmp_path):
        """write_file replaces existing file content."""
        target = tmp_path / "data.txt"
        target.write_text("old content", encoding="utf-8")
        approve = lambda desc: True
        result = json.loads(write_file(str(target), "new content", confirmation_callback=approve))
        assert result["status"] == "written"
        assert result["size"] == 11
        assert target.read_text(encoding="utf-8") == "new content"

    def test_write_creates_parent_dirs(self, tmp_path):
        """write_file creates parent directories if they don't exist."""
        target = tmp_path / "a" / "b" / "c" / "deep.txt"
        approve = lambda desc: True
        result = json.loads(write_file(str(target), "deep", confirmation_callback=approve))
        assert result["status"] == "written"
        assert target.read_text(encoding="utf-8") == "deep"

    def test_write_confirmation_denied(self, tmp_path):
        """write_file returns error when callback returns False."""
        target = tmp_path / "denied.txt"
        deny = lambda desc: False
        result = json.loads(write_file(str(target), "content", confirmation_callback=deny))
        assert "error" in result
        assert "denied" in result["error"].lower()
        assert not target.exists()

    def test_write_confirmation_message_new_file(self, tmp_path):
        """Confirmation message for a new file includes 'Write' and char count."""
        target = tmp_path / "new.txt"
        captured = {}
        def capture(desc):
            captured["desc"] = desc
            return True
        write_file(str(target), "hello", confirmation_callback=capture)
        assert "Write:" in captured["desc"]
        assert "new file" in captured["desc"]
        assert "5 chars" in captured["desc"]

    def test_write_confirmation_message_overwrite(self, tmp_path):
        """Confirmation message for overwrite includes old and new sizes."""
        target = tmp_path / "exist.txt"
        target.write_text("short", encoding="utf-8")
        captured = {}
        def capture(desc):
            captured["desc"] = desc
            return True
        write_file(str(target), "much longer content here", confirmation_callback=capture)
        assert "Overwrite:" in captured["desc"]
        assert "existing" in captured["desc"]

    def test_write_via_execute_tool(self, tmp_path, session_dir):
        """write_file is dispatched correctly through execute_tool."""
        target = tmp_path / "dispatch.txt"
        approve = lambda desc: True
        result = json.loads(execute_tool(
            session_dir, "write_file",
            {"path": str(target), "content": "via dispatch"},
            confirmation_callback=approve,
        ))
        assert result["status"] == "written"
        assert target.read_text(encoding="utf-8") == "via dispatch"


# === Slice 7b: append_file tests ===

class TestAppendFile:
    def test_append_to_existing_file(self, tmp_path):
        """append_file adds content without replacing, returns total size."""
        target = tmp_path / "log.txt"
        target.write_text("line1\n", encoding="utf-8")
        approve = lambda desc: True
        result = json.loads(append_file(str(target), "line2\n", confirmation_callback=approve))
        assert result["status"] == "appended"
        assert target.read_text(encoding="utf-8") == "line1\nline2\n"
        assert result["size"] == target.stat().st_size

    def test_append_creates_file_if_missing(self, tmp_path):
        """append_file creates new file when appending to nonexistent path."""
        target = tmp_path / "new_log.txt"
        approve = lambda desc: True
        result = json.loads(append_file(str(target), "first entry\n", confirmation_callback=approve))
        assert result["status"] == "appended"
        assert target.read_text(encoding="utf-8") == "first entry\n"

    def test_append_creates_parent_dirs(self, tmp_path):
        """append_file creates parent directories if needed."""
        target = tmp_path / "deep" / "nested" / "log.txt"
        approve = lambda desc: True
        result = json.loads(append_file(str(target), "entry\n", confirmation_callback=approve))
        assert result["status"] == "appended"
        assert target.read_text(encoding="utf-8") == "entry\n"

    def test_append_confirmation_denied(self, tmp_path):
        """append_file returns error when callback returns False."""
        target = tmp_path / "denied.txt"
        deny = lambda desc: False
        result = json.loads(append_file(str(target), "content", confirmation_callback=deny))
        assert "error" in result
        assert "denied" in result["error"].lower()
        assert not target.exists()

    def test_append_confirmation_message(self, tmp_path):
        """Confirmation message includes 'Append' and char count."""
        target = tmp_path / "log.txt"
        captured = {}
        def capture(desc):
            captured["desc"] = desc
            return True
        append_file(str(target), "12345", confirmation_callback=capture)
        assert "Append:" in captured["desc"]
        assert "+5 chars" in captured["desc"]

    def test_append_via_execute_tool(self, tmp_path, session_dir):
        """append_file is dispatched correctly through execute_tool."""
        target = tmp_path / "dispatch.txt"
        target.write_text("existing\n", encoding="utf-8")
        approve = lambda desc: True
        result = json.loads(execute_tool(
            session_dir, "append_file",
            {"path": str(target), "content": "appended\n"},
            confirmation_callback=approve,
        ))
        assert result["status"] == "appended"
        assert target.read_text(encoding="utf-8") == "existing\nappended\n"


# === Slice 8a: Knowledge store tests ===

class TestKnowledgeStore:
    def test_load_empty_knowledge(self, session_dir):
        """Loading from non-existent file returns empty structure."""
        session_dir.mkdir(parents=True, exist_ok=True)
        knowledge = _load_knowledge(session_dir)
        assert knowledge == {"nodes": [], "edges": []}

    def test_save_and_load_knowledge(self, session_dir):
        """Round-trip save/load preserves data."""
        session_dir.mkdir(parents=True, exist_ok=True)
        knowledge = {
            "nodes": [{"id": "fact-001", "type": "fact", "summary": "Test fact", "status": "active"}],
            "edges": [],
        }
        _save_knowledge(session_dir, knowledge)
        loaded = _load_knowledge(session_dir)
        assert len(loaded["nodes"]) == 1
        assert loaded["nodes"][0]["summary"] == "Test fact"

    def test_add_knowledge_creates_node(self, session_dir):
        """add_knowledge creates a fact node with correct fields."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(add_knowledge(session_dir, "fact", "API uses JWT with RS256"))
        assert result["status"] == "added"
        assert result["node_id"] == "fact-001"
        assert result["node_type"] == "fact"

        knowledge = _load_knowledge(session_dir)
        assert len(knowledge["nodes"]) == 1
        node = knowledge["nodes"][0]
        assert node["id"] == "fact-001"
        assert node["type"] == "fact"
        assert node["summary"] == "API uses JWT with RS256"
        assert node["status"] == "active"
        assert node["created"] is not None

    def test_add_knowledge_auto_id(self, session_dir):
        """Sequential IDs are generated per type."""
        session_dir.mkdir(parents=True, exist_ok=True)
        r1 = json.loads(add_knowledge(session_dir, "fact", "First fact"))
        r2 = json.loads(add_knowledge(session_dir, "fact", "Second fact"))
        r3 = json.loads(add_knowledge(session_dir, "preference", "Tabs over spaces"))
        assert r1["node_id"] == "fact-001"
        assert r2["node_id"] == "fact-002"
        assert r3["node_id"] == "preference-001"

    def test_add_knowledge_with_edges(self, session_dir):
        """related_to creates edges in the knowledge graph."""
        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "API uses JWT")
        result = json.loads(add_knowledge(
            session_dir, "fact", "JWT uses RS256 signing",
            related_to=["fact-001"], edge_type="supports",
        ))
        assert result["node_id"] == "fact-002"

        knowledge = _load_knowledge(session_dir)
        assert len(knowledge["edges"]) == 1
        edge = knowledge["edges"][0]
        assert edge["source"] == "fact-002"
        assert edge["target"] == "fact-001"
        assert edge["type"] == "supports"

    def test_add_knowledge_with_source(self, session_dir):
        """Source field is stored on the node."""
        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "decision", "Use PostgreSQL", source="db-selection effort")
        knowledge = _load_knowledge(session_dir)
        assert knowledge["nodes"][0]["source"] == "db-selection effort"

    def test_add_knowledge_via_execute_tool(self, session_dir):
        """add_knowledge dispatches correctly through execute_tool."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(execute_tool(
            session_dir, "add_knowledge",
            {"node_type": "preference", "summary": "Dark mode preferred"},
        ))
        assert result["status"] == "added"
        assert result["node_id"] == "preference-001"

    def test_knowledge_in_context(self, session_dir):
        """_build_messages includes knowledge section in system prompt."""
        from oi.orchestrator import _build_messages
        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "API uses JWT with RS256")
        add_knowledge(session_dir, "preference", "Tabs over spaces")

        messages = _build_messages(session_dir)
        system_content = messages[0]["content"]
        assert "Knowledge graph:" in system_content
        assert "[fact] API uses JWT with RS256" in system_content
        assert "[preference] Tabs over spaces" in system_content


# === Slice 8b: Knowledge extraction tests ===

class TestExtractKnowledgeLLM:
    """Test extract_knowledge() with mocked LLM."""

    def test_parses_valid_json(self):
        """Valid JSON array from LLM is parsed correctly."""
        from unittest.mock import patch
        from oi.llm import extract_knowledge

        mock_response = '[{"node_type": "fact", "summary": "Python uses GIL"}, {"node_type": "decision", "summary": "Use PostgreSQL for storage"}]'
        with patch("oi.llm.chat", return_value=mock_response):
            result = extract_knowledge("some effort content", "test-effort")
        assert len(result) == 2
        assert result[0] == {"node_type": "fact", "summary": "Python uses GIL"}
        assert result[1] == {"node_type": "decision", "summary": "Use PostgreSQL for storage"}

    def test_returns_empty_on_bad_json(self):
        """Non-JSON response returns empty list."""
        from unittest.mock import patch
        from oi.llm import extract_knowledge

        with patch("oi.llm.chat", return_value="I found some interesting facts..."):
            result = extract_knowledge("content", "test-effort")
        assert result == []

    def test_strips_markdown_fences(self):
        """JSON wrapped in markdown code fences is parsed correctly."""
        from unittest.mock import patch
        from oi.llm import extract_knowledge

        mock_response = '```json\n[{"node_type": "fact", "summary": "Redis uses single thread"}]\n```'
        with patch("oi.llm.chat", return_value=mock_response):
            result = extract_knowledge("content", "test-effort")
        assert len(result) == 1
        assert result[0]["summary"] == "Redis uses single thread"

    def test_filters_invalid_node_types(self):
        """Invalid node_type values are filtered out, valid ones kept."""
        from unittest.mock import patch
        from oi.llm import extract_knowledge

        mock_response = '[{"node_type": "solution", "summary": "bad type"}, {"node_type": "fact", "summary": "valid fact"}]'
        with patch("oi.llm.chat", return_value=mock_response):
            result = extract_knowledge("content", "test-effort")
        assert len(result) == 1
        assert result[0]["node_type"] == "fact"

    def test_returns_empty_on_exception(self):
        """LLM raising exception returns empty list."""
        from unittest.mock import patch
        from oi.llm import extract_knowledge

        with patch("oi.llm.chat", side_effect=RuntimeError("API error")):
            result = extract_knowledge("content", "test-effort")
        assert result == []


class TestCloseEffortKnowledgeExtraction:
    """Test that close_effort integrates knowledge extraction."""

    def test_close_effort_extracts_knowledge_nodes(self, session_dir):
        """Extracted nodes are saved to knowledge.yaml with source=effort_id."""
        from unittest.mock import patch

        # Open effort and write substantial content
        open_effort(session_dir, "db-design")
        effort_file = session_dir / "efforts" / "db-design.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "We decided to use PostgreSQL for all persistent storage because it handles JSON well.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Good choice. PostgreSQL's JSONB type is great for semi-structured data.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        mock_nodes = [{"node_type": "decision", "summary": "Use PostgreSQL for all persistent storage"}]
        with patch("oi.llm.summarize_effort", return_value="Discussed database choice."):
            with patch("oi.llm.extract_knowledge", return_value=mock_nodes):
                result = json.loads(close_effort(session_dir, effort_id="db-design"))

        assert result["status"] == "concluded"
        assert len(result["knowledge_extracted"]) == 1
        assert result["knowledge_extracted"][0]["node_type"] == "decision"
        assert result["knowledge_extracted"][0]["summary"] == "Use PostgreSQL for all persistent storage"
        assert "node_id" in result["knowledge_extracted"][0]

        # Verify persisted to knowledge.yaml (effort node + extracted decision node)
        knowledge = _load_knowledge(session_dir)
        non_effort_nodes = [n for n in knowledge["nodes"] if n.get("type") != "effort"]
        assert len(non_effort_nodes) == 1
        assert non_effort_nodes[0]["source"] == "db-design"

    def test_close_effort_succeeds_when_extraction_returns_empty(self, session_dir):
        """Close succeeds when extract_knowledge returns []."""
        from unittest.mock import patch

        open_effort(session_dir, "trivial")
        effort_file = session_dir / "efforts" / "trivial.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "Just checking something quick about the API endpoint.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "The endpoint is /api/v1/users.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        with patch("oi.llm.summarize_effort", return_value="Quick API check."):
            with patch("oi.llm.extract_knowledge", return_value=[]):
                result = json.loads(close_effort(session_dir, effort_id="trivial"))

        assert result["status"] == "concluded"
        assert result["knowledge_extracted"] == []

    def test_close_effort_skips_extraction_for_short_effort(self, session_dir):
        """Short content skips both summarization and extraction."""
        from unittest.mock import patch

        open_effort(session_dir, "tiny")
        effort_file = session_dir / "efforts" / "tiny.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text('{"role":"user","content":"hi","ts":"t1"}\n', encoding="utf-8")

        with patch("oi.llm.summarize_effort") as mock_summarize:
            with patch("oi.llm.extract_knowledge") as mock_extract:
                result = json.loads(close_effort(session_dir, effort_id="tiny"))

        assert result["status"] == "concluded"
        assert result["knowledge_extracted"] == []
        mock_summarize.assert_not_called()
        mock_extract.assert_not_called()


# === Slice 8c: Node linking integration tests ===

class TestNodeLinking:
    """Integration tests for auto-linking in add_knowledge."""

    def test_add_knowledge_triggers_linking(self, session_dir):
        """Mock run_linking returns supports edge → edge persisted in knowledge.yaml."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "API uses JWT tokens")

        mock_links = [{"target_id": "fact-001", "edge_type": "supports", "reasoning": "Related JWT"}]
        with patch("oi.linker.run_linking", return_value=mock_links):
            result = json.loads(add_knowledge(session_dir, "fact", "JWT uses RS256 signing"))

        assert result["status"] == "added"
        assert result["node_id"] == "fact-002"
        assert len(result.get("edges_created", [])) == 1
        assert result["edges_created"][0]["edge_type"] == "supports"

        knowledge = _load_knowledge(session_dir)
        auto_edges = [e for e in knowledge["edges"] if e["source"] == "fact-002"]
        assert len(auto_edges) == 1
        assert auto_edges[0]["target"] == "fact-001"
        assert auto_edges[0]["type"] == "supports"

    def test_add_knowledge_linking_creates_contradicts_edge(self, session_dir):
        """Contradicts edge sets has_contradiction flag on both nodes."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "decision", "Use JWT tokens for auth")

        mock_links = [{"target_id": "decision-001", "edge_type": "contradicts", "reasoning": "Conflicting"}]
        with patch("oi.linker.run_linking", return_value=mock_links):
            result = json.loads(add_knowledge(session_dir, "decision", "Use session cookies for auth"))

        assert result["edges_created"][0]["edge_type"] == "contradicts"

        knowledge = _load_knowledge(session_dir)
        new_node = next(n for n in knowledge["nodes"] if n["id"] == "decision-002")
        old_node = next(n for n in knowledge["nodes"] if n["id"] == "decision-001")
        assert new_node.get("has_contradiction") is True
        assert old_node.get("has_contradiction") is True

    def test_add_knowledge_linking_skips_empty_graph(self, session_dir):
        """First node → run_linking gets graph with only self, returns empty."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        with patch("oi.linker.run_linking", return_value=[]) as mock_link:
            result = json.loads(add_knowledge(session_dir, "fact", "First fact ever"))

        assert result["status"] == "added"
        assert "edges_created" not in result
        mock_link.assert_called_once()

    def test_add_knowledge_linking_fails_gracefully(self, session_dir):
        """run_linking raises → node still added, no edges."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "Existing fact")

        with patch("oi.linker.run_linking", side_effect=RuntimeError("LLM down")):
            result = json.loads(add_knowledge(session_dir, "fact", "New fact"))

        assert result["status"] == "added"
        assert result["node_id"] == "fact-002"
        assert "edges_created" not in result

        knowledge = _load_knowledge(session_dir)
        assert len(knowledge["nodes"]) == 2

    def test_add_knowledge_no_duplicate_edges(self, session_dir):
        """Manual related_to + auto-link to same target = one edge."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "API uses JWT tokens")

        mock_links = [{"target_id": "fact-001", "edge_type": "supports", "reasoning": "Related"}]
        with patch("oi.linker.run_linking", return_value=mock_links):
            result = json.loads(add_knowledge(
                session_dir, "fact", "JWT uses RS256 signing",
                related_to=["fact-001"], edge_type="supports",
            ))

        knowledge = _load_knowledge(session_dir)
        edges_from_002 = [e for e in knowledge["edges"] if e["source"] == "fact-002"]
        # Should have only the manual edge, auto-link skipped because target already in edge set
        assert len(edges_from_002) == 1
        # edges_created should be empty since the auto-link was a duplicate
        assert result.get("edges_created") is None or len(result.get("edges_created", [])) == 0

    def test_add_knowledge_result_includes_edges_created(self, session_dir):
        """Return JSON has edges_created field with target_id, edge_type, reasoning."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "First fact")

        mock_links = [
            {"target_id": "fact-001", "edge_type": "supports", "reasoning": "Both about same topic"},
        ]
        with patch("oi.linker.run_linking", return_value=mock_links):
            result = json.loads(add_knowledge(session_dir, "fact", "Second fact"))

        assert "edges_created" in result
        assert len(result["edges_created"]) == 1
        edge = result["edges_created"][0]
        assert edge["target_id"] == "fact-001"
        assert edge["edge_type"] == "supports"
        assert edge["reasoning"] == "Both about same topic"

    def test_add_knowledge_persists_reasoning(self, session_dir):
        """Auto-linked edges persist reasoning field in knowledge.yaml."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "API uses JWT tokens")

        mock_links = [{"target_id": "fact-001", "edge_type": "supports", "reasoning": "Both about JWT auth"}]
        with patch("oi.linker.run_linking", return_value=mock_links):
            add_knowledge(session_dir, "fact", "JWT uses RS256 signing")

        knowledge = _load_knowledge(session_dir)
        auto_edges = [e for e in knowledge["edges"] if e["source"] == "fact-002"]
        assert len(auto_edges) == 1
        assert auto_edges[0]["reasoning"] == "Both about JWT auth"

    def test_add_knowledge_result_includes_confidence(self, session_dir):
        """add_knowledge result includes confidence dict with level."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        # First node — no edges → low
        result1 = json.loads(add_knowledge(session_dir, "fact", "First fact", source="effort-a"))
        assert "confidence" in result1
        assert result1["confidence"]["level"] == "low"

        # Second node with support edge → medium for the new node? No — the new node
        # supports fact-001, not the other way around. The new node has 0 inbound → low.
        mock_links = [{"target_id": "fact-001", "edge_type": "supports", "reasoning": "related"}]
        with patch("oi.linker.run_linking", return_value=mock_links):
            result2 = json.loads(add_knowledge(session_dir, "fact", "Second fact", source="effort-b"))
        assert "confidence" in result2
        # fact-002 has 0 inbound supports (it supports fact-001, not vice versa)
        assert result2["confidence"]["level"] == "low"

    def test_existing_edges_without_reasoning_work(self, session_dir):
        """Edges created before reasoning field was added still work (no KeyError)."""
        session_dir.mkdir(parents=True, exist_ok=True)

        # Manually create a graph with an edge missing "reasoning"
        knowledge = {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old fact", "status": "active", "source": "effort-a"},
                {"id": "fact-002", "type": "fact", "summary": "Another fact", "status": "active", "source": "effort-b"},
            ],
            "edges": [
                {"source": "fact-002", "target": "fact-001", "type": "supports", "created": "2024-01-01"},
                # Note: no "reasoning" field — simulates pre-8d edge
            ],
        }
        _save_knowledge(session_dir, knowledge)

        # compute_confidence should still work (no KeyError)
        # Edges without reasoning get 0.5x weight (Decision 020)
        from oi.confidence import compute_confidence
        conf = compute_confidence("fact-001", knowledge)
        # Still medium: independent_sources >= 2 (effort-a + effort-b)
        assert conf["level"] == "medium"
        assert conf["inbound_supports"] == pytest.approx(0.5, abs=0.15)


# === Slice 8f: Expanded knowledge state tests ===

class TestExpandedKnowledgeState:
    def test_load_empty_expanded_knowledge(self, session_dir):
        """Loading expanded knowledge from empty session returns empty set."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = _load_expanded_knowledge(session_dir)
        assert result == set()

    def test_save_and_load_expanded_knowledge(self, session_dir):
        """Round-trip save/load preserves expanded knowledge set."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _save_expanded_knowledge(session_dir, {"fact-001", "decision-002"})
        loaded = _load_expanded_knowledge(session_dir)
        assert loaded == {"fact-001", "decision-002"}

    def test_expanded_knowledge_preserves_effort_state(self, session_dir):
        """Saving expanded knowledge doesn't clobber effort expanded state."""
        session_dir.mkdir(parents=True, exist_ok=True)
        # Set up effort expanded state first
        _save_expanded(session_dir, {"effort-a"}, last_referenced_turn={"effort-a": 5})

        # Save knowledge state
        _save_expanded_knowledge(session_dir, {"fact-001"}, last_expanded_turn={"fact-001": 3})

        # Effort state should be preserved
        effort_expanded = _load_expanded(session_dir)
        assert "effort-a" in effort_expanded

        # Knowledge state should also be there
        knowledge_expanded = _load_expanded_knowledge(session_dir)
        assert "fact-001" in knowledge_expanded

    def test_expanded_knowledge_preserves_timestamps(self, session_dir):
        """Saving expanded knowledge preserves existing expanded_knowledge_at timestamps."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _save_expanded_knowledge(session_dir, {"fact-001"}, last_expanded_turn={"fact-001": 1})
        state1 = _load_expanded_state(session_dir)
        ts = state1["expanded_knowledge_at"]["fact-001"]

        # Save again with fact-001 still present — timestamp preserved
        _save_expanded_knowledge(session_dir, {"fact-001", "fact-002"}, last_expanded_turn={"fact-001": 1, "fact-002": 3})
        state2 = _load_expanded_state(session_dir)
        assert state2["expanded_knowledge_at"]["fact-001"] == ts
        assert "fact-002" in state2["expanded_knowledge_at"]


# === Slice 8f: expand_knowledge / collapse_knowledge tests ===

class TestExpandKnowledge:
    def test_expand_session_sourced_node(self, session_dir):
        """Expanding a session-sourced node returns fragment info."""
        from oi.session_log import create_session_log, log_event
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)

        # Log conversation then add_knowledge with session_id
        log_event(session_dir, sid, "user-message", {"content": "Python uses GIL"})
        log_event(session_dir, sid, "assistant-message", {"content": "Noted as a fact"})
        add_knowledge(session_dir, "fact", "Python uses GIL for thread safety", session_id=sid)
        # Manually log the node-created event (normally done by orchestrator)
        log_event(session_dir, sid, "node-created", {"node_id": "fact-001", "node_type": "fact"})

        result = json.loads(expand_knowledge(session_dir, "fact-001"))
        assert result["status"] == "expanded"
        assert result["node_id"] == "fact-001"
        assert result["session_id"] == sid
        assert result["messages_loaded"] == 2

        # Should be in expanded knowledge state
        assert "fact-001" in _load_expanded_knowledge(session_dir)

    def test_expand_effort_sourced_node(self, session_dir):
        """Expanding an effort-sourced node delegates to expand_effort."""
        setup_concluded_effort(session_dir, "db-design", "Database design decisions.")
        # Add knowledge with source matching the effort
        add_knowledge(session_dir, "decision", "Use PostgreSQL", source="db-design")

        result = json.loads(expand_knowledge(session_dir, "decision-001"))
        assert result["status"] == "expanded"
        assert result["via_effort"] == "db-design"
        assert result["node_id"] == "decision-001"
        # effort should be expanded
        assert "db-design" in _load_expanded(session_dir)

    def test_expand_nonexistent_node_fails(self, session_dir):
        """Expanding a non-existent node returns error."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(expand_knowledge(session_dir, "fact-999"))
        assert "error" in result

    def test_expand_superseded_node_fails(self, session_dir):
        """Cannot expand a superseded node."""
        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "Old fact")
        add_knowledge(session_dir, "fact", "New fact", supersedes=["fact-001"])
        result = json.loads(expand_knowledge(session_dir, "fact-001"))
        assert "error" in result
        assert "superseded" in result["error"]

    def test_expand_already_expanded_fails(self, session_dir):
        """Cannot expand a node that's already expanded."""
        from oi.session_log import create_session_log, log_event
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)

        log_event(session_dir, sid, "user-message", {"content": "test"})
        log_event(session_dir, sid, "assistant-message", {"content": "noted"})
        add_knowledge(session_dir, "fact", "Test fact", session_id=sid)
        log_event(session_dir, sid, "node-created", {"node_id": "fact-001", "node_type": "fact"})

        expand_knowledge(session_dir, "fact-001")
        result = json.loads(expand_knowledge(session_dir, "fact-001"))
        assert "error" in result
        assert "already expanded" in result["error"]

    def test_expand_no_traceable_source_fails(self, session_dir):
        """Node with neither source nor created_in_session returns error."""
        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "Orphan fact")
        result = json.loads(expand_knowledge(session_dir, "fact-001"))
        assert "error" in result
        assert "no traceable source" in result["error"]

    def test_expand_effort_already_expanded_via_effort(self, session_dir):
        """If effort is already expanded, expand_knowledge reports the error."""
        setup_concluded_effort(session_dir, "db-design", "Database decisions.")
        add_knowledge(session_dir, "decision", "Use PostgreSQL", source="db-design")
        expand_effort(session_dir, "db-design")

        result = json.loads(expand_knowledge(session_dir, "decision-001"))
        assert "error" in result
        assert "already expanded" in result["error"]

    def test_expand_knowledge_via_execute_tool(self, session_dir):
        """expand_knowledge dispatches correctly through execute_tool."""
        from oi.session_log import create_session_log, log_event
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)
        log_event(session_dir, sid, "user-message", {"content": "test msg"})
        log_event(session_dir, sid, "assistant-message", {"content": "test reply"})
        add_knowledge(session_dir, "fact", "Test fact", session_id=sid)
        log_event(session_dir, sid, "node-created", {"node_id": "fact-001", "node_type": "fact"})

        result = json.loads(execute_tool(session_dir, "expand_knowledge", {"node_id": "fact-001"}))
        assert result["status"] == "expanded"


class TestCollapseKnowledge:
    def test_collapse_expanded_knowledge(self, session_dir):
        """Collapse succeeds and removes from expanded knowledge set."""
        from oi.session_log import create_session_log, log_event
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)
        log_event(session_dir, sid, "user-message", {"content": "test"})
        log_event(session_dir, sid, "assistant-message", {"content": "noted"})
        add_knowledge(session_dir, "fact", "Collapsible fact", session_id=sid)
        log_event(session_dir, sid, "node-created", {"node_id": "fact-001", "node_type": "fact"})
        expand_knowledge(session_dir, "fact-001")
        assert "fact-001" in _load_expanded_knowledge(session_dir)

        result = json.loads(collapse_knowledge(session_dir, "fact-001"))
        assert result["status"] == "collapsed"
        assert "fact-001" not in _load_expanded_knowledge(session_dir)

    def test_collapse_non_expanded_fails(self, session_dir):
        """Cannot collapse a node that's not expanded."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(collapse_knowledge(session_dir, "fact-999"))
        assert "error" in result
        assert "not currently expanded" in result["error"]

    def test_collapse_knowledge_via_execute_tool(self, session_dir):
        """collapse_knowledge dispatches correctly through execute_tool."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _save_expanded_knowledge(session_dir, {"fact-001"})
        result = json.loads(execute_tool(session_dir, "collapse_knowledge", {"node_id": "fact-001"}))
        assert result["status"] == "collapsed"


# === Slice 8f: close_effort session_id forwarding ===

class TestCloseEffortSessionId:
    def test_close_effort_forwards_session_id(self, session_dir):
        """close_effort passes session_id to add_knowledge for auto-extracted nodes."""
        from unittest.mock import patch
        from oi.session_log import create_session_log
        session_dir.mkdir(parents=True, exist_ok=True)
        sid = create_session_log(session_dir)

        open_effort(session_dir, "test-effort")
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "We decided to use Redis for caching because it's fast.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Redis is great for caching with TTL support.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        mock_nodes = [{"node_type": "decision", "summary": "Use Redis for caching"}]
        with patch("oi.llm.summarize_effort", return_value="Discussed caching."):
            with patch("oi.llm.extract_knowledge", return_value=mock_nodes):
                close_effort(session_dir, effort_id="test-effort", session_id=sid)

        knowledge = _load_knowledge(session_dir)
        node = knowledge["nodes"][0]
        assert node.get("created_in_session") == sid

    def test_close_effort_without_session_id_still_works(self, session_dir):
        """close_effort works without session_id (backwards compatible)."""
        from unittest.mock import patch
        open_effort(session_dir, "test-effort")
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "Did some work on refactoring the authentication module.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Completed the refactoring.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        mock_nodes = [{"node_type": "fact", "summary": "Refactored auth module"}]
        with patch("oi.llm.summarize_effort", return_value="Refactored auth."):
            with patch("oi.llm.extract_knowledge", return_value=mock_nodes):
                result = json.loads(close_effort(session_dir, effort_id="test-effort"))
        assert result["status"] == "concluded"

        knowledge = _load_knowledge(session_dir)
        node = knowledge["nodes"][0]
        assert "created_in_session" not in node


# === Provenance forwarding in close_effort ===

class TestCloseEffortProvenance:
    def test_close_effort_stamps_provenance_on_extracted_nodes(self, session_dir):
        """close_effort passes provenance_uri to add_knowledge for auto-extracted nodes."""
        from unittest.mock import patch
        open_effort(session_dir, "test-effort")
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "We decided to use Redis for caching.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Redis is great for caching.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        mock_nodes = [{"node_type": "decision", "summary": "Use Redis for caching"}]
        prov_uri = "chatlog://claude-code/abc123:L42"
        with patch("oi.llm.summarize_effort", return_value="Discussed caching."):
            with patch("oi.llm.extract_knowledge", return_value=mock_nodes):
                close_effort(session_dir, effort_id="test-effort", provenance_uri=prov_uri)

        knowledge = _load_knowledge(session_dir)
        # Find the extracted node (not the effort node)
        extracted = [n for n in knowledge["nodes"] if n["type"] == "decision"]
        assert len(extracted) == 1
        assert extracted[0]["provenance_uri"] == prov_uri


# === Slice 8g: Pattern detection in close_effort ===

class TestCloseEffortPatternDetection:
    def test_close_effort_triggers_pattern_detection(self, session_dir):
        """close_effort triggers detect_patterns when extraction yields nodes."""
        from unittest.mock import patch
        open_effort(session_dir, "test-effort")
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "Worked on auth module refactoring.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Done with refactoring.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        mock_nodes = [{"node_type": "fact", "summary": "Auth uses JWT"}]
        mock_patterns = [{"action": "created", "principle_id": "principle-001", "instance_count": 3, "summary": "Always validate tokens"}]
        with patch("oi.llm.summarize_effort", return_value="Refactored auth."):
            with patch("oi.llm.extract_knowledge", return_value=mock_nodes):
                with patch("oi.patterns.detect_patterns", return_value=mock_patterns):
                    result = json.loads(close_effort(session_dir, effort_id="test-effort"))

        assert result["status"] == "concluded"
        assert "patterns_detected" in result
        assert len(result["patterns_detected"]) == 1
        assert result["patterns_detected"][0]["action"] == "created"

    def test_pattern_detection_best_effort(self, session_dir):
        """detect_patterns raises → close_effort succeeds without patterns."""
        from unittest.mock import patch
        open_effort(session_dir, "test-effort")
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "Did auth work.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Done.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        mock_nodes = [{"node_type": "fact", "summary": "Auth uses JWT"}]
        with patch("oi.llm.summarize_effort", return_value="Auth work."):
            with patch("oi.llm.extract_knowledge", return_value=mock_nodes):
                with patch("oi.patterns.detect_patterns", side_effect=Exception("boom")):
                    result = json.loads(close_effort(session_dir, effort_id="test-effort"))

        assert result["status"] == "concluded"
        assert "patterns_detected" not in result

    def test_no_patterns_when_no_extraction(self, session_dir):
        """Short effort → no extraction → no pattern detection."""
        open_effort(session_dir, "test-effort")
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text("short\n", encoding="utf-8")

        result = json.loads(close_effort(session_dir, effort_id="test-effort"))
        assert result["status"] == "concluded"
        assert "patterns_detected" not in result

    def test_no_patterns_when_extraction_empty(self, session_dir):
        """extract_knowledge returns [] → no pattern detection called."""
        from unittest.mock import patch
        open_effort(session_dir, "test-effort")
        effort_file = session_dir / "efforts" / "test-effort.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "Some conversation about nothing.", "ts": "t1"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Nothing to extract.", "ts": "t2"}) + "\n",
            encoding="utf-8",
        )

        with patch("oi.llm.summarize_effort", return_value="Nothing happened."):
            with patch("oi.llm.extract_knowledge", return_value=[]):
                with patch("oi.patterns.detect_patterns") as mock_detect:
                    result = json.loads(close_effort(session_dir, effort_id="test-effort"))

        assert result["status"] == "concluded"
        assert "patterns_detected" not in result
        mock_detect.assert_not_called()


# === because_of edge type in tool definitions ===

class TestBecauseOfToolDefinition:
    def test_because_of_in_edge_type_enum(self):
        """Verify because_of is in the add_knowledge tool definition enum."""
        from oi.tools import TOOL_DEFINITIONS

        add_knowledge_def = None
        for tool in TOOL_DEFINITIONS:
            if tool["function"]["name"] == "add_knowledge":
                add_knowledge_def = tool
                break

        assert add_knowledge_def is not None
        edge_type_enum = add_knowledge_def["function"]["parameters"]["properties"]["edge_type"]["enum"]
        assert "because_of" in edge_type_enum
