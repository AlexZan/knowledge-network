"""Unit tests for tool functions (no LLM needed)."""

import json
import pytest

from helpers import setup_concluded_effort
from oi.tools import (
    open_effort, close_effort, effort_status,
    get_open_effort, get_active_effort, get_all_open_efforts,
    expand_effort, collapse_effort, switch_effort, search_efforts,
    reopen_effort,
)
from oi.state import (
    _load_expanded, _save_expanded, _load_expanded_state,
    _load_session_state, _save_session_state, increment_turn,
)


@pytest.fixture
def session_dir(tmp_path):
    """Create a clean session directory."""
    return tmp_path / "session"


# === Slice 1 tests (updated for multi-effort) ===

class TestOpenEffort:
    def test_open_effort_creates_manifest(self, session_dir):
        result = json.loads(open_effort(session_dir, "auth-bug"))
        assert result["status"] == "opened"
        assert result["effort_id"] == "auth-bug"

        manifest = (session_dir / "manifest.yaml").read_text()
        assert "auth-bug" in manifest
        assert "open" in manifest

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
        (session_dir / "manifest.yaml").write_text("efforts: []\n")
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
        (session_dir / "manifest.yaml").write_text("efforts: []\n")
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
        (session_dir / "manifest.yaml").write_text("efforts: []\n")
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
