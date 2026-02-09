"""Tests for Story 8: Start a New Effort After Concluding One"""

import pytest
import yaml
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStory8StartNewEffortAfterConcludingOne:
    """Story 8: Start a New Effort After Concluding One"""

    def test_after_concluding_effort_user_can_start_new_one(self, tmp_path):
        """After concluding an effort, I can say 'Let's work on Y' to start a new effort"""
        # Arrange
        from oi.storage import load_state, save_state
        from oi.conversation import process_turn
        from oi.models import ConversationState
        
        # Setup state with concluded effort
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create concluded effort in manifest
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Debugged 401 errors after 1 hour",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        
        manifest_path = state_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))
        
        # Create raw.jsonl with ambient chatter
        raw_log = state_dir / "raw.jsonl"
        raw_log.write_text("\n".join([
            json.dumps({"role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"role": "assistant", "content": "Good! Ready to help."})
        ]))
        
        # Create efforts directory
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        
        # Create concluded effort log
        (efforts_dir / "auth-bug.jsonl").write_text("\n".join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"})
        ]))
        
        # Load state
        state = load_state(state_dir)
        
        # Mock LLM to return response that opens new effort
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: guild-feature\n\nFor member limits, a few questions..."
            
            # Act
            new_state, assistant_response = process_turn(
                state, 
                "Now let's work on the guild feature - I want to add a member limit",
                "gpt-4"
            )
            
            # Save the new state
            save_state(new_state, state_dir)
        
        # Assert - Check that new effort was opened
        loaded_manifest = yaml.safe_load(manifest_path.read_text())
        effort_ids = [e["id"] for e in loaded_manifest["efforts"]]
        assert "guild-feature" in effort_ids
        
        # Check that new effort is open
        new_effort = [e for e in loaded_manifest["efforts"] if e["id"] == "guild-feature"][0]
        assert new_effort["status"] == "open"

    def test_assistant_creates_new_effort_file(self, tmp_path):
        """The assistant creates a new effort file for Y"""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import load_state, save_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Setup state with concluded effort and no open efforts
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Previous effort"
                }
            ]
        }
        
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (state_dir / "raw.jsonl").write_text("")
        (state_dir / "efforts").mkdir()
        
        state = load_state(state_dir)
        
        # Mock LLM response that opens new effort
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: database-optimization"
            
            # Act
            new_state, _ = process_turn(
                state,
                "Let's work on database optimization",
                "gpt-4"
            )
            save_state(new_state, state_dir)
        
        # Assert - New effort file should exist
        effort_file = state_dir / "efforts" / "database-optimization.jsonl"
        assert effort_file.exists()
        
        # Should contain the exchange that opened it
        content = effort_file.read_text()
        assert "database optimization" in content.lower()

    def test_new_effort_marked_open_in_manifest(self, tmp_path):
        """The new effort is marked as 'open' in the manifest"""
        # Arrange
        from oi.conversation import conclude_effort, process_turn
        from oi.storage import load_state, save_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        
        # Start with an open effort
        manifest = {
            "efforts": [
                {
                    "id": "first-effort",
                    "status": "open",
                    "raw_file": "efforts/first-effort.jsonl"
                }
            ]
        }
        
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (efforts_dir / "first-effort.jsonl").write_text("")
        
        state = load_state(state_dir)
        
        # Mock LLM for concluding first effort
        with patch('oi.llm.extract_conclusion') as mock_extract:
            mock_extract.return_value = MagicMock(summary="Concluded first effort")
            
            # Conclude the first effort
            conclude_effort("first-effort", state_dir)
        
        # Mock LLM for opening new effort
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: second-effort"
            
            # Open new effort
            new_state, _ = process_turn(
                load_state(state_dir),
                "Let's work on second effort",
                "gpt-4"
            )
            save_state(new_state, state_dir)
        
        # Assert
        manifest = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        
        # Find the new effort
        new_effort = None
        for effort in manifest["efforts"]:
            if effort["id"] == "second-effort":
                new_effort = effort
                break
        
        assert new_effort is not None, "New effort not found in manifest"
        assert new_effort["status"] == "open"
        
        # First effort should still be concluded
        first_effort = next(e for e in manifest["efforts"] if e["id"] == "first-effort")
        assert first_effort["status"] == "concluded"

    def test_context_includes_ambient_summaries_and_new_effort_raw(self, tmp_path):
        """The context includes: ambient + all summaries (including the just-concluded effort) + new effort's raw log"""
        # Arrange
        from oi.conversation import build_context, process_turn, conclude_effort
        from oi.storage import load_state, save_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        
        # Setup: ambient chatter + concluded effort + open new effort
        raw_log = state_dir / "raw.jsonl"
        raw_log.write_text("\n".join([
            json.dumps({"role": "user", "content": "Ambient message 1"}),
            json.dumps({"role": "assistant", "content": "Ambient response 1"})
        ]))
        
        # Create concluded effort with summary
        manifest = {
            "efforts": [
                {
                    "id": "concluded-effort",
                    "status": "concluded",
                    "summary": "Summary of concluded work",
                    "raw_file": "efforts/concluded-effort.jsonl"
                },
                {
                    "id": "new-effort",
                    "status": "open",
                    "raw_file": "efforts/new-effort.jsonl"
                }
            ]
        }
        
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Create effort logs
        (efforts_dir / "concluded-effort.jsonl").write_text(
            json.dumps({"role": "user", "content": "Old work message"})
        )
        
        (efforts_dir / "new-effort.jsonl").write_text("\n".join([
            json.dumps({"role": "user", "content": "Let's work on new thing"}),
            json.dumps({"role": "assistant", "content": "Opening new effort"})
        ]))
        
        state = load_state(state_dir)
        
        # Act
        context = build_context(state)
        
        # Assert - Check context includes all required parts
        context_text = str(context)
        
        # Should include ambient chatter
        assert "Ambient message 1" in context_text
        
        # Should include summary of concluded effort
        assert "Summary of concluded work" in context_text
        
        # Should include raw log of new effort
        assert "Let's work on new thing" in context_text
        assert "Opening new effort" in context_text
        
        # Should NOT include raw log of concluded effort (only summary)
        assert "Old work message" not in context_text

    def test_multiple_concluded_efforts_all_summaries_in_context(self, tmp_path):
        """When starting new effort after multiple concluded efforts, all summaries are in context"""
        # Arrange
        from oi.conversation import build_context, process_turn
        from oi.storage import load_state, save_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Setup manifest with multiple concluded efforts
        manifest = {
            "efforts": [
                {
                    "id": "effort-1",
                    "status": "concluded",
                    "summary": "First effort summary"
                },
                {
                    "id": "effort-2",
                    "status": "concluded",
                    "summary": "Second effort summary"
                },
                {
                    "id": "effort-3",
                    "status": "open",
                    "raw_file": "efforts/effort-3.jsonl"
                }
            ]
        }
        
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Create raw ambient
        (state_dir / "raw.jsonl").write_text(
            json.dumps({"role": "user", "content": "Ambient"})
        )
        
        # Create effort log for open effort
        (state_dir / "efforts").mkdir()
        (state_dir / "efforts" / "effort-3.jsonl").write_text(
            json.dumps({"role": "user", "content": "New work"})
        )
        
        state = load_state(state_dir)
        
        # Act
        context = build_context(state)
        context_text = str(context)
        
        # Assert
        assert "First effort summary" in context_text
        assert "Second effort summary" in context_text
        assert "New work" in context_text  # Raw from open effort
        assert "Ambient" in context_text

    def test_new_effort_id_generated_if_not_provided(self, tmp_path):
        """If user doesn't name effort, system generates unique ID"""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import load_state, save_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        (state_dir / "manifest.yaml").write_text(yaml.dump({"efforts": []}))
        (state_dir / "raw.jsonl").write_text("")
        (state_dir / "efforts").mkdir()
        
        state = load_state(state_dir)
        
        # Mock LLM response that opens effort with generated ID
        with patch('oi.llm.chat') as mock_chat:
            mock_chat.return_value = "Opening effort"
            
            # Mock generate_id to return predictable ID
            with patch('oi.conversation.generate_id') as mock_generate:
                mock_generate.return_value = "generated-effort-123"
                
                # Act
                new_state, _ = process_turn(
                    state,
                    "Let's work on something",
                    "gpt-4"
                )
                save_state(new_state, state_dir)
        
        # Assert
        manifest = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        
        # Should have effort with generated ID
        effort_ids = [e["id"] for e in manifest["efforts"]]
        assert "generated-effort-123" in effort_ids
        
        # Corresponding effort file should exist
        effort_file = state_dir / "efforts" / "generated-effort-123.jsonl"
        assert effort_file.exists()