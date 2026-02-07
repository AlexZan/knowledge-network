"""Tests for Story 8: Start a New Effort After Concluding One"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, Mock
import tempfile

class TestStory8StartNewEffortAfterConcludingOne:
    """Story 8: Start a New Effort After Concluding One"""

    def test_user_can_start_new_effort_after_concluding_one(self, tmp_path):
        """After concluding an effort, I can say 'Let's work on Y' to start a new effort"""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import load_state
        from oi.models import ConversationState
        
        # Create a state with a concluded effort
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create manifest with concluded effort
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
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Create raw.jsonl with ambient chatter
        raw_log = state_dir / "raw.jsonl"
        raw_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"role": "assistant", "content": "Good! Ready to help."})
        ]))
        
        # Create concluded effort file
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text("concluded effort content")
        
        # Load initial state
        initial_state = load_state(state_dir)
        
        # Mock LLM to simulate assistant recognizing new effort
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Opening effort: guild-feature\n\nFor member limits, a few questions..."
            
            # Act - user starts new effort
            new_state = process_turn(initial_state, "Let's work on the guild feature - I want to add a member limit", "gpt-4")
        
        # Assert - new effort created in manifest
        saved_manifest = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        effort_ids = [e["id"] for e in saved_manifest["efforts"]]
        assert "guild-feature" in effort_ids
        
        # Assert - new effort marked as open
        new_effort = next(e for e in saved_manifest["efforts"] if e["id"] == "guild-feature")
        assert new_effort["status"] == "open"
        
        # Assert - concluded effort still present
        assert "auth-bug" in effort_ids
        concluded_effort = next(e for e in saved_manifest["efforts"] if e["id"] == "auth-bug")
        assert concluded_effort["status"] == "concluded"

    def test_new_effort_file_created(self, tmp_path):
        """The assistant creates a new effort file for Y"""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import load_state, save_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create minimal state with concluded effort
        manifest = {"efforts": [{"id": "old-effort", "status": "concluded", "summary": "old work"}]}
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (state_dir / "raw.jsonl").write_text("")
        
        # Create state object
        state = ConversationState()
        
        # Mock LLM response that includes effort name
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Opening effort: new-task\n\nLet's begin..."
            
            # Act
            new_state = process_turn(state, "Let's work on new-task", "gpt-4")
            save_state(new_state, state_dir)
        
        # Assert - new effort file exists
        effort_file = state_dir / "efforts" / "new-task.jsonl"
        assert effort_file.exists()
        
        # Assert - file contains the assistant's opening message
        content = effort_file.read_text()
        assert "Opening effort: new-task" in content

    def test_new_effort_marked_open_in_manifest(self, tmp_path):
        """The new effort is marked as 'open' in the manifest"""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import load_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create state with no efforts initially
        manifest = {"efforts": []}
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (state_dir / "raw.jsonl").write_text("")
        
        state = load_state(state_dir)
        
        # Mock LLM
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Opening effort: database-migration\n\nWe need to plan..."
            
            # Act
            new_state = process_turn(state, "Let's work on database migration", "gpt-4")
        
        # Assert - manifest updated with open effort
        saved_manifest = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        assert len(saved_manifest["efforts"]) == 1
        
        new_effort = saved_manifest["efforts"][0]
        assert new_effort["id"] == "database-migration"
        assert new_effort["status"] == "open"
        assert "raw_file" in new_effort
        assert new_effort["raw_file"] == "efforts/database-migration.jsonl"

    def test_context_includes_ambient_summaries_and_new_effort_raw(self, tmp_path):
        """The context includes: ambient + all summaries (including the just-concluded effort) + new effort's raw log"""
        # Arrange
        from oi.conversation import process_turn
        from oi.context import build_context
        from oi.storage import load_state
        from oi.models import ConversationState
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create state with concluded effort and ambient chatter
        manifest = {
            "efforts": [
                {
                    "id": "auth-bug",
                    "status": "concluded",
                    "summary": "Fixed token refresh issue with axios interceptor",
                    "raw_file": "efforts/auth-bug.jsonl"
                }
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Create ambient raw log
        ambient_lines = [
            {"role": "user", "content": "How's the weather?"},
            {"role": "assistant", "content": "Sunny and warm."}
        ]
        (state_dir / "raw.jsonl").write_text('\n'.join(json.dumps(line) for line in ambient_lines))
        
        # Create concluded effort file
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "auth-bug.jsonl").write_text("detailed auth bug conversation")
        
        state = load_state(state_dir)
        
        # Mock LLM to start new effort
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Opening effort: ui-redesign\n\nLet's discuss the new layout..."
            
            # Act - start new effort
            new_state = process_turn(state, "Let's work on UI redesign", "gpt-4")
        
        # Act - build context after new effort started
        context = build_context(new_state)
        
        # Assert - context includes ambient chatter
        assert "How's the weather?" in context
        assert "Sunny and warm" in context
        
        # Assert - context includes concluded effort summary
        assert "Fixed token refresh issue with axios interceptor" in context
        
        # Assert - context includes new effort's opening (from LLM response)
        assert "Opening effort: ui-redesign" in context
        
        # Assert - context does NOT include raw concluded effort details
        assert "detailed auth bug conversation" not in context
        
        # Assert - new effort raw file exists and is referenced
        new_effort_file = state_dir / "efforts" / "ui-redesign.jsonl"
        assert new_effort_file.exists()
        new_effort_content = new_effort_file.read_text()
        assert "Opening effort: ui-redesign" in new_effort_content

    def test_multiple_concluded_efforts_summaries_in_context(self, tmp_path):
        """Context includes summaries from all concluded efforts when starting new effort"""
        # Arrange
        from oi.conversation import process_turn
        from oi.context import build_context
        from oi.storage import load_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create manifest with multiple concluded efforts
        manifest = {
            "efforts": [
                {
                    "id": "effort-1",
                    "status": "concluded",
                    "summary": "Summary of first concluded effort",
                    "raw_file": "efforts/effort-1.jsonl"
                },
                {
                    "id": "effort-2",
                    "status": "concluded",
                    "summary": "Summary of second concluded effort",
                    "raw_file": "efforts/effort-2.jsonl"
                }
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (state_dir / "raw.jsonl").write_text("")
        
        # Create effort files
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "effort-1.jsonl").write_text("raw 1")
        (efforts_dir / "effort-2.jsonl").write_text("raw 2")
        
        state = load_state(state_dir)
        
        # Mock LLM
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Opening effort: effort-3\n\nStarting new work..."
            
            # Act - start new effort
            new_state = process_turn(state, "Let's work on effort-3", "gpt-4")
        
        # Build context
        context = build_context(new_state)
        
        # Assert - both concluded effort summaries are in context
        assert "Summary of first concluded effort" in context
        assert "Summary of second concluded effort" in context
        
        # Assert - new effort opening is in context
        assert "Opening effort: effort-3" in context

    def test_effort_id_generated_from_user_message(self, tmp_path):
        """Effort ID is generated or extracted from user's 'Let's work on X' message"""
        # Arrange
        from oi.conversation import process_turn
        from oi.storage import load_state, save_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        (state_dir / "manifest.yaml").write_text(yaml.dump({"efforts": []}))
        (state_dir / "raw.jsonl").write_text("")
        
        state = load_state(state_dir)
        
        # Mock LLM to extract/generate effort ID
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Opening effort: payment-integration\n\nLet's discuss..."
            
            # Act - user mentions specific topic
            new_state = process_turn(state, "Let's work on payment integration with Stripe", "gpt-4")
            save_state(new_state, state_dir)
        
        # Assert - effort ID based on topic
        saved_manifest = yaml.safe_load((state_dir / "manifest.yaml").read_text())
        effort = saved_manifest["efforts"][0]
        
        # ID should be a slugified version of the topic
        assert "payment" in effort["id"].lower() or "payment-integration" == effort["id"]
        assert effort["status"] == "open"

    def test_new_effort_context_excludes_other_open_efforts_raw(self, tmp_path):
        """When starting new effort, context doesn't include raw logs of other open efforts (only summaries if concluded)"""
        # Arrange
        from oi.conversation import process_turn
        from oi.context import build_context
        from oi.storage import load_state
        
        state_dir = tmp_path / "session"
        state_dir.mkdir()
        
        # Create manifest with one open effort and one concluded
        manifest = {
            "efforts": [
                {
                    "id": "open-effort",
                    "status": "open",
                    "summary": "Should not be in summary form",
                    "raw_file": "efforts/open-effort.jsonl"
                },
                {
                    "id": "concluded-effort",
                    "status": "concluded",
                    "summary": "This concluded summary should be in context",
                    "raw_file": "efforts/concluded-effort.jsonl"
                }
            ]
        }
        (state_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (state_dir / "raw.jsonl").write_text("")
        
        # Create effort files with identifiable content
        efforts_dir = state_dir / "efforts"
        efforts_dir.mkdir()
        (efforts_dir / "open-effort.jsonl").write_text("RAW DETAILS OF OPEN EFFORT - SHOULD NOT BE IN CONTEXT")
        (efforts_dir / "concluded-effort.jsonl").write_text("RAW DETAILS OF CONCLUDED EFFORT")
        
        state = load_state(state_dir)
        
        # Mock LLM to start another new effort
        with patch("oi.llm.chat") as mock_chat:
            mock_chat.return_value = "Opening effort: third-effort\n\nBeginning..."
            
            # Act - start third effort
            new_state = process_turn(state, "Let's work on third thing", "gpt-4")
        
        # Build context for the new state
        context = build_context(new_state)
        
        # Assert - concluded effort summary IS in context
        assert "This concluded summary should be in context" in context
        
        # Assert - open effort raw details are NOT in context (only new effort's raw)
        assert "RAW DETAILS OF OPEN EFFORT - SHOULD NOT BE IN CONTEXT" not in context
        
        # Assert - new effort's opening is in context
        assert "Opening effort: third-effort" in context