"""Tests for token statistics calculation.

Tests Story 4: Calculate and display token savings.

These tests define interfaces that DON'T EXIST YET.
They should FAIL until implementation is complete.
"""

import pytest


class TestTokenCounting:
    """Test raw token counting for messages."""

    def test_count_raw_tokens_from_messages(self):
        """Test counting tokens in raw message thread."""
        from oi.tokens import count_tokens_in_messages  # Does not exist yet

        messages = [
            {"role": "user", "content": "My authentication is failing"},
            {"role": "assistant", "content": "Let me help you debug that..."},
            {"role": "user", "content": "I get error 401"},
            {"role": "assistant", "content": "That's an unauthorized error..."},
            {"role": "user", "content": "Thanks!"},
        ]

        raw_count = count_tokens_in_messages(messages)
        assert raw_count > 0

    def test_count_compacted_tokens_from_artifact(self):
        """Test counting tokens in compacted artifact."""
        from oi.tokens import count_tokens  # Does not exist yet

        artifact_text = "Auth bug => Token was expired, refresh fixed it"

        compacted_count = count_tokens(artifact_text)
        assert compacted_count > 0
        assert compacted_count < 100  # Should be compact


class TestTokenStatsFormatting:
    """Story 4: Test the display format of token stats."""

    def test_format_token_stats_display(self):
        """Test that stats format matches story spec.

        Expected format: [Tokens: 1,247 raw → 68 compacted | Savings: 95%]
        """
        from oi.tokens import format_token_stats  # Does not exist yet
        from oi.models import TokenStats

        stats = TokenStats(total_raw=1247, total_compacted=68)

        formatted = format_token_stats(stats)
        assert "1,247 raw" in formatted
        assert "68 compacted" in formatted
        assert "95%" in formatted
        assert formatted.startswith("[Tokens:")
        assert formatted.endswith("]")

    def test_format_with_comma_separators(self):
        """Test that large numbers use comma separators."""
        from oi.tokens import format_token_stats  # Does not exist yet
        from oi.models import TokenStats

        stats = TokenStats(total_raw=12470, total_compacted=680)

        formatted = format_token_stats(stats)
        assert "12,470" in formatted  # Should have comma

    def test_format_rounds_percentage(self):
        """Test that percentage is rounded appropriately."""
        from oi.tokens import format_token_stats  # Does not exist yet
        from oi.models import TokenStats

        stats = TokenStats(total_raw=1000, total_compacted=333)
        # Actual savings: 66.7%

        formatted = format_token_stats(stats)
        # Should round to nearest integer
        assert "67%" in formatted


class TestStatsForSpecificEffort:
    """Story 4: Stats should reflect only the effort just resolved."""

    def test_stats_for_single_effort_only(self):
        """Test that stats show only current effort, not cumulative."""
        from oi.tokens import calculate_effort_stats  # Does not exist yet

        # Effort 1: Auth bug
        effort1_messages = [
            {"role": "user", "content": "Login failing"},
            {"role": "assistant", "content": "Let's debug..."},
            {"role": "user", "content": "Thanks!"},
        ]
        effort1_artifact = "Auth bug => Token expired"

        stats1 = calculate_effort_stats(effort1_messages, effort1_artifact)

        # Effort 2: Database bug (longer conversation)
        effort2_messages = [
            {"role": "user", "content": "Database slow"},
            {"role": "assistant", "content": "Check indexes..."},
            {"role": "user", "content": "Still slow"},
            {"role": "assistant", "content": "Try connection pooling..."},
            {"role": "user", "content": "Fixed it!"},
        ]
        effort2_artifact = "DB slow => Added index"

        stats2 = calculate_effort_stats(effort2_messages, effort2_artifact)

        # Each should be independent
        assert stats1.total_raw != stats2.total_raw
        assert stats2.total_raw > stats1.total_raw  # Longer conversation
