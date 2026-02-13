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

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Good! Ready to help."
            result = process_turn(session_dir, "Hey, how's it going?")

        # Verify: ambient raw log has both messages
        raw_log = session_dir / "raw.jsonl"
        assert raw_log.exists()
        messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert any(m["role"] == "user" and "how's it going" in m["content"] for m in messages)
        assert any(m["role"] == "assistant" and "Good! Ready" in m["content"] for m in messages)

        # Verify: manifest is empty
        manifest_path = session_dir / "manifest.yaml"
        if manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text())
            assert not manifest.get("efforts", [])

        # Verify: LLM received just the user message with system prompt
        assert mock_chat.called
        call_args = mock_chat.call_args[0][0]  # messages list
        assert any(m["role"] == "system" for m in call_args)
        assert call_args[-1]["role"] == "user"
        assert "how's it going" in call_args[-1]["content"]


class TestOpenEffort:
    """Turns 3-4: Open effort creates effort log and manifest entry"""

    def test_open_effort_creates_effort_log_and_manifest(self, tmp_path):
        """User opens effort → effort file created → manifest updated"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?", "timestamp": "2024-01-01T00:00:00"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help.", "timestamp": "2024-01-01T00:00:01"}) + "\n"
        )

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: auth-bug\n\nThat timing suggests token expiration. A few questions:\n1. What's your access token TTL?\n2. Are you using refresh tokens?"
            result = process_turn(session_dir, "Let's debug the auth bug - users are getting 401s after about an hour")

        # Verify: effort file created with both messages
        effort_log = session_dir / "efforts" / "auth-bug.jsonl"
        assert effort_log.exists()
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 2
        assert effort_messages[0]["role"] == "user"
        assert "auth bug" in effort_messages[0]["content"].lower()
        assert effort_messages[1]["role"] == "assistant"
        assert "Opening effort: auth-bug" in effort_messages[1]["content"]

        # Verify: manifest updated with open effort
        manifest_path = session_dir / "manifest.yaml"
        assert manifest_path.exists()
        manifest = yaml.safe_load(manifest_path.read_text())
        assert "efforts" in manifest
        assert len(manifest["efforts"]) == 1
        assert manifest["efforts"][0]["id"] == "auth-bug"
        assert manifest["efforts"][0]["status"] == "open"

        # Verify: raw log unchanged (still just ambient)
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 2  # Original ambient messages

        # Verify: LLM received context with ambient history
        call_args = mock_chat.call_args[0][0]
        # Should have system prompt
        assert any(m["role"] == "system" for m in call_args)
        # Should include ambient history in context
        call_content = "\n".join([m.get("content", "") for m in call_args])
        assert "Hey, how's it going" in call_content
        assert "Good! Ready" in call_content


class TestWorkingOnEffort:
    """Turns 5-10: Messages within open effort go to effort log"""

    def test_effort_message_saved_to_effort_log_not_raw(self, tmp_path):
        """User message during open effort → goes to effort log, not raw"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?", "timestamp": "2024-01-01T00:00:00"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help.", "timestamp": "2024-01-01T00:00:01"}) + "\n"
        )

        # Set up open effort with opening exchange
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug - users are getting 401s after about an hour", "timestamp": "2024-01-01T00:00:02"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug\n\nThat timing suggests token expiration...", "timestamp": "2024-01-01T00:00:03"}) + "\n"
        )

        # Set up manifest with open effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "created": "2024-01-01T00:00:02",
                    "updated": "2024-01-01T00:00:03"
                }
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "The 1-hour TTL matches the failure timing. Let me see your refresh logic."
            result = process_turn(session_dir, "Access token is 1 hour, yes we have refresh tokens")

        # Verify: effort log got new messages
        effort_log = session_dir / "efforts" / "auth-bug.jsonl"
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 4  # Original 2 + new 2
        assert effort_messages[2]["role"] == "user"
        assert "Access token is 1 hour" in effort_messages[2]["content"]
        assert effort_messages[3]["role"] == "assistant"
        assert "1-hour TTL matches" in effort_messages[3]["content"]

        # Verify: raw log unchanged
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 2  # Still just original ambient

        # Verify: manifest unchanged (still open)
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        assert manifest["efforts"][0]["status"] == "open"

        # Verify: LLM received effort context (including previous effort messages)
        call_args = mock_chat.call_args[0][0]
        call_content = "\n".join([m.get("content", "") for m in call_args])
        # Should include effort context
        assert "auth bug" in call_content.lower()
        assert "Opening effort: auth-bug" in call_content
        # Should NOT include raw ambient in context (only in system prompt)
        # But might include ambient in "Recent Conversation" section
        # At minimum, user's current message should be in context
        assert "Access token is 1 hour" in call_content


