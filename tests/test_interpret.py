"""Tests for agentic interpretation."""

import pytest
from unittest.mock import patch

from oi.interpret import interpret_exchange, ArtifactInterpretation


class TestInterpretExchange:
    def test_parses_valid_effort_response(self):
        mock_response = '''{
            "should_capture": true,
            "artifact_type": "effort",
            "summary": "User wants to add multiplayer mode",
            "status": "open",
            "related_to": null,
            "tags": ["game", "multiplayer"],
            "reasoning": "User is starting new work on a feature"
        }'''

        with patch("oi.interpret.chat", return_value=mock_response):
            result = interpret_exchange(
                "I want to add multiplayer mode",
                "That sounds exciting! What type of multiplayer are you thinking?",
                model="test-model"
            )

        assert result.should_capture is True
        assert result.artifact_type == "effort"
        assert result.status == "open"
        assert "multiplayer" in result.summary.lower()

    def test_parses_no_capture_response(self):
        mock_response = '''{
            "should_capture": false,
            "artifact_type": null,
            "summary": null,
            "status": null,
            "related_to": null,
            "tags": [],
            "reasoning": "Just a greeting, no value to capture"
        }'''

        with patch("oi.interpret.chat", return_value=mock_response):
            result = interpret_exchange(
                "Hello",
                "Hi there!",
                model="test-model"
            )

        assert result.should_capture is False
        assert result.artifact_type is None

    def test_parses_fact_response(self):
        mock_response = '''{
            "should_capture": true,
            "artifact_type": "fact",
            "summary": "Paris is the capital of France",
            "status": null,
            "related_to": null,
            "tags": ["geography"],
            "reasoning": "Simple Q&A about public knowledge"
        }'''

        with patch("oi.interpret.chat", return_value=mock_response):
            result = interpret_exchange(
                "What's the capital of France?",
                "Paris",
                model="test-model"
            )

        assert result.should_capture is True
        assert result.artifact_type == "fact"

    def test_handles_markdown_wrapped_json(self):
        mock_response = '''```json
{
    "should_capture": true,
    "artifact_type": "effort",
    "summary": "Choosing a frontend framework",
    "status": "resolved",
    "resolution": "Decided to use React",
    "tags": ["tech", "decision"],
    "reasoning": "A decision was made"
}
```'''

        with patch("oi.interpret.chat", return_value=mock_response):
            result = interpret_exchange(
                "Let's use React",
                "Great choice!",
                model="test-model"
            )

        assert result.should_capture is True
        assert result.artifact_type == "effort"
        assert result.status == "resolved"
        assert result.resolution == "Decided to use React"

    def test_handles_invalid_json(self):
        mock_response = "This is not valid JSON"

        with patch("oi.interpret.chat", return_value=mock_response):
            result = interpret_exchange(
                "test",
                "test",
                model="test-model"
            )

        assert result.should_capture is False
        assert "Failed to parse" in result.reasoning


class TestArtifactInterpretation:
    def test_model_defaults(self):
        interp = ArtifactInterpretation(
            should_capture=True,
            reasoning="Test"
        )
        assert interp.tags == []
        assert interp.artifact_type is None
        assert interp.status is None
