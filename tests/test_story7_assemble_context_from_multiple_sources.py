"""Tests for Story 7: Assemble Context from Multiple Sources"""

import json
import tempfile
from pathlib import Path
import yaml
from unittest.mock import patch, MagicMock


class TestStory7AssembleContext:
    """Story 7: Assemble Context from Multiple Sources"""

    def test_build_turn_context_includes_ambient_raw_log(self, tmp_path):
        """The context for each turn includes all ambient messages (raw.jsonl)"""
        from oi.context import build_turn_context
        from oi.models import ConversationState
        raw_log = tmp_path / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )
        state = ConversationState(artifacts=[])
        context = build_turn_context(state, tmp_path)
        assert "Hey, how's it going?" in context
        assert "Good! Ready to help." in context

    def test_build_turn_context_includes_effort_summaries_from_manifest(self, tmp_path):
        """The context for each turn includes all effort summaries (from manifest.yaml)"""
        from oi.context import build_turn_context
        from oi.models import ConversationState
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(yaml.dump({
            "efforts": [
                {"id": "auth-bug", "status": "concluded", "summary": "Debugged 401 errors after 1 hour."},
                {"id": "guild-feature", "status": "open", "summary": "Adding member limit to guilds."}
            ]
        }))
        state = ConversationState(artifacts=[])
        context = build_turn_context(state, tmp_path)
        assert "Debugged 401 errors after 1 hour." in context
        assert "Adding member limit to guilds." in context

    def test_build_turn_context_includes_full_raw_logs_of_open_efforts(self, tmp_path):
        """The context for each turn includes the full raw logs of all open efforts"""
        from oi.context import build_turn_context
        from oi.models import Artifact, ConversationState
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        open_effort_log = efforts_dir / "guild-feature.jsonl"
        open_effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's work on guild member limits."}) + "\n" +
            json.dumps({"role": "assistant", "content": "What's the max you're thinking?"}) + "\n"
        )
        concluded_effort_log = efforts_dir / "auth-bug.jsonl"
        concluded_effort_log.write_text(
            json.dumps({"role": "user", "content": "Debug the auth bug."}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n"
        )
        state = ConversationState(artifacts=[
            Artifact(id="guild-feature", artifact_type="effort", summary="Adding member limit", status="open"),
            Artifact(id="auth-bug", artifact_type="effort", summary="Debugged 401", status="resolved")
        ])
        context = build_turn_context(state, tmp_path)
        assert "Let's work on guild member limits." in context
        assert "What's the max you're thinking?" in context
        assert "Debug the auth bug." not in context
        assert "Opening effort: auth-bug" not in context

    def test_build_turn_context_combines_all_sources(self, tmp_path):
        """The context includes ambient, summaries, and open effort logs together"""
        from oi.context import build_turn_context
        from oi.models import Artifact, ConversationState
        raw_log = tmp_path / "raw.jsonl"
        raw_log.write_text(json.dumps({"role": "user", "content": "Ambient message."}) + "\n")
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(yaml.dump({
            "efforts": [
                {"id": "effort1", "status": "concluded", "summary": "Summary of concluded effort."}
            ]
        }))
        efforts_dir = tmp_path / "efforts"
        efforts_dir.mkdir()
        open_log = efforts_dir / "effort2.jsonl"
        open_log.write_text(json.dumps({"role": "user", "content": "Open effort message."}) + "\n")
        state = ConversationState(artifacts=[
            Artifact(id="effort2", artifact_type="effort", summary="Open effort", status="open")
        ])
        context = build_turn_context(state, tmp_path)
        assert "Ambient message." in context
        assert "Summary of concluded effort." in context
        assert "Open effort message." in context

    def test_build_turn_context_handles_missing_files_gracefully(self, tmp_path):
        """The context assembly works when some files are missing"""
        from oi.context import build_turn_context
        from oi.models import Artifact, ConversationState
        state = ConversationState(artifacts=[
            Artifact(id="nonexistent", artifact_type="effort", summary="Missing", status="open")
        ])
        context = build_turn_context(state, tmp_path)
        assert isinstance(context, str)
        assert "Missing" in context