class TestAmbientInterruption:
    """Turns 11-12: Ambient interruption during open effort"""

    def test_ambient_interruption_saves_to_raw_not_effort(self, tmp_path):
        """Unrelated message during open effort → goes to raw, not effort"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?", "timestamp": "2024-01-01T00:00:00"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help.", "timestamp": "2024-01-01T00:00:01"}) + "\n"
        )

        # Set up open effort with several messages
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug...", "timestamp": "2024-01-01T00:00:02"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug...", "timestamp": "2024-01-01T00:00:03"}) + "\n" +
            json.dumps({"role": "user", "content": "Access token is 1 hour...", "timestamp": "2024-01-01T00:00:04"}) + "\n" +
            json.dumps({"role": "assistant", "content": "The 1-hour TTL matches...", "timestamp": "2024-01-01T00:00:05"}) + "\n"
        )

        # Set up manifest with open effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "created": "2024-01-01T00:00:02",
                    "updated": "2024-01-01T00:00:05"
                }
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "72°F and sunny in Seattle today."
            result = process_turn(session_dir, "Quick question - what's the weather in Seattle?")

        # Verify: raw log got new messages
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 4  # Original 2 + new 2
        assert raw_messages[2]["role"] == "user"
        assert "weather in Seattle" in raw_messages[2]["content"]
        assert raw_messages[3]["role"] == "assistant"
        assert "72°F and sunny" in raw_messages[3]["content"]

        # Verify: effort log unchanged
        effort_log = session_dir / "efforts" / "auth-bug.jsonl"
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 4  # Still original 4

        # Verify: manifest unchanged
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        assert manifest["efforts"][0]["status"] == "open"

        # Verify: LLM received ambient context (not effort context)
        call_args = mock_chat.call_args[0][0]
        call_content = "\n".join([m.get("content", "") for m in call_args])
        # Should include ambient history
        assert "Hey, how's it going" in call_content
        assert "Good! Ready" in call_content
        # Should NOT include effort details in primary context
        # (might mention "you have an open effort: auth-bug" in system prompt)
        # But actual effort messages shouldn't be in the conversation history sent to LLM
        assert "auth bug" not in call_content.lower() or "open effort" in call_content  # Only summary


class TestConcludeEffort:
    """Turns 13-14: Conclude effort updates manifest with summary"""

    def test_conclude_effort_updates_manifest_and_saves_conclusion(self, tmp_path):
        """User concludes effort → manifest status changed to concluded with summary"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history (including interruption)
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?", "timestamp": "2024-01-01T00:00:00"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help.", "timestamp": "2024-01-01T00:00:01"}) + "\n" +
            json.dumps({"role": "user", "content": "Quick question - what's the weather in Seattle?", "timestamp": "2024-01-01T00:00:06"}) + "\n" +
            json.dumps({"role": "assistant", "content": "72°F and sunny in Seattle today.", "timestamp": "2024-01-01T00:00:07"}) + "\n"
        )

        # Set up open effort with several messages
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug...", "timestamp": "2024-01-01T00:00:02"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug...", "timestamp": "2024-01-01T00:00:03"}) + "\n" +
            json.dumps({"role": "user", "content": "Access token is 1 hour...", "timestamp": "2024-01-01T00:00:04"}) + "\n" +
            json.dumps({"role": "assistant", "content": "The 1-hour TTL matches...", "timestamp": "2024-01-01T00:00:05"}) + "\n"
        )

        # Set up manifest with open effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "open",
                    "created": "2024-01-01T00:00:02",
                    "updated": "2024-01-01T00:00:05"
                }
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Concluding effort: auth-bug\n\nSummary: Debugged 401 errors occurring after 1 hour. Root cause was refresh tokens existing but never being called automatically. Fixed by adding axios interceptor in tokenService.ts that proactively refreshes tokens before expiry.\n\nEffort concluded and summarized. Context freed up."
            result = process_turn(session_dir, "Back to auth - I implemented the interceptor and it works. Bug is fixed!")

        # Verify: effort log got conclusion messages
        effort_log = session_dir / "efforts" / "auth-bug.jsonl"
        effort_messages = [json.loads(line) for line in effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 6  # Original 4 + new 2
        assert effort_messages[4]["role"] == "user"
        assert "implemented the interceptor" in effort_messages[4]["content"]
        assert effort_messages[5]["role"] == "assistant"
        assert "Concluding effort: auth-bug" in effort_messages[5]["content"]

        # Verify: manifest updated to concluded with summary
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        assert len(manifest["efforts"]) == 1
        assert manifest["efforts"][0]["id"] == "auth-bug"
        assert manifest["efforts"][0]["status"] == "concluded"
        assert "summary" in manifest["efforts"][0]
        assert "401 errors" in manifest["efforts"][0]["summary"]
        assert "axios interceptor" in manifest["efforts"][0]["summary"]

        # Verify: raw log unchanged
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 4

        # Verify: LLM received effort context for conclusion
        call_args = mock_chat.call_args[0][0]
        call_content = "\n".join([m.get("content", "") for m in call_args])
        # Should include effort history in context for proper conclusion
        assert "auth bug" in call_content.lower()
        assert "Let's debug the auth bug" in call_content
        # Should include user's conclusion message
        assert "implemented the interceptor" in call_content


class TestOpenNewEffort:
    """Turns 15-16: Open new effort after concluding previous"""

    def test_new_effort_after_conclusion_creates_separate_log(self, tmp_path):
        """After concluding effort, new effort creates new file and manifest entry"""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        # Set up ambient history
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?", "timestamp": "2024-01-01T00:00:00"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help.", "timestamp": "2024-01-01T00:00:01"}) + "\n" +
            json.dumps({"role": "user", "content": "Quick question - what's the weather in Seattle?", "timestamp": "2024-01-01T00:00:06"}) + "\n" +
            json.dumps({"role": "assistant", "content": "72°F and sunny in Seattle today.", "timestamp": "2024-01-01T00:00:07"}) + "\n"
        )

        # Set up concluded effort log
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text(
            json.dumps({"role": "user", "content": "Let's debug the auth bug...", "timestamp": "2024-01-01T00:00:02"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug...", "timestamp": "2024-01-01T00:00:03"}) + "\n" +
            json.dumps({"role": "user", "content": "Access token is 1 hour...", "timestamp": "2024-01-01T00:00:04"}) + "\n" +
            json.dumps({"role": "assistant", "content": "The 1-hour TTL matches...", "timestamp": "2024-01-01T00:00:05"}) + "\n" +
            json.dumps({"role": "user", "content": "Back to auth - I implemented the interceptor...", "timestamp": "2024-01-01T00:00:08"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Concluding effort: auth-bug...", "timestamp": "2024-01-01T00:00:09"}) + "\n"
        )

        # Set up manifest with concluded effort
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor.",
                    "created": "2024-01-01T00:00:02",
                    "updated": "2024-01-01T00:00:09",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        with patch('oi.orchestrator.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: guild-feature\n\nFor member limits, a few questions:\n1. What's the max you're thinking?\n2. Should it be configurable per guild or global?"
            result = process_turn(session_dir, "Now let's work on the guild feature - I want to add a member limit")

        # Verify: new effort file created
        new_effort_log = session_dir / "efforts" / "guild-feature.jsonl"
        assert new_effort_log.exists()
        effort_messages = [json.loads(line) for line in new_effort_log.read_text().strip().split('\n')]
        assert len(effort_messages) == 2
        assert effort_messages[0]["role"] == "user"
        assert "guild feature" in effort_messages[0]["content"].lower()
        assert effort_messages[1]["role"] == "assistant"
        assert "Opening effort: guild-feature" in effort_messages[1]["content"]

        # Verify: old effort log unchanged
        old_effort_log = session_dir / "efforts" / "auth-bug.jsonl"
        old_messages = [json.loads(line) for line in old_effort_log.read_text().strip().split('\n')]
        assert len(old_messages) == 6

        # Verify: manifest has both efforts
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        assert len(manifest["efforts"]) == 2
        
        # Find each effort
        auth_effort = next(e for e in manifest["efforts"] if e["id"] == "auth-bug")
        guild_effort = next(e for e in manifest["efforts"] if e["id"] == "guild-feature")
        
        assert auth_effort["status"] == "concluded"
        assert guild_effort["status"] == "open"
        assert "raw_file" in guild_effort
        assert guild_effort["raw_file"] == "efforts/guild-feature.jsonl"

        # Verify: raw log unchanged
        raw_messages = [json.loads(line) for line in raw_log.read_text().strip().split('\n')]
        assert len(raw_messages) == 4

        # Verify: LLM received context with concluded effort summary (not raw)
        call_args = mock_chat.call_args[0][0]
        call_content = "\n".join([m.get("content", "") for m in call_args])
        # Should mention concluded effort in system prompt/context
        assert "auth-bug" in call_content or "401 errors" in call_content
        # But should NOT include raw effort messages
        assert "Let's debug the auth bug" not in call_content
        assert "Access token is 1 hour" not in call_content