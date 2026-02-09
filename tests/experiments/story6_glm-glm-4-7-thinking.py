"""Tests for Story 6: Remove Concluded Effort from Active Context"""

import pytest
import json
from pathlib import Path

from oi.models import ConversationState, Artifact
from oi.chatlog import append_exchange


class TestStory6RemoveConcludedEffortFromActiveContext:
    """Story 6: Remove Concluded Effort from Active Context"""

    def test_concluded_effort_raw_log_excluded_from_context(self, tmp_path):
        """After an effort is concluded, its raw log is no longer included in the context for subsequent turns."""
        # Arrange
        from oi.conversation import conclude_effort, build_context

        state = ConversationState()
        effort_id = "auth-bug"
        state.artifacts.append(
            Artifact(
                id=effort_id,
                artifact_type="effort",
                summary="Debugging 401 errors",
                status="open"
            )
        )

        # Add raw messages to the chat log
        append_exchange("Users getting 401s", "Check token TTL", state_dir=tmp_path)
        append_exchange("TTL is 1 hour", "Need refresh logic", state_dir=tmp_path)

        # Act
        conclude_effort(
            effort_id=effort_id,
            state=state,
            state_dir=tmp_path,
            resolution="Fixed by adding axios interceptor"
        )

        # Build context for subsequent turn
        context_messages = build_context(state, state_dir=tmp_path)
        context_str = json.dumps([m["content"] for m in context_messages])

        # Assert
        # The raw messages "Users getting 401s" and "TTL is 1 hour" should NOT be in context
        assert "Users getting 401s" not in context_str
        assert "TTL is 1 hour" not in context_str

    def test_concluded_effort_summary_included_in_context(self, tmp_path):
        """Only the summary of the concluded effort (from the manifest) is included in the context."""
        # Arrange
        from oi.conversation import conclude_effort, build_context

        state = ConversationState()
        effort_id = "auth-bug"
        state.artifacts.append(
            Artifact(
                id=effort_id,
                artifact_type="effort",
                summary="Debugging 401 errors",
                status="open"
            )
        )

        append_exchange("Users getting 401s", "Check token TTL", state_dir=tmp_path)

        resolution_text = "Fixed by adding axios interceptor for proactive refresh"

        # Act
        conclude_effort(
            effort_id=effort_id,
            state=state,
            state_dir=tmp_path,
            resolution=resolution_text
        )

        # Build context
        context_messages = build_context(state, state_dir=tmp_path)
        context_str = json.dumps([m["content"] for m in context_messages])

        # Assert
        # The summary/resolution SHOULD be in context
        assert resolution_text in context_str
        assert "Debugging 401 errors" in context_str

    def test_concluded_effort_raw_log_preserved_on_disk(self, tmp_path):
        """The raw log file for the concluded effort is preserved on disk for potential future reference."""
        # Arrange
        from oi.conversation import conclude_effort

        state = ConversationState()
        effort_id = "auth-bug"
        state.artifacts.append(
            Artifact(
                id=effort_id,
                artifact_type="effort",
                summary="Debugging 401 errors",
                status="open"
            )
        )

        # Add messages
        append_exchange("Users getting 401s", "Check token TTL", state_dir=tmp_path)
        append_exchange("TTL is 1 hour", "Need refresh logic", state_dir=tmp_path)

        # Act
        conclude_effort(
            effort_id=effort_id,
            state=state,
            state_dir=tmp_path,
            resolution="Fixed by adding axios interceptor"
        )

        # Assert
        # Check that the specific effort file exists in the efforts/ directory
        effort_file = tmp_path / "efforts" / f"{effort_id}.jsonl"
        assert effort_file.exists()

        # Verify it contains the raw messages
        content = effort_file.read_text()
        assert "Users getting 401s" in content
        assert "TTL is 1 hour" in content