"""Tests for context building with artifacts.

Tests Story 7: Building context that includes resolved artifacts.

These tests define interfaces that DON'T EXIST YET.
They should FAIL until implementation is complete.
"""

import pytest
from oi.models import Artifact, ConversationState


class TestContextIncludesArtifacts:
    """Story 7: Test that context includes resolved artifacts."""

    def test_context_includes_resolved_artifact(self):
        """Test that resolved artifacts are included in context."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[
            Artifact(
                id="art1",
                artifact_type="effort",
                summary="Debug authentication bug",
                status="resolved",
                resolution="Token was expired, refresh fixed it",
                tags=["auth", "debug"]
            )
        ])

        context = build_context(state, recent_messages=[])

        # Context should include the resolved artifact
        assert "authentication" in context.lower() or "auth" in context.lower()
        assert "token" in context.lower()

    def test_context_includes_multiple_artifacts(self):
        """Test context with multiple resolved artifacts."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[
            Artifact(
                id="art1",
                artifact_type="effort",
                summary="Debug auth bug",
                status="resolved",
                resolution="Token expired, refresh fixed it",
                tags=["auth"]
            ),
            Artifact(
                id="art2",
                artifact_type="effort",
                summary="Optimize database queries",
                status="resolved",
                resolution="Added index on user_id column",
                tags=["database"]
            )
        ])

        context = build_context(state, recent_messages=[])

        # Should include both artifacts
        assert "auth" in context.lower()
        assert "database" in context.lower() or "index" in context.lower()

    def test_context_includes_recent_messages(self):
        """Test that context includes recent conversation messages."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[])

        recent_messages = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "It's sunny today."},
        ]

        context = build_context(state, recent_messages=recent_messages)

        # Should include recent messages
        assert "weather" in context.lower()
        assert "sunny" in context.lower()

    def test_open_efforts_in_context(self):
        """Test that open efforts are included in context."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[
            Artifact(
                id="art1",
                artifact_type="effort",
                summary="Finding best gaming mouse",
                status="open",
                tags=["gaming", "hardware"]
            )
        ])

        context = build_context(state, recent_messages=[])

        # Open efforts should be in context
        assert "gaming mouse" in context.lower()


class TestContextLimits:
    """Test context size limits and prioritization."""

    def test_recent_messages_limit(self):
        """Test that only recent messages are included (not entire history)."""
        from oi.context import build_context  # Does not exist yet

        recent_messages = [{"role": "user", "content": f"Message {i}"} for i in range(100)]

        context = build_context(state=ConversationState(), recent_messages=recent_messages)

        # Should not include all 100 messages - only recent ones
        assert "Message 99" in context  # Most recent should be included
        # Older messages may be truncated

    def test_all_open_efforts_included(self):
        """Test that ALL open efforts are included, even if many artifacts exist."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[
            Artifact(id="open1", artifact_type="effort", summary="Current task 1",
                     status="open", tags=[]),
            Artifact(id="open2", artifact_type="effort", summary="Current task 2",
                     status="open", tags=[]),
            # Many resolved artifacts
            *[Artifact(id=f"resolved{i}", artifact_type="effort", summary=f"Old task {i}",
                      status="resolved", resolution="Done", tags=[])
              for i in range(10)]
        ])

        context = build_context(state, recent_messages=[])

        # Both open efforts should be in context
        assert "Current task 1" in context
        assert "Current task 2" in context


class TestContextFormat:
    """Test the format of context sent to LLM."""

    def test_context_structure(self):
        """Test that context has a clear structure."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[
            Artifact(id="open1", artifact_type="effort", summary="Current work",
                     status="open", tags=[]),
            Artifact(id="resolved1", artifact_type="effort", summary="Past work",
                     status="resolved", resolution="Done", tags=[]),
        ])

        recent_messages = [
            {"role": "user", "content": "Recent question"}
        ]

        context = build_context(state, recent_messages)

        # Context should be a non-empty string
        assert isinstance(context, str)
        assert len(context) > 0

    def test_artifact_format_in_context(self):
        """Test how artifacts are formatted in context."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[
            Artifact(
                id="art1",
                artifact_type="effort",
                summary="Debug auth bug",
                status="resolved",
                resolution="Token was expired, refresh fixed it",
                tags=["auth"]
            )
        ])

        context = build_context(state, recent_messages=[])

        # Should include summary and resolution
        assert "Debug auth bug" in context or "auth bug" in context.lower()
        assert "token" in context.lower()


class TestContextWithNoArtifacts:
    """Test context when no artifacts exist yet."""

    def test_context_with_empty_state(self):
        """Test context for first-time user (Story 10)."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[])
        recent_messages = [
            {"role": "user", "content": "Hello, this is my first message"}
        ]

        context = build_context(state, recent_messages)

        # Should work fine with no artifacts
        assert context is not None
        # Should still include the recent message
        assert "first message" in context.lower()

    def test_context_with_only_recent_messages(self):
        """Test context when only recent messages exist (no artifacts yet)."""
        from oi.context import build_context  # Does not exist yet

        state = ConversationState(artifacts=[])
        recent_messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
        ]

        context = build_context(state, recent_messages)

        # Should include recent messages
        assert "Question 1" in context or "Question 2" in context
