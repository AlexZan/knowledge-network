"""Tests for Story 9: Token Savings Measurement"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestStory9VerifyTokenSavings:
    """Story 9: Verify Token Savings from Effort Management"""

    def test_context_size_measured_for_open_effort(self, tmp_path):
        """After working on an effort for several turns, the context size is measured"""
        from oi.context import build_turn_context
        from oi.tokens import count_tokens

        # Arrange: Create session with open effort containing multiple messages
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create ambient log with some messages
        ambient_log = session_dir / "raw.jsonl"
        ambient_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )
        
        # Create effort log with many messages (simulating work)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        
        # Write 10 messages to effort log (simulating extended discussion)
        effort_content = ""
        for i in range(10):
            effort_content += json.dumps({"role": "user" if i % 2 == 0 else "assistant", 
                                         "content": f"Message {i} about auth bug"}) + "\n"
        effort_log.write_text(effort_content)
        
        # Create state with open effort
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug investigation", status="open")
        ])
        
        # Act: Build context and measure tokens
        context = build_turn_context(state, session_dir)
        context_tokens = count_tokens(context, "gpt-4")
        
        # Assert: Context size is measured (non-zero)
        assert context_tokens > 0
        # Should include both ambient and effort content
        assert "Hey, how's it going?" in context
        assert "Message 0 about auth bug" in context

    def test_context_size_measured_after_effort_concluded(self, tmp_path):
        """After concluding that effort, the context size is measured again"""
        from oi.context import build_turn_context
        from oi.tokens import count_tokens

        # Arrange: Create session with concluded effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        
        # Create ambient log
        ambient_log = session_dir / "raw.jsonl"
        ambient_log.write_text(
            json.dumps({"role": "user", "content": "Hey, how's it going?"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Good! Ready to help."}) + "\n"
        )
        
        # Create concluded effort log (preserved but not in context)
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text(
            json.dumps({"role": "user", "content": "Let's debug auth bug"}) + "\n" +
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug"}) + "\n"
        )
        
        # Create manifest with concluded effort summary
        import yaml
        manifest = {
            "efforts": [{
                "id": "auth-bug",
                "status": "concluded",
                "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor.",
                "raw_file": "efforts/auth-bug.jsonl"
            }]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Create state with concluded effort
        from oi.models import ConversationState, Artifact
        state = ConversationState(artifacts=[
            Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug investigation", status="resolved")
        ])
        
        # Act: Build context and measure tokens
        context = build_turn_context(state, session_dir)
        context_tokens = count_tokens(context, "gpt-4")
        
        # Assert: Context size is measured (non-zero)
        assert context_tokens > 0
        # Should include summary but not raw effort messages
        assert "Debugged 401 errors" in context
        assert "Let's debug auth bug" not in context  # Raw messages not in context

    def test_token_savings_calculated_for_concluded_effort(self, tmp_path):
        """The token count shows a significant reduction (e.g., 80%+ savings for that effort)"""
        from oi.tokens import calculate_effort_savings

        # Arrange: Create session with effort that has many raw tokens
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # Create effort log with many tokens (simulated by repeating content)
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_content = ""
        # Write 100 messages with substantial content
        for i in range(100):
            effort_content += json.dumps({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"This is message {i} discussing the authentication bug where users get 401 errors after about an hour. We need to investigate the token expiration logic and refresh mechanism."
            }) + "\n"
        effort_log.write_text(effort_content)
        
        # Create manifest with concise summary
        import yaml
        manifest = {
            "efforts": [{
                "id": "auth-bug",
                "status": "concluded",
                "summary": "Fixed 401 errors by adding axios interceptor for token refresh.",
                "raw_file": "efforts/auth-bug.jsonl"
            }]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Act: Calculate savings percentage
        savings = calculate_effort_savings("auth-bug", session_dir, model="gpt-4")
        
        # Assert: Significant token savings achieved
        assert savings >= 80.0  # At least 80% savings

    def test_summary_much_smaller_than_raw_effort_log(self, tmp_path):
        """The summary in the manifest is substantially smaller than the raw effort log it replaces"""
        from oi.tokens import count_tokens, compare_effort_to_summary

        # Arrange: Create session with effort having many raw tokens
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        
        # Create effort log with many tokens
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_content = ""
        # Write 50 detailed messages
        for i in range(50):
            effort_content += json.dumps({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Detailed technical discussion about authentication issue {i}: examining token validation, refresh mechanisms, API endpoints, and error handling strategies for production deployment."
            }) + "\n"
        effort_log.write_text(effort_content)
        
        # Create manifest with concise summary
        import yaml
        summary = "Fixed auth bug with token refresh interceptor."
        manifest = {
            "efforts": [{
                "id": "auth-bug",
                "status": "concluded",
                "summary": summary,
                "raw_file": "efforts/auth-bug.jsonl"
            }]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        
        # Act: Compare raw tokens to summary tokens
        ratio = compare_effort_to_summary("auth-bug", session_dir, model="gpt-4")
        
        # Assert: Raw log has many more tokens than summary
        assert ratio > 10.0  # Raw log at least 10x larger than summary
        
        # Also verify directly with count_tokens
        raw_tokens = count_tokens(effort_log.read_text(), "gpt-4")
        summary_tokens = count_tokens(summary, "gpt-4")
        assert raw_tokens > summary_tokens * 10  # 10x compression