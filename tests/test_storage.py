"""Tests for simple JSON persistence layer."""

import pytest
from pathlib import Path
import tempfile
import shutil
import json

from oi.models import ConversationState, Artifact
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
        assert state.artifacts == []

    def test_save_and_load_roundtrip(self, temp_state_dir):
        original_state = ConversationState(artifacts=[
            Artifact(
                id="effort1",
                artifact_type="effort",
                summary="Finding best gaming mouse",
                status="resolved",
                resolution="Chose Logitech G Pro X Superlight",
                tags=["gaming", "hardware"]
            ),
            Artifact(
                id="fact1",
                artifact_type="fact",
                summary="The capital of France is Paris",
                expires=True
            ),
        ])

        save_state(original_state, temp_state_dir)

        # Verify file exists
        state_path = get_state_path(temp_state_dir)
        assert state_path.exists()

        loaded_state = load_state(temp_state_dir)

        assert len(loaded_state.artifacts) == 2
        assert loaded_state.artifacts[0].id == "effort1"
        assert loaded_state.artifacts[0].resolution == "Chose Logitech G Pro X Superlight"
        assert loaded_state.artifacts[1].artifact_type == "fact"

    def test_save_overwrites_existing(self, temp_state_dir):
        state1 = ConversationState(artifacts=[
            Artifact(id="1", artifact_type="fact", summary="First")
        ])
        save_state(state1, temp_state_dir)

        state2 = ConversationState(artifacts=[
            Artifact(id="2", artifact_type="fact", summary="Second")
        ])
        save_state(state2, temp_state_dir)

        loaded = load_state(temp_state_dir)
        assert len(loaded.artifacts) == 1
        assert loaded.artifacts[0].id == "2"
        assert loaded.artifacts[0].summary == "Second"

    def test_migration_from_legacy_format(self, temp_state_dir):
        """Test that legacy state with threads/conclusions is migrated."""
        # Write legacy format directly
        legacy_state = {
            "threads": [{"id": "t001", "messages": [], "status": "open"}],
            "conclusions": [{"id": "c001", "content": "Old conclusion", "source_thread_id": "t001"}],
            "artifacts": [
                {"id": "a001", "artifact_type": "effort", "summary": "New artifact", "status": "open"}
            ],
            "active_thread_id": "t001",
            "token_stats": {"total_raw": 100, "total_compacted": 10}
        }
        state_path = get_state_path(temp_state_dir)
        ensure_state_dir(temp_state_dir)
        state_path.write_text(json.dumps(legacy_state))

        # Load should migrate - keep artifacts, drop threads/conclusions
        loaded = load_state(temp_state_dir)
        assert len(loaded.artifacts) == 1
        assert loaded.artifacts[0].id == "a001"
