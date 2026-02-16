"""Unit tests for tool functions (no LLM needed)."""

import json
import pytest
from pathlib import Path

from oi.tools import (
    open_effort, close_effort, effort_status,
    get_open_effort, get_active_effort, get_all_open_efforts,
    expand_effort, collapse_effort, switch_effort,
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
        open_effort(session_dir, "old")
        # Manually conclude it
        import yaml
        session_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"efforts": [{"id": "old", "status": "concluded", "summary": "Done."}]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (session_dir / "efforts").mkdir(exist_ok=True)
        (session_dir / "efforts" / "old.jsonl").write_text('{"role":"user","content":"test","ts":"t"}\n')

        expand_effort(session_dir, "old")
        result = json.loads(effort_status(session_dir))
        old_entry = [e for e in result["efforts"] if e["id"] == "old"][0]
        assert old_entry.get("expanded") is True


# === Slice 2: Expansion tests ===

class TestExpandEffort:
    def _setup_concluded_effort(self, session_dir, effort_id="auth-bug", content=None):
        """Helper to create a concluded effort with a raw log."""
        import yaml
        session_dir.mkdir(parents=True, exist_ok=True)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(exist_ok=True)

        if content is None:
            content = (
                '{"role":"user","content":"What about the auth bug?","ts":"t1"}\n'
                '{"role":"assistant","content":"The token expires after 1 hour.","ts":"t2"}\n'
            )
        (efforts_dir / f"{effort_id}.jsonl").write_text(content)

        manifest = {"efforts": [{
            "id": effort_id,
            "status": "concluded",
            "summary": f"Fixed {effort_id}."
        }]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

    def test_expand_concluded_effort(self, session_dir):
        self._setup_concluded_effort(session_dir)
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
        self._setup_concluded_effort(session_dir)
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
        import yaml
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "efforts").mkdir(exist_ok=True)
        (session_dir / "efforts" / "old.jsonl").write_text('{"role":"user","content":"x","ts":"t"}\n')
        manifest = {"efforts": [{"id": "old", "status": "concluded", "summary": "Done."}]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

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
        import yaml
        session_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"efforts": [{"id": "old", "status": "concluded", "summary": "Done."}]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

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
        import yaml
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "efforts").mkdir(exist_ok=True)
        (session_dir / "efforts" / "old.jsonl").write_text(
            '{"role":"user","content":"x","ts":"t"}\n'
        )
        manifest = {"efforts": [{"id": "old", "status": "concluded", "summary": "Done."}]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

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
