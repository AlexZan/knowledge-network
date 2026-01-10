"""Tests for data models."""

import pytest
from oi.models import (
    Message,
    Thread,
    Conclusion,
    TokenStats,
    ConversationState,
)


class TestMessage:
    def test_create_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_message_roles(self):
        user_msg = Message(role="user", content="Hi")
        assistant_msg = Message(role="assistant", content="Hello!")
        assert user_msg.role == "user"
        assert assistant_msg.role == "assistant"


class TestThread:
    def test_create_thread(self):
        thread = Thread(id="t001")
        assert thread.id == "t001"
        assert thread.messages == []
        assert thread.status == "open"
        assert thread.conclusion_id is None

    def test_thread_with_messages(self):
        thread = Thread(
            id="t001",
            messages=[
                Message(role="user", content="Hi"),
                Message(role="assistant", content="Hello!"),
            ]
        )
        assert len(thread.messages) == 2

    def test_concluded_thread(self):
        thread = Thread(id="t001", status="concluded", conclusion_id="c001")
        assert thread.status == "concluded"
        assert thread.conclusion_id == "c001"


class TestConclusion:
    def test_create_conclusion(self):
        conclusion = Conclusion(
            id="c001",
            content="The bug was caused by expired tokens",
            source_thread_id="t001"
        )
        assert conclusion.id == "c001"
        assert conclusion.content == "The bug was caused by expired tokens"
        assert conclusion.source_thread_id == "t001"
        assert conclusion.created is not None


class TestTokenStats:
    def test_empty_stats(self):
        stats = TokenStats()
        assert stats.total_raw == 0
        assert stats.total_compacted == 0
        assert stats.savings_percent == 0.0

    def test_savings_calculation(self):
        stats = TokenStats(total_raw=1000, total_compacted=100)
        assert stats.savings_percent == 90.0

    def test_savings_no_division_by_zero(self):
        stats = TokenStats(total_raw=0, total_compacted=0)
        assert stats.savings_percent == 0.0


class TestConversationState:
    def test_empty_state(self):
        state = ConversationState()
        assert state.threads == []
        assert state.conclusions == []
        assert state.active_thread_id is None

    def test_get_active_thread(self):
        thread = Thread(id="t001")
        state = ConversationState(
            threads=[thread],
            active_thread_id="t001"
        )
        assert state.get_active_thread() == thread

    def test_get_active_thread_none(self):
        state = ConversationState()
        assert state.get_active_thread() is None

    def test_get_active_conclusions(self):
        conclusions = [
            Conclusion(id="c001", content="First", source_thread_id="t001"),
            Conclusion(id="c002", content="Second", source_thread_id="t002"),
        ]
        state = ConversationState(conclusions=conclusions)
        assert state.get_active_conclusions() == conclusions

    def test_serialization_roundtrip(self):
        state = ConversationState(
            threads=[Thread(id="t001")],
            conclusions=[Conclusion(id="c001", content="Test", source_thread_id="t001")],
            active_thread_id="t001",
            token_stats=TokenStats(total_raw=100, total_compacted=10)
        )
        json_str = state.model_dump_json()
        loaded = ConversationState.model_validate_json(json_str)

        assert loaded.threads[0].id == "t001"
        assert loaded.conclusions[0].content == "Test"
        assert loaded.active_thread_id == "t001"
        assert loaded.token_stats.total_raw == 100
