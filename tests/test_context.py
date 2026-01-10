"""Tests for context building."""

import pytest
from oi.models import ConversationState, Thread, Message, Conclusion
from oi.context import (
    build_conclusions_context,
    build_thread_messages,
    build_context,
    count_tokens,
    count_messages_tokens,
)


class TestBuildConclusionsContext:
    def test_empty_conclusions(self):
        result = build_conclusions_context([])
        assert result == ""

    def test_single_conclusion(self):
        conclusions = [
            Conclusion(id="c001", content="Bug was caused by X", source_thread_id="t001")
        ]
        result = build_conclusions_context(conclusions)
        assert "Previous conclusions" in result
        assert "Bug was caused by X" in result

    def test_multiple_conclusions(self):
        conclusions = [
            Conclusion(id="c001", content="First issue", source_thread_id="t001"),
            Conclusion(id="c002", content="Second issue", source_thread_id="t002"),
        ]
        result = build_conclusions_context(conclusions)
        assert "First issue" in result
        assert "Second issue" in result


class TestBuildThreadMessages:
    def test_empty_thread(self):
        thread = Thread(id="t001")
        result = build_thread_messages(thread)
        assert result == []

    def test_thread_with_messages(self):
        thread = Thread(
            id="t001",
            messages=[
                Message(role="user", content="Hello"),
                Message(role="assistant", content="Hi there!"),
            ]
        )
        result = build_thread_messages(thread)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there!"}


class TestBuildContext:
    def test_empty_state(self):
        state = ConversationState()
        result = build_context(state)
        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_with_conclusions(self):
        state = ConversationState(
            conclusions=[
                Conclusion(id="c001", content="Resolved issue X", source_thread_id="t001")
            ]
        )
        result = build_context(state)
        system_msg = result[0]["content"]
        assert "Previous conclusions" in system_msg
        assert "Resolved issue X" in system_msg

    def test_with_active_thread(self):
        thread = Thread(
            id="t001",
            messages=[
                Message(role="user", content="Question?"),
                Message(role="assistant", content="Answer!"),
            ]
        )
        state = ConversationState(
            threads=[thread],
            active_thread_id="t001"
        )
        result = build_context(state)
        assert len(result) == 3  # system + 2 messages
        assert result[1]["content"] == "Question?"
        assert result[2]["content"] == "Answer!"

    def test_full_context(self):
        thread = Thread(
            id="t002",
            messages=[Message(role="user", content="New question")]
        )
        state = ConversationState(
            threads=[thread],
            conclusions=[
                Conclusion(id="c001", content="Old resolved issue", source_thread_id="t001")
            ],
            active_thread_id="t002"
        )
        result = build_context(state)

        # System prompt with conclusions
        assert "Old resolved issue" in result[0]["content"]
        # Active thread message
        assert result[1]["content"] == "New question"


class TestTokenCounting:
    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_approximation(self):
        # ~4 chars per token
        text = "This is a test message"  # 22 chars
        tokens = count_tokens(text)
        assert tokens == 5  # 22 // 4 = 5

    def test_count_messages_tokens(self):
        messages = [
            {"role": "user", "content": "Hello world"},  # 11 chars = 2 tokens
            {"role": "assistant", "content": "Hi there"},  # 8 chars = 2 tokens
        ]
        total = count_messages_tokens(messages)
        assert total == 4
