"""Acceptance tests for Effort-Based Context Management"""

import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestAmbientChatter:
    """Turns 1-2: Ambient messages are captured and included in context"""

    def test_ambient_turn_saves_to_raw_log_and_returns_response(self, tmp_path):
        """A full ambient turn: user message → route → save → LLM → save response"""
        from oi.orchestrator import process_turn  # Will fail - doesn't exist yet

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # No pre-existing state - this is first turn
        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Good! Ready to help."
            result = process_turn(session_dir, "Hey, how's it going?")

        # Verify: ambient raw log has both messages
        raw_log = session_dir / "raw.jsonl"
        assert raw_log.exists()
        messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert any(m["role"] == "user" and "how's it going" in m["content"] for m in messages)
        assert any(m["role"] == "assistant" for m in messages)

        # Verify: no efforts directory created
        efforts_dir = session_dir / "efforts"
        assert not efforts_dir.exists()

        # Verify: no manifest yet (or empty)
        manifest_path = session_dir / "manifest.yaml"
        if manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text())
            assert "efforts" not in manifest or len(manifest.get("efforts", [])) == 0


class TestOpenEffort:
    """Turns 3-4: Open a new effort with focused work"""

    def test_open_effort_creates_effort_file_and_updates_manifest(self, tmp_path):
        """User opens effort → creates effort log, updates manifest, saves to raw log"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history from turns 1-2
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )

        # Create empty manifest
        manifest = {"efforts": []}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: auth-bug\n\nThat timing suggests token expiration. A few questions:\n1. What's your access token TTL?\n2. Are you using refresh tokens?"
            result = process_turn(session_dir, "Let's debug the auth bug - users are getting 401s after about an hour")

        # Verify: raw.jsonl unchanged (ambient log not modified)
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 2  # Still just the ambient messages

        # Verify: efforts directory exists
        efforts_dir = session_dir / "efforts"
        assert efforts_dir.exists()

        # Verify: effort file created with opening exchange
        effort_log = efforts_dir / "auth-bug.jsonl"
        assert effort_log.exists()
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 2
        assert any(m["role"] == "user" and "auth bug" in m["content"].lower() for m in effort_messages)
        assert any(m["role"] == "assistant" and "Opening effort: auth-bug" in m["content"] for m in effort_messages)

        # Verify: manifest updated with open effort
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        assert "efforts" in manifest
        auth_bug_effort = [e for e in manifest["efforts"] if e["id"] == "auth-bug"]
        assert len(auth_bug_effort) == 1
        assert auth_bug_effort[0]["status"] == "open"


class TestWorkOnEffort:
    """Turns 5-10: Working within an open effort"""

    def test_effort_message_saved_to_effort_log_not_raw(self, tmp_path):
        """During open effort, messages go to effort log, not raw.jsonl"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history (turns 1-2)
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )

        # Set up open effort with initial exchange (turns 3-4)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug - users are getting 401s after about an hour"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug\n\nThat timing suggests token expiration. A few questions:\n1. What's your access token TTL?\n2. Are you using refresh tokens?"}) + "\n"
        )

        # Set up manifest with open effort
        manifest = {"efforts": [{"id": "auth-bug", "status": "open"}]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "The 1-hour TTL matches the failure timing. Let me see your refresh logic."
            result = process_turn(session_dir, "Access token is 1 hour, yes we have refresh tokens")

        # Verify: raw.jsonl unchanged (still 2 ambient messages)
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 2

        # Verify: effort log has new messages appended
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 4  # Original 2 + new 2
        assert any(m["role"] == "user" and "Access token is 1 hour" in m["content"] for m in effort_messages)
        assert any(m["role"] == "assistant" and "1-hour TTL" in m["content"] for m in effort_messages)

        # Verify: manifest still has open effort (unchanged)
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        auth_bug_effort = [e for e in manifest["efforts"] if e["id"] == "auth-bug"]
        assert len(auth_bug_effort) == 1
        assert auth_bug_effort[0]["status"] == "open"


class TestAmbientInterruption:
    """Turns 11-12: Ambient interruption during open effort"""

    def test_ambient_during_effort_saves_to_raw_not_effort(self, tmp_path):
        """Ambient message during open effort goes to raw.jsonl, not effort log"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history (turns 1-2)
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )

        # Set up open effort with some history (turns 3-10)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text(
            "\n".join([
                json.dumps({"role": "user", "content": "Let's debug the auth bug..."}),
                json.dumps({"role": "assistant", "content": "Opening effort: auth-bug..."}),
                json.dumps({"role": "user", "content": "Access token is 1 hour..."}),
                json.dumps({"role": "assistant", "content": "The 1-hour TTL matches..."}),
                json.dumps({"role": "user", "content": "Here's the code from tokenService.ts..."}),
                json.dumps({"role": "assistant", "content": "That's the problem - the refresh function exists but nothing calls it..."}),
                json.dumps({"role": "user", "content": "Oh that makes sense. So the token just expires because nothing refreshes it."}),
                json.dumps({"role": "assistant", "content": "Exactly. The fix is:..."})
            ]) + "\n"
        )

        # Set up manifest with open effort
        manifest = {"efforts": [{"id": "auth-bug", "status": "open"}]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            result = process_turn(session_dir, "Quick question - what's the weather in Seattle?")

        # Verify: raw.jsonl has new ambient messages (total 4)
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 4
        assert any(m["role"] == "user" and "weather in Seattle" in m["content"] for m in raw_messages)
        assert any(m["role"] == "assistant" and "72°F" in m["content"] for m in raw_messages)

        # Verify: effort log unchanged (still 8 messages)
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 8

        # Verify: manifest unchanged
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        assert len(manifest["efforts"]) == 1
        assert manifest["efforts"][0]["status"] == "open"


class TestConcludeEffort:
    """Turns 13-14: Conclude an open effort"""

    def test_conclude_effort_updates_manifest_and_adds_summary(self, tmp_path):
        """Effort conclusion updates manifest status and adds summary"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history (turns 1-2, 11-12)
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            "\n".join([
                json.dumps({"role": "user", "content": "Hey, how's it going?"}),
                json.dumps({"role": "assistant", "content": "Good! Ready to help."}),
                json.dumps({"role": "user", "content": "Quick question - what's the weather in Seattle?"}),
                json.dumps({"role": "assistant", "content": "72°F and sunny in Seattle today."})
            ]) + "\n"
        )

        # Set up open effort with history (turns 3-10)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text(
            "\n".join([
                json.dumps({"role": "user", "content": "Let's debug the auth bug..."}),
                json.dumps({"role": "assistant", "content": "Opening effort: auth-bug..."}),
                json.dumps({"role": "user", "content": "Access token is 1 hour..."}),
                json.dumps({"role": "assistant", "content": "The 1-hour TTL matches..."}),
                json.dumps({"role": "user", "content": "Here's the code from tokenService.ts..."}),
                json.dumps({"role": "assistant", "content": "That's the problem - the refresh function exists but nothing calls it..."}),
                json.dumps({"role": "user", "content": "Oh that makes sense. So the token just expires because nothing refreshes it."}),
                json.dumps({"role": "assistant", "content": "Exactly. The fix is:..."})
            ]) + "\n"
        )

        # Set up manifest with open effort
        manifest = {"efforts": [{"id": "auth-bug", "status": "open", "created": "2024-01-01T00:00:00"}]}
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Concluding effort: auth-bug\n\nSummary: Debugged 401 errors occurring after 1 hour. Root cause was refresh tokens existing but never being called automatically. Fixed by adding axios interceptor in tokenService.ts that proactively refreshes tokens before expiry.\n\nEffort concluded and summarized. Context freed up."
            result = process_turn(session_dir, "Back to auth - I implemented the interceptor and it works. Bug is fixed!")

        # Verify: raw.jsonl unchanged (still 4 ambient messages)
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 4

        # Verify: effort log has conclusion messages appended (now 10 messages)
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 10
        assert any(m["role"] == "user" and "implemented the interceptor" in m["content"] for m in effort_messages)
        assert any(m["role"] == "assistant" and "Concluding effort: auth-bug" in m["content"] for m in effort_messages)

        # Verify: manifest updated to concluded with summary
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        auth_bug_effort = [e for e in manifest["efforts"] if e["id"] == "auth-bug"]
        assert len(auth_bug_effort) == 1
        assert auth_bug_effort[0]["status"] == "concluded"
        assert "summary" in auth_bug_effort[0]
        assert "401 errors" in auth_bug_effort[0]["summary"]
        assert "updated" in auth_bug_effort[0]  # Timestamp should be updated


