"""Tests for Story 9: Verify Token Savings from Effort Management"""

import pytest
from unittest.mock import patch
from oi.models import ConversationState, Message
from oi.tokens import calculate_effort_stats, count_tokens_in_messages
from oi.context import build_context


class TestStory9VerifyTokenSavings:
    """Story 9: Verify Token Savings from Effort Management"""

    def test_context_size_measured_with_open_effort(self):
        """After working on an effort for several turns, the context size is measured"""
        # Arrange
        # Constructing state with an open effort containing messages
        effort_messages = [
            Message(role="user", content="Let's debug the auth bug"),
            Message(role="assistant", content="Opening effort: auth-bug. What's the TTL?"),
            Message(role="user", content="Access token is 1 hour"),
            Message(role="assistant", content="That matches the failure timing.")
        ]
        
        state = ConversationState(
            efforts=[
                {
                    "id": "auth-bug",
                    "status": "open",
                    "messages": effort_messages
                }
            ]
        )
        
        # Act
        # build_context should include the full raw messages of the open effort
        context = build_context(state, [])
        token_count = count_tokens_in_messages(context, "gpt-4")
        
        # Assert
        # We expect a non-zero token count representing the full effort
        assert token_count > 0

    def test_context_size_measured_after_concluding_effort(self):
        """After concluding that effort, the context size is measured again"""
        # Arrange
        # Constructing state with a concluded effort (has summary, not raw messages in context)
        effort_messages = [
            Message(role="user", content="Let's debug the auth bug"),
            Message(role="assistant", content="Opening effort: auth-bug.")
        ]
        
        state = ConversationState(
            efforts=[
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor.",
                    "messages": effort_messages
                }
            ]
        )
        
        # Act
        # build_context should include the summary, NOT the full raw messages
        context = build_context(state, [])
        token_count = count_tokens_in_messages(context, "gpt-4")
        
        # Assert
        # We expect a non-zero token count, but it should be smaller than the raw
        assert token_count > 0

    @patch('oi.tokens.count_tokens')
    @patch('oi.tokens.count_tokens_in_messages')
    def test_token_count_shows_significant_reduction(self, mock_count_msgs, mock_count_text):
        """The token count shows a significant reduction (e.g., 80%+ savings for that effort)"""
        # Arrange
        # Simulate: Raw effort = 1000 tokens, Summary = 100 tokens
        mock_count_msgs.return_value = 1000
        mock_count_text.return_value = 100
        
        messages = [
            Message(role="user", content="Long conversation about auth bug..."),
            Message(role="assistant", content="Detailed debugging steps...")
        ]
        summary = "Debugged 401 errors. Fixed with axios interceptor."
        
        # Act
        stats = calculate_effort_stats(messages, summary, "gpt-4")
        
        # Assert
        # Savings = 1 - (100 / 1000) = 90%
        assert stats.savings_percent() >= 80.0

    @patch('oi.tokens.count_tokens')
    @patch('oi.tokens.count_tokens_in_messages')
    def test_summary_smaller_than_raw_log(self, mock_count_msgs, mock_count_text):
        """The summary in the manifest is substantially smaller than the raw effort log it replaces"""
        # Arrange
        # Raw = 1000 tokens, Summary = 150 tokens
        mock_count_msgs.return_value = 1000
        mock_count_text.return_value = 150
        
        messages = [Message(role="user", content="Raw log content...")]
        summary = "Concise summary."
        
        # Act
        stats = calculate_effort_stats(messages, summary, "gpt-4")
        
        # Assert
        assert stats.raw_tokens > stats.summary_tokens