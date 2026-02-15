"""E2E test: Script a full conversation through process_turn.

Mocks only the LLM layer (oi.llm.chat). Everything else runs for real:
file I/O, state management, routing, manifest updates.

Covers the full lifecycle: ambient → open effort → effort messages →
interruption → conclude effort → verify compaction.
"""

import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch


def read_jsonl(path: Path) -> list[dict]:
    """Read all entries from a JSONL file."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_manifest(session_dir: Path) -> dict:
    """Read manifest.yaml from session dir."""
    manifest_path = session_dir / "manifest.yaml"
    if not manifest_path.exists():
        return {"efforts": []}
    return yaml.safe_load(manifest_path.read_text())


class TestE2EConversation:
    """Full conversation lifecycle through process_turn."""

    def test_full_lifecycle(self, tmp_path):
        """Ambient → open effort → effort messages → interruption → conclude → verify."""
        from oi.orchestrator import process_turn

        session_dir = tmp_path / "session"
        session_dir.mkdir()
        raw_log = session_dir / "raw.jsonl"

        # Script LLM responses in order
        llm_responses = iter([
            # 1. Ambient greeting
            "Hello! How can I help you today?",
            # 2. Open effort (triggers effort creation)
            "Opening effort: auth-bug",
            # 3. Effort message (routed to effort, not interruption)
            "The refresh token logic looks correct. Check the TTL config.",
            # 4. Interruption (user says "quick question")
            "72°F and sunny in Seattle.",
            # 5. Back to effort (not an interruption)
            "I see the token expiry is set to 1 hour. That's too short.",
            # 6. Conclude effort
            "Concluding effort: auth-bug\n\nSummary: Fixed auth token TTL from 1hr to 24hr",
        ])

        with patch("oi.orchestrator.chat", side_effect=lambda msgs, **kw: next(llm_responses)):

            # --- Step 1: Ambient greeting ---
            response = process_turn(session_dir, "Hello!")
            assert response == "Hello! How can I help you today?"

            # Verify: logged to raw.jsonl
            ambient = read_jsonl(raw_log)
            assert len(ambient) == 2  # user + assistant
            assert ambient[0]["role"] == "user"
            assert ambient[0]["content"] == "Hello!"
            assert ambient[1]["role"] == "assistant"

            # No manifest yet
            assert not (session_dir / "manifest.yaml").exists()

            # --- Step 2: Open effort ---
            response = process_turn(session_dir, "Let's debug the auth bug")
            assert "Opening effort: auth-bug" in response

            # Verify: manifest created with open effort
            manifest = read_manifest(session_dir)
            efforts = manifest["efforts"]
            assert len(efforts) == 1
            assert efforts[0]["id"] == "auth-bug"
            assert efforts[0]["status"] == "open"

            # Verify: effort file created with user message + assistant confirmation
            effort_log = session_dir / "efforts" / "auth-bug.jsonl"
            assert effort_log.exists()
            effort_entries = read_jsonl(effort_log)
            assert len(effort_entries) == 2
            assert effort_entries[0]["role"] == "user"
            assert effort_entries[0]["content"] == "Let's debug the auth bug"
            assert effort_entries[1]["role"] == "assistant"

            # Verify: ambient log unchanged (effort doesn't go to ambient)
            ambient_after = read_jsonl(raw_log)
            assert len(ambient_after) == 2  # still just the greeting

            # --- Step 3: Effort message ---
            response = process_turn(session_dir, "Check the auth error logs")
            assert "refresh token" in response

            # Verify: message added to effort log
            effort_entries = read_jsonl(effort_log)
            assert len(effort_entries) == 4  # 2 from open + 2 from this exchange
            assert effort_entries[2]["role"] == "user"
            assert effort_entries[2]["content"] == "Check the auth error logs"
            assert effort_entries[3]["role"] == "assistant"

            # Verify: ambient log still unchanged
            assert len(read_jsonl(raw_log)) == 2

            # --- Step 4: Interruption ---
            response = process_turn(session_dir, "Quick question - what's the weather in Seattle?")
            assert "72°F" in response

            # Verify: logged to ambient (raw.jsonl)
            ambient_after_interrupt = read_jsonl(raw_log)
            assert len(ambient_after_interrupt) == 4  # greeting + interruption
            assert ambient_after_interrupt[2]["content"] == "Quick question - what's the weather in Seattle?"

            # Verify: effort log unchanged
            assert len(read_jsonl(effort_log)) == 4

            # Verify: effort still open
            manifest = read_manifest(session_dir)
            assert manifest["efforts"][0]["status"] == "open"

            # --- Step 5: Back to effort ---
            response = process_turn(session_dir, "The auth token expiry seems wrong")
            assert "1 hour" in response

            # Verify: added to effort log
            effort_entries = read_jsonl(effort_log)
            assert len(effort_entries) == 6
            assert effort_entries[4]["content"] == "The auth token expiry seems wrong"

            # --- Step 6: Conclude effort ---
            response = process_turn(session_dir, "The auth bug is fixed, looks good")
            assert "Concluding effort: auth-bug" in response

            # Verify: manifest updated to concluded with summary
            manifest = read_manifest(session_dir)
            auth_effort = manifest["efforts"][0]
            assert auth_effort["status"] == "concluded"
            assert auth_effort.get("summary") == "Fixed auth token TTL from 1hr to 24hr"

            # Verify: effort log has conclusion exchange
            effort_entries = read_jsonl(effort_log)
            assert len(effort_entries) == 8  # 6 + conclusion user + assistant

            # Verify: effort file still exists on disk (preserved, not deleted)
            assert effort_log.exists()
