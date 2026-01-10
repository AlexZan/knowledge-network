"""Tests for persistence layer."""

import pytest
from pathlib import Path
import tempfile
import shutil

from oi.models import ConversationState, Thread, Conclusion, TokenStats
from oi.storage import save_state, load_state, get_state_path, ensure_state_dir


@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for state storage."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestStorage:
    def test_ensure_state_dir_creates_directory(self, temp_state_dir):
        new_dir = temp_state_dir / "subdir"
        assert not new_dir.exists()
        ensure_state_dir(new_dir)
        assert new_dir.exists()

    def test_get_state_path(self, temp_state_dir):
        path = get_state_path(temp_state_dir)
        assert path == temp_state_dir / "state.json"

    def test_load_empty_state(self, temp_state_dir):
        state = load_state(temp_state_dir)
        assert isinstance(state, ConversationState)
        assert state.threads == []
        assert state.conclusions == []

    def test_save_and_load_roundtrip(self, temp_state_dir):
        # Create state with data
        original_state = ConversationState(
            threads=[
                Thread(id="t001", status="concluded", conclusion_id="c001"),
                Thread(id="t002", status="open"),
            ],
            conclusions=[
                Conclusion(id="c001", content="Test conclusion", source_thread_id="t001")
            ],
            active_thread_id="t002",
            token_stats=TokenStats(total_raw=500, total_compacted=50)
        )

        # Save
        save_state(original_state, temp_state_dir)

        # Verify file exists
        state_path = get_state_path(temp_state_dir)
        assert state_path.exists()

        # Load
        loaded_state = load_state(temp_state_dir)

        # Verify
        assert len(loaded_state.threads) == 2
        assert loaded_state.threads[0].id == "t001"
        assert loaded_state.threads[0].status == "concluded"
        assert loaded_state.threads[1].id == "t002"
        assert loaded_state.threads[1].status == "open"

        assert len(loaded_state.conclusions) == 1
        assert loaded_state.conclusions[0].content == "Test conclusion"

        assert loaded_state.active_thread_id == "t002"
        assert loaded_state.token_stats.total_raw == 500
        assert loaded_state.token_stats.savings_percent == 90.0

    def test_save_overwrites_existing(self, temp_state_dir):
        # Save first state
        state1 = ConversationState(
            conclusions=[Conclusion(id="c001", content="First", source_thread_id="t001")]
        )
        save_state(state1, temp_state_dir)

        # Save second state
        state2 = ConversationState(
            conclusions=[Conclusion(id="c002", content="Second", source_thread_id="t002")]
        )
        save_state(state2, temp_state_dir)

        # Load and verify it's the second state
        loaded = load_state(temp_state_dir)
        assert len(loaded.conclusions) == 1
        assert loaded.conclusions[0].id == "c002"
        assert loaded.conclusions[0].content == "Second"
