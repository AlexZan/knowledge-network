"""Tests for SQLite persistence layer."""

import pytest
from pathlib import Path
import tempfile
import shutil

from oi.models import ConversationState, Thread, Message, Conclusion, TokenStats
from oi.storage import (
    save_state, load_state, ensure_state_dir, init_db,
    get_db_path, save_thread, load_thread,
    save_conclusion, load_conclusion, load_all_conclusions,
    add_history_entry, load_recent_history,
    get_token_stats, update_token_stats,
    get_active_thread_id, set_active_thread_id
)


@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for state storage."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestDatabaseSetup:
    def test_ensure_state_dir_creates_directory(self, temp_state_dir):
        new_dir = temp_state_dir / "subdir"
        assert not new_dir.exists()
        ensure_state_dir(new_dir)
        assert new_dir.exists()

    def test_get_db_path(self, temp_state_dir):
        path = get_db_path(temp_state_dir)
        assert path == temp_state_dir / "oi.db"

    def test_init_db_creates_tables(self, temp_state_dir):
        init_db(temp_state_dir)
        db_path = get_db_path(temp_state_dir)
        assert db_path.exists()


class TestConclusionOperations:
    def test_save_and_load_conclusion(self, temp_state_dir):
        init_db(temp_state_dir)
        conclusion = Conclusion(
            id="c001",
            content="Test conclusion",
            source_thread_id="t001"
        )

        save_conclusion(conclusion, temp_state_dir)
        loaded = load_conclusion("c001", temp_state_dir)

        assert loaded is not None
        assert loaded.id == "c001"
        assert loaded.content == "Test conclusion"
        assert loaded.source_thread_id == "t001"

    def test_load_nonexistent_conclusion(self, temp_state_dir):
        init_db(temp_state_dir)
        loaded = load_conclusion("nonexistent", temp_state_dir)
        assert loaded is None

    def test_load_all_conclusions(self, temp_state_dir):
        init_db(temp_state_dir)
        c1 = Conclusion(id="c001", content="First", source_thread_id="t001")
        c2 = Conclusion(id="c002", content="Second", source_thread_id="t002")

        save_conclusion(c1, temp_state_dir)
        save_conclusion(c2, temp_state_dir)

        all_conclusions = load_all_conclusions(temp_state_dir)
        assert len(all_conclusions) == 2


class TestThreadOperations:
    def test_save_and_load_thread(self, temp_state_dir):
        init_db(temp_state_dir)
        thread = Thread(
            id="t001",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!")
            ],
            context_conclusion_ids=["c001", "c002"],
            status="open"
        )

        save_thread(thread, temp_state_dir)
        loaded = load_thread("t001", temp_state_dir)

        assert loaded is not None
        assert loaded.id == "t001"
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"
        assert loaded.messages[1].content == "Hi there!"
        assert loaded.context_conclusion_ids == ["c001", "c002"]
        assert loaded.status == "open"

    def test_load_nonexistent_thread(self, temp_state_dir):
        init_db(temp_state_dir)
        loaded = load_thread("nonexistent", temp_state_dir)
        assert loaded is None


class TestHistoryOperations:
    def test_add_and_load_history(self, temp_state_dir):
        init_db(temp_state_dir)

        add_history_entry("event", label="greeting", thread_id="t001", state_dir=temp_state_dir)
        add_history_entry("knowledge", thread_id="t002", conclusion_id="c001", state_dir=temp_state_dir)

        history = load_recent_history(limit=10, state_dir=temp_state_dir)
        assert len(history) == 2
        # Most recent first
        assert history[0]["type"] == "knowledge"
        assert history[1]["type"] == "event"


class TestTokenStats:
    def test_initial_token_stats(self, temp_state_dir):
        init_db(temp_state_dir)
        stats = get_token_stats(temp_state_dir)
        assert stats.total_raw == 0
        assert stats.total_compacted == 0

    def test_update_token_stats(self, temp_state_dir):
        init_db(temp_state_dir)
        update_token_stats(100, 50, temp_state_dir)
        update_token_stats(200, 75, temp_state_dir)

        stats = get_token_stats(temp_state_dir)
        assert stats.total_raw == 300
        assert stats.total_compacted == 125


class TestActiveThreadState:
    def test_initial_active_thread_is_none(self, temp_state_dir):
        init_db(temp_state_dir)
        active_id = get_active_thread_id(temp_state_dir)
        assert active_id is None

    def test_set_and_get_active_thread(self, temp_state_dir):
        init_db(temp_state_dir)
        set_active_thread_id("t001", temp_state_dir)

        active_id = get_active_thread_id(temp_state_dir)
        assert active_id == "t001"

    def test_clear_active_thread(self, temp_state_dir):
        init_db(temp_state_dir)
        set_active_thread_id("t001", temp_state_dir)
        set_active_thread_id(None, temp_state_dir)

        active_id = get_active_thread_id(temp_state_dir)
        assert active_id is None


class TestHighLevelStateOperations:
    def test_load_empty_state(self, temp_state_dir):
        state = load_state(temp_state_dir)
        assert isinstance(state, ConversationState)
        assert state.threads == []
        assert state.conclusions == []

    def test_save_and_load_state_with_active_thread(self, temp_state_dir):
        original_state = ConversationState(
            threads=[
                Thread(id="t001", status="concluded", conclusion_id="c001",
                       messages=[Message(role="user", content="Q"), Message(role="assistant", content="A")]),
                Thread(id="t002", status="open",
                       messages=[Message(role="user", content="Hello")]),
            ],
            conclusions=[
                Conclusion(id="c001", content="Test conclusion", source_thread_id="t001")
            ],
            active_thread_id="t002",
            token_stats=TokenStats(total_raw=500, total_compacted=50)
        )

        save_state(original_state, temp_state_dir)
        loaded_state = load_state(temp_state_dir)

        # Only active thread is loaded
        assert len(loaded_state.threads) == 1
        assert loaded_state.threads[0].id == "t002"
        assert loaded_state.threads[0].status == "open"

        # Conclusions are loaded
        assert len(loaded_state.conclusions) == 1
        assert loaded_state.conclusions[0].content == "Test conclusion"

        # Metadata
        assert loaded_state.active_thread_id == "t002"
        assert loaded_state.token_stats.total_raw == 500
        assert loaded_state.token_stats.savings_percent == 90.0

    def test_save_state_no_active_thread(self, temp_state_dir):
        state = ConversationState(
            threads=[
                Thread(id="t001", status="concluded", conclusion_id="c001",
                       messages=[Message(role="user", content="Q")]),
            ],
            conclusions=[
                Conclusion(id="c001", content="Done", source_thread_id="t001")
            ],
            active_thread_id=None
        )

        save_state(state, temp_state_dir)
        loaded = load_state(temp_state_dir)

        assert len(loaded.threads) == 0
        assert len(loaded.conclusions) == 1
        assert loaded.active_thread_id is None