class TestOpenNewEffort:
    """Turns 15-16: Open a new effort after concluding previous"""

    def test_open_new_effort_while_previous_is_concluded(self, tmp_path):
        """New effort opens while previous is concluded - both in manifest"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history (turns 1-2, 11-12)
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            "\n".join([
                json.dumps({"role": "user", "content": "Hey, how's it going?"}),
                json.dumps({"role": "assistant", "content": "Good! Ready to help."}),
                json.dumps({"role": "user", "content": "Quick question - what's the weather in Seattle?"}),
                json.dumps({"role": "assistant", "content": "72°F and sunny in Seattle today."})
            ]) + "\n"
        )

        # Set up concluded effort file (auth-bug)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text("concluded effort log content\n")

        # Set up manifest with concluded effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh.",
                    "created": "2024-01-01T00:00:00",
                    "updated": "2024-01-01T01:00:00"
                }
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: guild-feature\n\nFor member limits, a few questions:\n1. What's the max you're thinking?\n2. Should it be configurable per guild or global?"
            result = process_turn(session_dir, "Now let's work on the guild feature - I want to add a member limit")

        # Verify: raw.jsonl unchanged (still 4 ambient messages)
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 4

        # Verify: new effort file created
        new_effort_log = efforts_dir / "guild-feature.jsonl"
        assert new_effort_log.exists()
        effort_messages = [json.loads(line) for line in new_effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 2
        assert any(m["role"] == "user" and "guild feature" in m["content"].lower() for m in effort_messages)
        assert any(m["role"] == "assistant" and "Opening effort: guild-feature" in m["content"] for m in effort_messages)

        # Verify: manifest has both efforts - one concluded, one open
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        assert len(manifest["efforts"]) == 2
        
        auth_bug_effort = [e for e in manifest["efforts"] if e["id"] == "auth-bug"]
        assert len(auth_bug_effort) == 1
        assert auth_bug_effort[0]["status"] == "concluded"
        
        guild_feature_effort = [e for e in manifest["efforts"] if e["id"] == "guild-feature"]
        assert len(guild_feature_effort) == 1
        assert guild_feature_effort[0]["status"] == "open"
        assert "created" in guild_feature_effort[0]