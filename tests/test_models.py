"""Tests for data models."""

import pytest
from oi.models import Artifact, ConversationState


class TestArtifact:
    def test_create_effort(self):
        artifact = Artifact(
            id="abc123",
            artifact_type="effort",
            summary="Finding best gaming mouse",
            status="open",
            tags=["gaming", "hardware"]
        )
        assert artifact.id == "abc123"
        assert artifact.artifact_type == "effort"
        assert artifact.status == "open"
        assert artifact.resolution is None
        assert artifact.expires is False

    def test_create_resolved_effort(self):
        artifact = Artifact(
            id="abc123",
            artifact_type="effort",
            summary="Finding best gaming mouse",
            status="resolved",
            resolution="Decided to buy Logitech G Pro X Superlight",
            tags=["gaming", "hardware"]
        )
        assert artifact.status == "resolved"
        assert artifact.resolution == "Decided to buy Logitech G Pro X Superlight"

    def test_create_fact(self):
        artifact = Artifact(
            id="fact1",
            artifact_type="fact",
            summary="The capital of France is Paris",
            expires=True
        )
        assert artifact.artifact_type == "fact"
        assert artifact.expires is True

    def test_create_event(self):
        artifact = Artifact(
            id="event1",
            artifact_type="event",
            summary="User mentioned they're tired today",
            expires=True
        )
        assert artifact.artifact_type == "event"

    def test_default_values(self):
        artifact = Artifact(
            id="test",
            artifact_type="fact",
            summary="Test"
        )
        assert artifact.status is None
        assert artifact.resolution is None
        assert artifact.related_to is None
        assert artifact.tags == []
        assert artifact.ref_count == 0
        assert artifact.expires is False


class TestConversationState:
    def test_empty_state(self):
        state = ConversationState()
        assert state.artifacts == []

    def test_get_open_efforts(self):
        state = ConversationState(artifacts=[
            Artifact(id="1", artifact_type="effort", summary="Open effort", status="open"),
            Artifact(id="2", artifact_type="effort", summary="Resolved effort", status="resolved", resolution="Done"),
            Artifact(id="3", artifact_type="fact", summary="A fact"),
        ])
        open_efforts = state.get_open_efforts()
        assert len(open_efforts) == 1
        assert open_efforts[0].id == "1"

    def test_get_resolved_efforts(self):
        state = ConversationState(artifacts=[
            Artifact(id="1", artifact_type="effort", summary="Open effort", status="open"),
            Artifact(id="2", artifact_type="effort", summary="Resolved effort", status="resolved", resolution="Done"),
        ])
        resolved = state.get_resolved_efforts()
        assert len(resolved) == 1
        assert resolved[0].id == "2"

    def test_get_facts(self):
        state = ConversationState(artifacts=[
            Artifact(id="1", artifact_type="effort", summary="An effort", status="open"),
            Artifact(id="2", artifact_type="fact", summary="Fact 1"),
            Artifact(id="3", artifact_type="fact", summary="Fact 2"),
        ])
        facts = state.get_facts()
        assert len(facts) == 2

    def test_serialization_roundtrip(self):
        state = ConversationState(artifacts=[
            Artifact(id="1", artifact_type="effort", summary="Test", status="resolved", resolution="Done"),
        ])
        json_str = state.model_dump_json()
        loaded = ConversationState.model_validate_json(json_str)
        assert len(loaded.artifacts) == 1
        assert loaded.artifacts[0].resolution == "Done"
