"""Tests for Story 2: Explicitly Open New Effort"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, Mock
from oi.models import ConversationState, Artifact


class TestStory2ExplicitlyOpenEffort:
    """Story 2: User explicitly opens a new effort"""
    
    def test_detect_effort_opening_from_message_returns_effort_name(self):
        """When user says 'Let's work on X', detect effort opening and extract name"""
        from oi.detection import detect_effort_opening  # ImportError = red
        
        # Test various opening phrases
        test_cases = [
            ("Let's work on auth-bug", "auth-bug"),
            ("I want to debug the payment issue", "payment issue"),
            ("Can we focus on the guild feature?", "guild feature"),
            ("Let's tackle the auth bug", "auth bug"),
            ("How about we work on the login flow", "login flow"),
        ]
        
        for message, expected_name in test_cases:
            result = detect_effort_opening(message)
            assert result == expected_name, f"Failed for: {message}"
    
    def test_create_effort_file_creates_jsonl_in_efforts_dir(self, tmp_path):
        """When opening new effort, create efforts/X.jsonl file"""
        from oi.storage import create_effort_file  # ImportError = red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        effort_path = create_effort_file(session_dir, "auth-bug")
        
        assert effort_path.exists()
        assert effort_path.name == "auth-bug.jsonl"
        assert effort_path.parent == efforts_dir
        # Should be empty JSONL file initially
        content = effort_path.read_text().strip()
        assert content == ""  # Empty file
    
    def test_add_effort_to_manifest_creates_open_entry(self, tmp_path):
        """When effort opens, add entry with status=open to manifest.yaml"""
        from oi.storage import add_effort_to_manifest  # ImportError = red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        manifest_path = session_dir / "manifest.yaml"
        
        # Create initial manifest
        initial_manifest = {"ambient_messages": [], "efforts": []}
        manifest_path.write_text(yaml.dump(initial_manifest))
        
        # Add effort
        add_effort_to_manifest(session_dir, "auth-bug", "open")
        
        # Load and verify
        manifest = yaml.safe_load(manifest_path.read_text())
        assert len(manifest["efforts"]) == 1
        effort_entry = manifest["efforts"][0]
        assert effort_entry["id"] == "auth-bug"
        assert effort_entry["status"] == "open"
        assert "created" in effort_entry
        assert "updated" in effort_entry
    
    def test_route_message_to_effort_returns_effort_id_when_opening(self):
        """When user opens effort, routing returns effort ID instead of 'ambient'"""
        from oi.routing import route_message_to_effort  # ImportError = red
        
        state = ConversationState(artifacts=[])
        
        # With detection of opening phrase
        with patch('oi.routing.detect_effort_opening') as mock_detect:
            mock_detect.return_value = "auth-bug"
            result = route_message_to_effort(state, "Let's work on auth-bug")
            assert result == "auth-bug"
    
    def test_save_message_to_effort_log_appends_to_correct_file(self, tmp_path):
        """When effort is open, messages saved to effort's JSONL, not ambient"""
        from oi.storage import save_message_to_effort_log  # ImportError = red
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        effort_file = efforts_dir / "auth-bug.jsonl"
        effort_file.touch()
        
        # Save user message
        user_message = {"role": "user", "content": "Let's debug the auth bug"}
        save_message_to_effort_log(session_dir, "auth-bug", user_message)
        
        # Save assistant confirmation
        assistant_message = {"role": "assistant", "content": "Opening effort: auth-bug"}
        save_message_to_effort_log(session_dir, "auth-bug", assistant_message)
        
        # Verify both messages in effort log
        lines = effort_file.read_text().strip().split('\n')
        assert len(lines) == 2
        
        # Check user message
        user_saved = json.loads(lines[0])
        assert user_saved["role"] == "user"
        assert "auth bug" in user_saved["content"].lower()
        
        # Check assistant confirmation
        assistant_saved = json.loads(lines[1])
        assert assistant_saved["role"] == "assistant"
        assert "auth-bug" in assistant_saved["content"]
    
    def test_open_effort_creates_artifact_in_state(self):
        """When effort opens, create Artifact with type=effort and status=open"""
        from oi.efforts import open_effort  # ImportError = red
        
        state = ConversationState(artifacts=[])
        
        new_state = open_effort(state, "auth-bug", "Let's debug the auth bug")
        
        # Should have one artifact
        assert len(new_state.artifacts) == 1
        artifact = new_state.artifacts[0]
        
        assert artifact.id == "auth-bug"
        assert artifact.artifact_type == "effort"
        assert artifact.status == "open"
        assert "auth bug" in artifact.summary.lower()
        # Should have current timestamp
        assert artifact.created is not None
        assert artifact.updated is not None
    
    def test_generate_effort_opening_confirmation_includes_name(self):
        """Assistant confirmation includes effort name"""
        from oi.efforts import generate_effort_opening_confirmation  # ImportError = red
        
        # Mock LLM to return predictable response
        with patch('oi.efforts.chat') as mock_chat:
            mock_chat.return_value = "Opening effort: auth-bug"
            
            response = generate_effort_opening_confirmation("auth-bug")
            
            mock_chat.assert_called_once()
            # Verify response contains effort name
            assert "auth-bug" in response
    
    def test_ambient_message_not_saved_to_effort_log(self, tmp_path):
        """Messages not during open effort go to ambient, not effort log"""
        from oi.routing import save_message_appropriately  # ImportError = red
        
        session_dir = tmp_path / "session"
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir(parents=True)
        
        # Create empty effort file
        effort_file = efforts_dir / "auth-bug.jsonl"
        effort_file.touch()
        
        # Create ambient log
        ambient_file = session_dir / "raw.jsonl"
        ambient_file.touch()
        
        # Message that doesn't open effort (no detection)
        with patch('oi.routing.detect_effort_opening') as mock_detect:
            mock_detect.return_value = None
            
            message = {"role": "user", "content": "How's it going?"}
            save_message_appropriately(session_dir, message, current_effort=None)
            
            # Should be in ambient, not effort
            ambient_lines = ambient_file.read_text().strip().split('\n')
            assert len(ambient_lines) == 1
            
            effort_lines = effort_file.read_text().strip().split('\n')
            assert len(effort_lines) == 0  # Empty