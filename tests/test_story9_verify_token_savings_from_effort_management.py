"""Tests for Story 9: Verify Token Savings from Effort Management"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from oi.models import ConversationState, Artifact, TokenStats


class TestStory9VerifyTokenSavings:
    """Story 9: Verify Token Savings from Effort Management"""

    def test_token_count_of_current_context_can_be_measured(self, tmp_path):
        """The token count of the current context can be measured"""
        from oi.tokens import measure_context_size
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text('{"role": "user", "content": "hello"}\n')
        manifest = session_dir / "manifest.yaml"
        manifest.write_text(yaml.dump({"efforts": [{"id": "effort1", "status": "open"}]}))
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "effort1.jsonl"
        effort_log.write_text('{"role": "user", "content": "debug"}\n{"role": "assistant", "content": "help"}\n')
        state = ConversationState(artifacts=[Artifact(id="effort1", artifact_type="effort", summary="Debug", status="open")])
        token_count = measure_context_size(session_dir, state)
        assert isinstance(token_count, int)
        assert token_count > 0

    def test_after_concluding_effort_measured_token_count_is_lower_than_before(self, tmp_path):
        """After concluding an effort, the measured token count is lower than before"""
        from oi.tokens import measure_context_size
        from oi.storage import conclude_effort
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        raw_log = session_dir / "raw.jsonl"
        raw_log.write_text('{"role": "user", "content": "ambient"}\n')
        manifest = session_dir / "manifest.yaml"
        manifest.write_text(yaml.dump({"efforts": [{"id": "auth-bug", "status": "open"}]}))
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
            json.dumps({"role": "assistant", "content": "Exactly. The fix is"}),
        ]) + '\n')
        state_before = ConversationState(artifacts=[Artifact(id="auth-bug", artifact_type="effort", summary="Auth bug", status="open")])
        token_count_before = measure_context_size(session_dir, state_before)
        conclude_effort("auth-bug", session_dir, "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh.")
        state_after = ConversationState(artifacts=[Artifact(id="auth-bug", artifact_type="effort", summary="Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh.", status="resolved")])
        token_count_after = measure_context_size(session_dir, state_after)
        assert token_count_after < token_count_before

    def test_token_reduction_is_significant_80_percent_savings_for_that_effort(self, tmp_path):
        """The token reduction is significant (e.g., 80%+ savings for that effort)"""
        from oi.tokens import calculate_effort_savings
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug - users are getting 401s after about an hour"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug\n\nThat timing suggests token expiration. A few questions:\n1. What's your access token TTL?\n2. Are you using refresh tokens?"}),
            json.dumps({"role": "user", "content": "Access token is 1 hour, yes we have refresh tokens"}),
            json.dumps({"role": "assistant", "content": "The 1-hour TTL matches the failure timing. Let me see your refresh logic."}),
            json.dumps({"role": "user", "content": "Here's the code from tokenService.ts:\n[shows refresh function code]\nBut I don't see where it's called automatically"}),
            json.dumps({"role": "assistant", "content": "That's the problem - the refresh function exists but nothing calls it.\nYou need an axios interceptor. Here's the pattern:\n[shows interceptor code]"}),
            json.dumps({"role": "user", "content": "Oh that makes sense. So the token just expires because nothing refreshes it."}),
            json.dumps({"role": "assistant", "content": "Exactly. The fix is:\n- Root cause: refresh tokens never auto-called\n- Solution: axios interceptor that refreshes proactively"}),
            json.dumps({"role": "user", "content": "Back to auth - I implemented the interceptor and it works. Bug is fixed!"}),
            json.dumps({"role": "assistant", "content": "Concluding effort: auth-bug\n\nSummary: Debugged 401 errors occurring after 1 hour. Root cause was refresh\ntokens existing but never being called automatically. Fixed by adding axios\ninterceptor in tokenService.ts that proactively refreshes tokens before expiry.\n\nEffort concluded and summarized. Context freed up."}),
        ]) + '\n')
        manifest = session_dir / "manifest.yaml"
        manifest.write_text(yaml.dump({
            "efforts": [{
                "id": "auth-bug",
                "status": "concluded",
                "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh."
            }]
        }))
        with patch('oi.tokens.count_tokens') as mock_count:
            mock_count.side_effect = [700, 60]
            savings = calculate_effort_savings("auth-bug", session_dir, model="gpt-4")
            assert savings >= 80.0

    def test_summary_in_manifest_is_substantially_smaller_than_raw_effort_log_it_replaces(self, tmp_path):
        """The summary in the manifest is substantially smaller than the raw effort log it replaces"""
        from oi.tokens import compare_effort_to_summary
        session_dir = tmp_path / "session"
        session_dir.mkdir()
        efforts_dir = session_dir / "efforts"
        efforts_dir.mkdir()
        effort_log = efforts_dir / "auth-bug.jsonl"
        effort_log.write_text('\n'.join([
            json.dumps({"role": "user", "content": "Let's debug the auth bug - users are getting 401s after about an hour"}),
            json.dumps({"role": "assistant", "content": "Opening effort: auth-bug\n\nThat timing suggests token expiration. A few questions:\n1. What's your access token TTL?\n2. Are you using refresh tokens?"}),
            json.dumps({"role": "user", "content": "Access token is 1 hour, yes we have refresh tokens"}),
            json.dumps({"role": "assistant", "content": "The 1-hour TTL matches the failure timing. Let me see your refresh logic."}),
            json.dumps({"role": "user", "content": "Here's the code from tokenService.ts:\n[shows refresh function code]\nBut I don't see where it's called automatically"}),
            json.dumps({"role": "assistant", "content": "That's the problem - the refresh function exists but nothing calls it.\nYou need an axios interceptor. Here's the pattern:\n[shows interceptor code]"}),
            json.dumps({"role": "user", "content": "Oh that makes sense. So the token just expires because nothing refreshes it."}),
            json.dumps({"role": "assistant", "content": "Exactly. The fix is:\n- Root cause: refresh tokens never auto-called\n- Solution: axios interceptor that refreshes proactively"}),
            json.dumps({"role": "user", "content": "Back to auth - I implemented the interceptor and it works. Bug is fixed!"}),
            json.dumps({"role": "assistant", "content": "Concluding effort: auth-bug\n\nSummary: Debugged 401 errors occurring after 1 hour. Root cause was refresh\ntokens existing but never being called automatically. Fixed by adding axios\ninterceptor in tokenService.ts that proactively refreshes tokens before expiry.\n\nEffort concluded and summarized. Context freed up."}),
        ]) + '\n')
        manifest = session_dir / "manifest.yaml"
        manifest.write_text(yaml.dump({
            "efforts": [{
                "id": "auth-bug",
                "status": "concluded",
                "summary": "Debugged 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor for proactive refresh."
            }]
        }))
        with patch('oi.tokens.count_tokens') as mock_count:
            mock_count.side_effect = [700, 60]
            ratio = compare_effort_to_summary("auth-bug", session_dir, model="gpt-4")
            assert ratio > 5.0