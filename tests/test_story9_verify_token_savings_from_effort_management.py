"""Tests for Story 9: Verify Token Savings from Effort Management"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStory9VerifyTokenSavings:
    """Story 9: Verify Token Savings from Effort Management"""

    def test_measure_context_size_with_open_effort(self, tmp_path):
        """AC1: After working on an effort for several turns, the context size is measured"""
        # Arrange
        from oi.tokens import measure_context_size  # NEW function - ImportError = red
        
        # Create session directory structure
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Ambient chat
        ambient_log = session_dir / "raw.jsonl"
        ambient_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"role": "assistant", "content": "Good! Ready to help."})
        ]))
        
        # Open effort log
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}),
            json.dumps({"role": "user", "content": "Access token is 1 hour"}),
            json.dumps({"role": "assistant", "content": "The 1-hour TTL matches"}),
            json.dumps({"role": "user", "content": "Here's the code"}),
            json.dumps({"role": "assistant", "content": "That's the problem"}),
            json.dumps({"role": "user", "content": "Oh that makes sense"}),
            json.dumps({"role": "assistant", "content": "Exactly."})
        ]))
        
        # Manifest with open effort
        manifest = session_dir / "manifest.yaml"
        manifest.write_text("""
efforts:
  - id: auth-bug
    status: open
""")
        
        # Mock token counting for each component
        mock_counts = {
            str(ambient_log): 40,  # ambient chat tokens
            str(effort_log): 600,  # effort raw tokens
            str(manifest): 10,    # manifest overhead tokens
        }
        
        def mock_count_tokens(text, model):
            # Simple mock: count based on known values
            if "ambient" in text:  # This would be the actual tokenizer logic
                return 40
            elif "effort" in text:
                return 600
            elif "manifest" in text:
                return 10
            return len(text.split()) // 0.75  # rough estimate
        
        # Act
        with patch('oi.tokens.count_tokens', side_effect=mock_count_tokens) as mock_count:
            context_size = measure_context_size(session_dir, "gpt-4")  # SUT called
        
        # Assert
        assert context_size == 650  # 40 + 10 + 600
        mock_count.assert_called()  # Verify token counting was used

    def test_measure_context_size_after_concluding_effort(self, tmp_path):
        """AC2: After concluding that effort, the context size is measured again"""
        # Arrange
        from oi.tokens import measure_context_size  # NEW function - ImportError = red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Ambient chat (unchanged)
        ambient_log = session_dir / "raw.jsonl"
        ambient_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Hey, how's it going?"}),
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}),
            json.dumps({"role": "user", "content": "Quick question - weather?"}),
            json.dumps({"role": "assistant", "content": "72°F and sunny"})
        ]))
        
        # Effort log exists but not in context
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}),
            # ... many more messages
            json.dumps({"role": "user", "content": "Back to auth - I implemented it"}),
            json.dumps({"role": "assistant", "content": "Concluding effort: auth-bug"})
        ]))
        
        # Manifest with concluded effort (summary replaces raw)
        manifest = session_dir / "manifest.yaml"
        manifest.write_text("""
efforts:
  - id: auth-bug
    status: concluded
    summary: Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh.
""")
        
        # Mock token counting
        def mock_count_tokens(text, model):
            if "concluded" in text or "summary" in text:
                return 60  # summary tokens
            if "ambient" in text:
                return 80  # ambient grew with interruption
            if "manifest" in text:
                return 60  # manifest with summary
            return 0
        
        # Act
        with patch('oi.tokens.count_tokens', side_effect=mock_count_tokens):
            context_size = measure_context_size(session_dir, "gpt-4")  # SUT called
        
        # Assert
        assert context_size == 140  # 80 + 60 (ambient + manifest summary)

    def test_token_savings_calculation_shows_80_percent_reduction(self, tmp_path):
        """AC3: The token count shows a significant reduction (e.g., 80%+ savings for that effort)"""
        # Arrange
        from oi.tokens import calculate_effort_savings  # NEW function - ImportError = red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Mock token counts to match scenario
        with patch('oi.tokens.count_tokens') as mock_count:
            mock_count.side_effect = [
                600,  # raw effort tokens (8 messages)
                60,   # summary tokens
            ]
            
            # Create effort log and summary for calculation
            efforts_dir = session_dir / "efforts"
            efforts_dir.mkdir()
            effort_log = efforts_dir / "auth-bug.jsonl"
            effort_log.write_text("raw messages")  # Content doesn't matter, mock handles it
            
            manifest = session_dir / "manifest.yaml"
            manifest.write_text("""
efforts:
  - id: auth-bug
    status: concluded
    summary: Debugged 401 errors after 1 hour.
            """)
            
            # Act
            savings = calculate_effort_savings("auth-bug", session_dir, "gpt-4")  # SUT called
        
        # Assert
        assert savings >= 80.0  # (600-60)/600 = 90% savings
        assert mock_count.call_count == 2  # Called for raw and summary

    def test_summary_substantially_smaller_than_raw_effort_log(self, tmp_path):
        """AC4: The summary in the manifest is substantially smaller than the raw effort log it replaces"""
        # Arrange
        from oi.tokens import compare_effort_to_summary  # NEW function - ImportError = red
        
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create effort log with many messages
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        
        # Simulate many turns (10 user + 10 assistant messages)
        messages = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            content = f"Message {i} with detailed technical content about auth bug and token refresh and axios interceptors"
            messages.append(json.dumps({"role": role, "content": content}))
        
        effort_log.write_text('\n'.join(messages))
        
        # Create manifest with concise summary
        manifest = session_dir / "manifest.yaml"
        manifest.write_text("""
efforts:
  - id: auth-bug
    status: concluded
    summary: "Fixed 401 errors by adding axios interceptor for token refresh."
""")
        
        # Mock token counting
        with patch('oi.tokens.count_tokens') as mock_count:
            # Raw effort has many tokens, summary has few
            mock_count.side_effect = [1000, 20]  # raw=1000, summary=20
            
            # Act
            ratio = compare_effort_to_summary("auth-bug", session_dir, "gpt-4")  # SUT called
            
        # Assert
        assert ratio >= 5.0  # summary is at least 5x smaller (1000/20 = 50x)
        assert mock_count.call_count == 2  # Raw effort and summary counted