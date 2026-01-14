"""Tests for context building with artifacts.

Tests Story 7: Building context that includes resolved artifacts.
"""

import pytest
from oi.models import Artifact, ConversationState


class TestContextIncludesArtifacts:
    """Story 7: Test that context includes resolved artifacts."""

    def test_context_includes_resolved_artifact(self):
        """Test that resolved artifacts are included in context.

        After an artifact is extracted, subsequent messages should have
        access to it in the context.
        """
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

        # TODO: Implement build_context() function
        # context = build_context(state, recent_messages=[])

        # Context should include the resolved artifact
        # assert "authentication" in context.lower() or "auth" in context.lower()
        # assert "token" in context.lower()

        pytest.skip("Context building implementation needed")

    def test_context_includes_multiple_artifacts(self):
        """Test context with multiple resolved artifacts."""
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

        # TODO: Implement build_context() function
        # context = build_context(state, recent_messages=[])

        # Should include both artifacts
        # assert "auth" in context.lower()
        # assert "database" in context.lower() or "index" in context.lower()

        pytest.skip("Context building implementation needed")

    def test_context_includes_recent_messages(self):
        """Test that context includes recent conversation messages."""
        state = ConversationState(artifacts=[])

        recent_messages = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "It's sunny today."},
        ]

        # TODO: Implement build_context() function
        # context = build_context(state, recent_messages=recent_messages)

        # Should include recent messages
        # assert "weather" in context.lower()
        # assert "sunny" in context.lower()

        pytest.skip("Context building implementation needed")

    def test_open_efforts_in_context(self):
        """Test that open efforts are included in context."""
        state = ConversationState(artifacts=[
            Artifact(
                id="art1",
                artifact_type="effort",
                summary="Finding best gaming mouse",
                status="open",
                tags=["gaming", "hardware"]
            )
        ])

        # TODO: Implement build_context() function
        # context = build_context(state, recent_messages=[])

        # Open efforts should be in context
        # assert "gaming mouse" in context.lower()

        pytest.skip("Context building implementation needed")


class TestAIReferencesArtifacts:
    """Story 7: Test that AI can reference earlier artifacts."""

    def test_ai_knows_about_resolved_artifact(self):
        """Test that AI response shows knowledge of resolved artifact.

        Acceptance criteria from Story 7:
        - The AI responds with knowledge of the earlier resolution
        """
        state = ConversationState(artifacts=[
            Artifact(
                id="art1",
                artifact_type="effort",
                summary="Debug auth bug",
                status="resolved",
                resolution="Token expired, refresh fixed it",
                tags=["auth"]
            )
        ])

        # TODO: This requires full integration with LLM
        # When user asks "What did we fix earlier?",
        # AI should mention the auth bug and token expiration

        pytest.skip("Integration test - needs full LLM context flow")

    def test_reference_multiple_artifacts(self):
        """Test AI can reference multiple previous artifacts.

        Story 7 example: After resolving auth bug and db bug,
        asking "which was easier to fix?" gets a relevant answer.
        """
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
                summary="Fix database timeout",
                status="resolved",
                resolution="Increased connection pool size",
                tags=["database"]
            )
        ])

        # TODO: Integration test
        # User asks: "Which was easier to fix?"
        # AI should compare both resolutions

        pytest.skip("Integration test - needs full LLM context flow")

    def test_no_reexplanation_needed(self):
        """Test that user doesn't need to re-explain earlier context.

        Story 7 acceptance criteria:
        - I do not need to re-explain the earlier topic
        """
        state = ConversationState(artifacts=[
            Artifact(
                id="art1",
                artifact_type="effort",
                summary="Setup CI/CD pipeline",
                status="resolved",
                resolution="Using GitHub Actions with Docker",
                tags=["devops", "ci"]
            )
        ])

        # TODO: Integration test
        # User asks: "How do I trigger it manually?"
        # AI should know "it" refers to the CI/CD pipeline
        # User should NOT need to say "How do I trigger the GitHub Actions pipeline?"

        pytest.skip("Integration test - needs full LLM context flow")


class TestContextLimits:
    """Test context size limits and prioritization."""

    def test_recent_messages_limit(self):
        """Test that only recent messages are included (not entire history)."""
        # Story 7 implies artifacts compress history, so we don't need
        # to send all raw messages - just recent ones + artifacts

        recent_messages = [{"role": "user", "content": f"Message {i}"} for i in range(100)]

        # TODO: Implement build_context() with limits
        # context = build_context(state=ConversationState(), recent_messages=recent_messages)

        # Should not include all 100 messages
        # assert "Message 1" not in context  # Too old
        # assert "Message 99" in context  # Recent

        pytest.skip("Context building with limits needed")

    def test_prioritize_relevant_artifacts(self):
        """Test that relevant artifacts are prioritized over irrelevant ones."""
        # If there are many artifacts, context should prioritize relevant ones

        state = ConversationState(artifacts=[
            Artifact(id="art1", artifact_type="effort", summary="Auth bug",
                     status="resolved", resolution="Fixed", tags=["auth"]),
            Artifact(id="art2", artifact_type="effort", summary="Database issue",
                     status="resolved", resolution="Fixed", tags=["database"]),
            Artifact(id="art3", artifact_type="effort", summary="UI bug",
                     status="resolved", resolution="Fixed", tags=["ui"]),
            # ... many more ...
        ])

        # TODO: If user is asking about database, database artifact should be included
        # even if there are many artifacts

        pytest.skip("Context prioritization implementation needed")

    def test_all_open_efforts_included(self):
        """Test that ALL open efforts are included, even if many artifacts exist.

        Open efforts are current work and should always be in context.
        """
        state = ConversationState(artifacts=[
            Artifact(id="open1", artifact_type="effort", summary="Current task 1",
                     status="open", tags=[]),
            Artifact(id="open2", artifact_type="effort", summary="Current task 2",
                     status="open", tags=[]),
            # Many resolved artifacts
            *[Artifact(id=f"resolved{i}", artifact_type="effort", summary=f"Old task {i}",
                      status="resolved", resolution="Done", tags=[])
              for i in range(50)]
        ])

        # TODO: Implement build_context()
        # context = build_context(state, recent_messages=[])

        # Both open efforts should be in context
        # assert "Current task 1" in context
        # assert "Current task 2" in context

        pytest.skip("Context building with open efforts needed")


class TestContextFormat:
    """Test the format of context sent to LLM."""

    def test_context_structure(self):
        """Test that context has a clear structure.

        Context should distinguish between:
        - Open efforts (current work)
        - Resolved artifacts (past work)
        - Recent messages (immediate context)
        """
        state = ConversationState(artifacts=[
            Artifact(id="open1", artifact_type="effort", summary="Current work",
                     status="open", tags=[]),
            Artifact(id="resolved1", artifact_type="effort", summary="Past work",
                     status="resolved", resolution="Done", tags=[]),
        ])

        recent_messages = [
            {"role": "user", "content": "Recent question"}
        ]

        # TODO: Implement build_context()
        # context = build_context(state, recent_messages)

        # Context should have clear sections
        # assert "Open efforts:" in context or "Current work:" in context
        # assert "Resolved:" in context or "Past:" in context
        # assert "Recent:" in context

        pytest.skip("Context formatting implementation needed")

    def test_artifact_format_in_context(self):
        """Test how artifacts are formatted in context.

        Should match the notification format from Story 3:
        [effort:resolved] Debug auth bug
          => Token was expired, refresh fixed it
        """
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

        # TODO: Implement build_context()
        # context = build_context(state, recent_messages=[])

        # Should include summary and resolution
        # assert "Debug auth bug" in context
        # assert "Token was expired" in context
        # assert "refresh fixed it" in context

        pytest.skip("Context formatting implementation needed")


class TestSessionVsCrossSessions:
    """Test context in same session vs across sessions (Story 7 vs Story 9)."""

    def test_same_session_context(self):
        """Story 7: Test context in same session.

        After an artifact is extracted in the same session,
        I can reference it immediately.
        """
        # This is Story 7 - artifacts available in same session
        pytest.skip("Same-session context - covered by other tests")

    def test_cross_session_context(self):
        """Story 9: Test context after restart.

        After exiting and running `oi` again, previous artifacts
        should still be available.
        """
        # This is Story 9 - persistence across restarts
        # Context building should load from saved state

        # TODO: Test that artifacts loaded from disk are included in context
        pytest.skip("Cross-session persistence - Story 9 scope")


class TestContextWithNoArtifacts:
    """Test context when no artifacts exist yet."""

    def test_context_with_empty_state(self):
        """Test context for first-time user (Story 10)."""
        state = ConversationState(artifacts=[])
        recent_messages = [
            {"role": "user", "content": "Hello, this is my first message"}
        ]

        # TODO: Implement build_context()
        # context = build_context(state, recent_messages)

        # Should work fine with no artifacts
        # assert context is not None
        # Should still include the recent message
        # assert "first message" in context.lower()

        pytest.skip("Context building implementation needed")

    def test_context_with_only_recent_messages(self):
        """Test context when only recent messages exist (no artifacts yet)."""
        state = ConversationState(artifacts=[])
        recent_messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
        ]

        # TODO: Implement build_context()
        # context = build_context(state, recent_messages)

        # Should include recent messages
        # assert "Question 1" in context or "Question 2" in context

        pytest.skip("Context building implementation needed")
