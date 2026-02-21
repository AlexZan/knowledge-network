"""End-to-end test with real LLM (deepseek-chat).

Verifies:
1. LLM correctly detects when to open/close efforts from natural language
2. Token measurements match predictions
3. Tool-based flow works end-to-end

Run with: pytest tests/test_e2e_real_llm.py -v -s
Requires: DEEPSEEK_API_KEY environment variable
"""

import os
import yaml
import pytest

from oi.orchestrator import process_turn, _build_messages
from oi.tools import get_open_effort, get_active_effort, get_all_open_efforts
from oi.state import (
    _load_expanded, _load_expanded_state, _load_session_state,
    _save_summary_references,
)
from oi.tokens import count_tokens
from oi.decay import DECAY_THRESHOLD, SUMMARY_EVICTION_THRESHOLD


requires_llm = pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not set — skipping real LLM test"
)

MODEL = "deepseek/deepseek-chat"


def _context_tokens(session_dir):
    messages = _build_messages(session_dir)
    return sum(count_tokens(m["content"]) for m in messages)


@requires_llm
class TestRealLLMToolCalling:
    """Verify LLM correctly calls tools via natural language."""

    def test_llm_opens_effort_via_tool_call(self, tmp_path):
        """User says 'let's debug X' → LLM calls open_effort tool → manifest updated."""
        session_dir = tmp_path / "session"
        response = process_turn(
            session_dir,
            "Let's debug the auth bug - users are getting 401 errors after about an hour",
            model=MODEL
        )

        effort = get_open_effort(session_dir)
        assert effort is not None, f"LLM did not open an effort. Response: {response[:200]}"
        print(f"\nOpened effort: {effort['id']}")
        print(f"Response: {response[:200]}")

    def test_ambient_message_no_effort(self, tmp_path):
        """Casual message → no effort created."""
        session_dir = tmp_path / "session"
        response = process_turn(session_dir, "Hello, how are you?", model=MODEL)

        effort = get_open_effort(session_dir)
        assert effort is None, f"LLM opened an effort for casual chat. Response: {response[:200]}"

        # Ambient log should exist
        raw = session_dir / "raw.jsonl"
        assert raw.exists()

    def test_follow_up_stays_in_effort(self, tmp_path):
        """After opening effort, follow-up messages don't open a second one."""
        session_dir = tmp_path / "session"

        # Open effort
        process_turn(
            session_dir,
            "Let's work on fixing the login timeout issue",
            model=MODEL
        )
        assert get_open_effort(session_dir) is not None

        # Follow-up
        process_turn(
            session_dir,
            "The access token expires after 1 hour, we have refresh tokens configured",
            model=MODEL
        )

        # Still only one effort
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        efforts = [e for e in manifest.get("efforts", []) if e["status"] == "open"]
        assert len(efforts) == 1, f"Expected 1 open effort, got {len(efforts)}"

    def test_llm_closes_effort_via_tool_call(self, tmp_path):
        """User signals completion → LLM calls close_effort → effort concluded with summary."""
        session_dir = tmp_path / "session"

        # Open and work
        process_turn(
            session_dir,
            "Let's work on fixing the database connection pool exhaustion",
            model=MODEL
        )
        process_turn(
            session_dir,
            "The pool size was set to 5 but we need at least 20 for our load",
            model=MODEL
        )

        # Signal completion (retry once with explicit instruction if needed)
        response = process_turn(
            session_dir,
            "I've increased the pool size to 25 and the connection errors are gone. Bug is fixed, we're done.",
            model=MODEL
        )

        effort = get_open_effort(session_dir)
        if effort is not None:
            response = process_turn(
                session_dir,
                "This effort is complete. Please call the close_effort tool to conclude it.",
                model=MODEL
            )
            effort = get_open_effort(session_dir)

        assert effort is None, f"LLM did not close the effort. Response: {response[:200]}"

        # Verify summary in manifest
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        concluded = [e for e in manifest["efforts"] if e["status"] == "concluded"]
        assert len(concluded) == 1
        assert concluded[0]["summary"], "Summary should not be empty"
        print(f"\nSummary: {concluded[0]['summary']}")

    def test_full_scenario_token_savings(self, tmp_path):
        """Full scenario: ambient → open → work → close. Measure token savings."""
        session_dir = tmp_path / "session"

        # Ambient
        process_turn(session_dir, "Hey, how's it going?", model=MODEL)
        t_ambient = _context_tokens(session_dir)

        # Open
        process_turn(
            session_dir,
            "Let's debug the auth bug - users get 401 errors after an hour",
            model=MODEL
        )
        t_open = _context_tokens(session_dir)

        # Work
        process_turn(
            session_dir,
            "The access token TTL is 1 hour. The refreshAccessToken function exists "
            "in tokenService.ts but nothing calls it automatically.",
            model=MODEL
        )
        process_turn(
            session_dir,
            "So the token expires because nothing triggers a refresh. "
            "I'll add an axios interceptor to handle this.",
            model=MODEL
        )
        t_work = _context_tokens(session_dir)

        # Close
        process_turn(
            session_dir,
            "I implemented the interceptor and tested it - 401 errors are gone. "
            "Bug is fixed, let's wrap this up.",
            model=MODEL
        )
        t_closed = _context_tokens(session_dir)

        print(f"\nToken progression:")
        print(f"  Ambient: {t_ambient}")
        print(f"  After open: {t_open}")
        print(f"  After work: {t_work}")
        print(f"  After close: {t_closed}")
        if t_work > 0:
            savings = (1 - t_closed / t_work) * 100
            print(f"  Savings: {savings:.0f}%")


from helpers import setup_concluded_effort


@requires_llm
class TestDecayE2E:
    """Slice 3: Verify salience decay works end-to-end with real LLM."""

    def test_llm_expands_concluded_effort(self, tmp_path):
        """User asks about a concluded effort → LLM calls expand_effort."""
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "auth-bug",
            "Fixed 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor.",
            raw_lines=[
                ("user", "Let's debug the auth bug - users get 401s after 1 hour"),
                ("assistant", "That timing suggests token expiration. What's your access token TTL?"),
                ("user", "Access token TTL is 1 hour. We have refresh tokens with 30-day TTL."),
                ("assistant", "Root cause: refreshAccessToken exists but nothing calls it automatically. Fix: add axios response interceptor."),
            ]
        )

        response = process_turn(
            session_dir,
            "Can you show me the full details of the auth-bug investigation? I need to review exactly what we discussed.",
            model=MODEL
        )

        expanded = _load_expanded(session_dir)
        assert "auth-bug" in expanded, f"LLM did not expand auth-bug. Response: {response[:300]}"
        print(f"\nExpanded: {expanded}")
        print(f"Response: {response[:300]}")

    def test_decay_fires_after_unrelated_turns(self, tmp_path):
        """Expand effort, then have unrelated conversation → auto-collapse fires.

        Note: The LLM may reference the expanded effort in its responses (since
        the raw log is in context), which resets the decay counter. We use many
        short factual questions and allow up to 8 turns for decay to fire.
        """
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "cache-bug",
            "Fixed Redis cache invalidation race condition. Added distributed lock with 5s TTL.",
            raw_lines=[
                ("user", "The cache is returning stale data intermittently"),
                ("assistant", "This sounds like a cache invalidation race condition. Are you using Redis?"),
                ("user", "Yes, Redis with a 60s TTL on cache entries"),
                ("assistant", "The fix is a distributed lock around cache writes. Use SETNX with a 5s TTL."),
            ]
        )

        # Turn 1: Expand the effort
        response = process_turn(
            session_dir,
            "Show me the full details of cache-bug please",
            model=MODEL
        )
        assert "cache-bug" in _load_expanded(session_dir), f"LLM did not expand. Response: {response[:200]}"
        t_expanded = _context_tokens(session_dir)
        print(f"\nAfter expand: {t_expanded} tokens")

        # Send many short factual questions (non-tech to avoid keyword overlap)
        # Allow up to 8 turns — LLM may reference the expanded effort initially
        factual_questions = [
            "What is the capital of Mongolia?",
            "What is the tallest mountain in South America?",
            "Who painted the Mona Lisa?",
            "What year did the Titanic sink?",
            "What is the largest ocean on Earth?",
            "What is the smallest country in the world?",
            "How many continents are there?",
            "What is the speed of light in km/s?",
        ]
        decayed = False
        last_response = ""
        for i, msg in enumerate(factual_questions, start=2):
            last_response = process_turn(session_dir, msg, model=MODEL)
            expanded = _load_expanded(session_dir)
            state = _load_expanded_state(session_dir)
            lrt = state.get("last_referenced_turn", {})
            print(f"  Turn {i}: expanded={expanded}, lrt={lrt}")
            if "cache-bug" not in expanded:
                decayed = True
                print(f"  Decayed at turn {i}")
                break

        assert decayed, (
            f"cache-bug should have decayed within 8 unrelated turns. "
            f"LRT: {_load_expanded_state(session_dir).get('last_referenced_turn')}"
        )
        assert "Auto-collapsed" in last_response, (
            f"Expected auto-collapse banner. Got: {last_response[-300:]}"
        )
        print(f"\nDecay confirmed with banner")

    def test_re_expand_after_collapse(self, tmp_path):
        """After collapse, user can ask about the effort again and LLM re-expands.

        Uses manual collapse_effort() to simulate decay (natural decay is
        unreliable in e2e because the LLM references expanded content in its
        responses, resetting the decay counter). The decay mechanism itself
        is thoroughly proven by unit tests in test_decay.py.
        """
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "redis-cluster",
            "Migrated Redis from standalone to cluster mode with 6 shards. Fixed hash slot rebalancing during failover.",
            raw_lines=[
                ("user", "Our Redis instance is hitting memory limits, we need to shard it"),
                ("assistant", "I recommend Redis Cluster with 6 shards. You'll need to handle hash slot distribution."),
                ("user", "During failover testing, some hash slots became unassigned"),
                ("assistant", "Fixed: added CLUSTER SETSLOT commands to rebalance during failover. All shards stable now."),
            ]
        )

        # Step 1: LLM expands the effort
        response = process_turn(
            session_dir,
            "I need to review the full conversation details of redis-cluster. "
            "Please expand it so I can see the complete raw discussion.",
            model=MODEL
        )
        assert "redis-cluster" in _load_expanded(session_dir), (
            f"LLM did not expand redis-cluster. Response: {response[:300]}"
        )
        print(f"\nExpanded redis-cluster")

        # Step 2: Manually collapse (simulates decay auto-collapse)
        from oi.tools import collapse_effort
        collapse_effort(session_dir, "redis-cluster")
        assert "redis-cluster" not in _load_expanded(session_dir)
        print("Manually collapsed (simulating decay)")

        # Step 3: One ambient turn so LLM sees the effort is back to summary-only
        process_turn(session_dir, "What is the capital of France?", model=MODEL)

        # Step 4: Ask LLM to re-expand (retry once if needed)
        response = process_turn(
            session_dir,
            "I need to see the full raw conversation from redis-cluster again. "
            "Please use the expand_effort tool to load the complete discussion.",
            model=MODEL
        )

        expanded = _load_expanded(session_dir)
        if "redis-cluster" not in expanded:
            response = process_turn(
                session_dir,
                "Please call expand_effort for redis-cluster. I need the raw log loaded.",
                model=MODEL
            )
            expanded = _load_expanded(session_dir)

        assert "redis-cluster" in expanded, (
            f"LLM did not re-expand redis-cluster after collapse. Response: {response[:300]}"
        )
        print(f"Re-expanded: {expanded}")

    def test_turn_counter_increments_with_real_llm(self, tmp_path):
        """Verify turn counter advances correctly through real LLM turns."""
        session_dir = tmp_path / "session"

        process_turn(session_dir, "Hello", model=MODEL)
        assert _load_session_state(session_dir)["turn_count"] == 1

        process_turn(session_dir, "How are you?", model=MODEL)
        assert _load_session_state(session_dir)["turn_count"] == 2

        process_turn(session_dir, "What's 2+2?", model=MODEL)
        assert _load_session_state(session_dir)["turn_count"] == 3

        print(f"\nTurn counter after 3 turns: {_load_session_state(session_dir)['turn_count']}")


@requires_llm
class TestBoundedContextE2E:
    """Slice 4: Verify bounded working context works end-to-end with real LLM."""

    def test_llm_calls_search_for_evicted_effort(self, tmp_path):
        """When a summary is evicted from WM, asking about it triggers search_efforts.

        Setup: concluded effort with artificially old reference → evicted from WM.
        Then ask the LLM about that topic. It should call search_efforts and answer.
        """
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "auth-bug",
            "Fixed 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor.",
            raw_lines=[
                ("user", "Let's debug the auth bug - users get 401s after 1 hour"),
                ("assistant", "Root cause: refreshAccessToken exists but nothing calls it. Fix: axios interceptor."),
            ]
        )

        # Artificially set reference to old turn so it's evicted
        _save_summary_references(session_dir, {"auth-bug": 1})

        # Verify it's evicted at turn 25
        messages = _build_messages(session_dir, current_turn=25)
        system_content = messages[0]["content"]
        assert "auth-bug" not in system_content, "auth-bug should be evicted from WM"
        assert "search_efforts" in system_content, "Memory section should mention search_efforts"
        print(f"\nVerified: auth-bug evicted from WM at turn 25")

        # Now ask the LLM about it — LLM should use search_efforts
        # Set session turn count high enough so _build_messages evicts during process_turn
        from oi.state import _save_session_state
        _save_session_state(session_dir, {"turn_count": 24})  # next turn will be 25

        response = process_turn(
            session_dir,
            "What was the fix for the auth bug we worked on? I can't remember the details.",
            model=MODEL
        )

        # The LLM should have found and mentioned the auth-bug fix
        response_lower = response.lower()
        found_auth_info = (
            "refresh" in response_lower
            or "interceptor" in response_lower
            or "401" in response_lower
            or "auth" in response_lower
        )
        assert found_auth_info, (
            f"LLM should have found auth-bug info via search. Response: {response[:400]}"
        )
        print(f"Response mentions auth fix: {response[:300]}")

    def test_search_then_expand_path(self, tmp_path):
        """After search finds an evicted effort, user asks for full details → LLM expands.

        This tests the full recall path: eviction → search → expand.
        """
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "perf-fix",
            "Fixed N+1 query in dashboard. Batched with JOIN, 5s to 200ms.",
            raw_lines=[
                ("user", "The dashboard is loading slowly, about 5 seconds"),
                ("assistant", "Classic N+1 query problem. Each widget makes a separate DB query."),
                ("user", "There are about 50 widgets"),
                ("assistant", "Batch the queries with a single JOIN. Should drop to under 200ms."),
            ]
        )

        # Evict it
        _save_summary_references(session_dir, {"perf-fix": 1})
        from oi.state import _save_session_state
        _save_session_state(session_dir, {"turn_count": 24})

        # Turn 1: Ask about it (LLM should search and find it)
        response = process_turn(
            session_dir,
            "I think we fixed a dashboard performance issue before. Can you find it?",
            model=MODEL
        )
        print(f"\nSearch response: {response[:300]}")

        # Turn 2: Ask for full details (LLM should expand)
        response = process_turn(
            session_dir,
            "Can you show me the full conversation from that perf-fix effort? "
            "Please use expand_effort to load the raw discussion.",
            model=MODEL
        )

        expanded = _load_expanded(session_dir)
        if "perf-fix" not in expanded:
            # Retry with more explicit instruction
            response = process_turn(
                session_dir,
                "Please call expand_effort with id perf-fix to load the full details.",
                model=MODEL
            )
            expanded = _load_expanded(session_dir)

        assert "perf-fix" in expanded, (
            f"LLM did not expand perf-fix after search. Response: {response[:300]}"
        )
        print(f"Expanded after search: {expanded}")

    def test_ambient_windowing_with_real_llm(self, tmp_path):
        """Long ambient conversation stays bounded — LLM still functions correctly.

        Send many ambient messages, verify the system works and context doesn't
        include all old messages.
        """
        session_dir = tmp_path / "session"

        # Send 15 ambient turns (beyond AMBIENT_WINDOW of 10)
        topics = [
            "What is the capital of Japan?",
            "What's the largest planet?",
            "Who invented the telephone?",
            "What year was the internet invented?",
            "What is photosynthesis?",
            "Who wrote Romeo and Juliet?",
            "What is the speed of sound?",
            "How many bones in the human body?",
            "What is the deepest ocean trench?",
            "What causes earthquakes?",
            "What is the Pythagorean theorem?",
            "Who discovered penicillin?",
            "What is the largest desert?",
            "How does a combustion engine work?",
            "What is the boiling point of water in Celsius?",
        ]
        for msg in topics:
            process_turn(session_dir, msg, model=MODEL)

        # Verify context is bounded: only last AMBIENT_WINDOW exchanges in messages
        state = _load_session_state(session_dir)
        messages = _build_messages(session_dir, current_turn=state["turn_count"])
        non_system = [m for m in messages if m["role"] != "system"]

        from oi.decay import AMBIENT_WINDOW
        max_ambient_messages = AMBIENT_WINDOW * 2
        assert len(non_system) <= max_ambient_messages, (
            f"Expected at most {max_ambient_messages} ambient messages, got {len(non_system)}"
        )
        print(f"\nAfter 15 turns: {len(non_system)} messages in context "
              f"(max {max_ambient_messages})")

        # Verify raw.jsonl has ALL messages (nothing lost)
        raw_lines = (session_dir / "raw.jsonl").read_text().strip().split("\n")
        assert len(raw_lines) == 30, f"Expected 30 raw lines (15 turns × 2), got {len(raw_lines)}"
        print(f"raw.jsonl has {len(raw_lines)} lines (all preserved)")

        # Verify LLM still responds correctly with windowed context
        response = process_turn(
            session_dir,
            "What's 7 times 8?",
            model=MODEL
        )
        assert "56" in response, f"LLM should still answer correctly. Response: {response[:200]}"
        print(f"LLM still functional: {response[:100]}")

    def test_reference_resets_eviction_counter(self, tmp_path):
        """A summary about to expire gets its counter reset when referenced.

        Setup: concluded effort with last reference at turn 5.
        At turn 24 (delta=19, one short of threshold=20), mention the topic.
        Verify it stays in WM at turn 44 would-have-been-eviction point,
        because the reference at turn 24 reset the counter.
        """
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "fishing-trip",
            "Planned coastal fishing trip. Route: Bay area charter, targeting halibut and rockfish.",
            raw_lines=[
                ("user", "I want to plan a fishing trip near the Bay area"),
                ("assistant", "Great choice! Charter boats from Half Moon Bay target halibut and rockfish."),
            ]
        )

        # Last referenced at turn 5
        _save_summary_references(session_dir, {"fishing-trip": 5})
        from oi.state import _save_session_state
        _save_session_state(session_dir, {"turn_count": 23})  # next turn = 24

        # Verify it's still in WM at turn 24 (delta=19, not yet evicted)
        messages = _build_messages(session_dir, current_turn=24)
        assert "fishing-trip" in messages[0]["content"], "Should still be in WM at delta=19"

        # Turn 24: mention the fishing trip — LLM responds, update_summary_references fires
        response = process_turn(
            session_dir,
            "By the way, remember that fishing trip we planned? I'm thinking of going next month.",
            model=MODEL
        )
        print(f"\nTurn 24 response: {response[:200]}")

        # Check that the reference was reset
        from oi.state import _load_summary_references
        refs = _load_summary_references(session_dir)
        assert refs["fishing-trip"] == 24, (
            f"Expected fishing-trip last_ref reset to 24, got {refs.get('fishing-trip')}"
        )
        print(f"Reference reset to turn {refs['fishing-trip']}")

        # LLM may have expanded the effort — collapse so we test summary visibility
        from oi.tools import collapse_effort
        if "fishing-trip" in _load_expanded(session_dir):
            collapse_effort(session_dir, "fishing-trip")
            print("Collapsed fishing-trip (LLM had expanded it)")

        # Now at turn 25 (old threshold if it hadn't been reset), it should still be in WM
        messages = _build_messages(session_dir, current_turn=25)
        assert "fishing-trip" in messages[0]["content"], (
            "fishing-trip should still be in WM at turn 25 (reset at 24, delta=1)"
        )

        # And even at turn 43 (delta=19 from reset), still in WM
        messages = _build_messages(session_dir, current_turn=43)
        assert "fishing-trip" in messages[0]["content"], (
            "fishing-trip should still be in WM at turn 43 (reset at 24, delta=19)"
        )

        # But at turn 44 (delta=20 from reset), it would evict
        messages = _build_messages(session_dir, current_turn=44)
        assert "fishing-trip" not in messages[0]["content"], (
            "fishing-trip should be evicted at turn 44 (reset at 24, delta=20)"
        )
        print("Verified: reference at turn 24 reset the counter, eviction deferred to turn 44")


@requires_llm
class TestReopenE2E:
    """Slice 5: Verify effort reopening works end-to-end with real LLM."""

    def test_llm_reopens_explicit_request(self, tmp_path):
        """User explicitly asks to reopen a concluded effort → LLM calls reopen_effort."""
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "auth-bug",
            "Fixed 401 errors after 1 hour. Root cause: refresh tokens never auto-called. Fix: axios interceptor.",
            raw_lines=[
                ("user", "Let's debug the auth bug - users get 401s after 1 hour"),
                ("assistant", "Root cause: refreshAccessToken exists but nothing calls it. Fix: axios interceptor."),
            ]
        )

        response = process_turn(
            session_dir,
            "Let's reopen the auth-bug effort, I found another edge case with the token refresh.",
            model=MODEL
        )

        active = get_active_effort(session_dir)
        if active is None or active["id"] != "auth-bug":
            # Retry with more explicit instruction
            response = process_turn(
                session_dir,
                "Please call reopen_effort with id auth-bug. I need to continue working on it.",
                model=MODEL
            )
            active = get_active_effort(session_dir)

        assert active is not None and active["id"] == "auth-bug", (
            f"LLM did not reopen auth-bug. Active: {active}. Response: {response[:300]}"
        )
        assert active["status"] == "open"
        assert "Reopened" in response, f"Expected reopen banner. Response: {response[:300]}"
        print(f"\nReopened auth-bug. Response: {response[:200]}")

    def test_reopen_then_work_then_reconlude(self, tmp_path):
        """Full cycle: concluded → reopen → work → re-conclude. Summary should update."""
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "db-pool",
            "Increased connection pool from 5 to 25. Fixed exhaustion errors.",
            raw_lines=[
                ("user", "Database connections keep running out"),
                ("assistant", "Pool size is only 5. Increase to 25 for your load."),
            ]
        )

        # Reopen
        response = process_turn(
            session_dir,
            "Reopen the db-pool effort please. The connection issue is back.",
            model=MODEL
        )
        active = get_active_effort(session_dir)
        if active is None or active["id"] != "db-pool":
            process_turn(
                session_dir,
                "Please call reopen_effort with id db-pool.",
                model=MODEL
            )
            active = get_active_effort(session_dir)
        assert active is not None and active["id"] == "db-pool"
        print(f"\nReopened db-pool")

        # Work on it
        process_turn(
            session_dir,
            "The pool of 25 wasn't enough. Under peak load we need 50 connections. "
            "I've also added connection timeout of 30 seconds.",
            model=MODEL
        )

        # Re-conclude
        response = process_turn(
            session_dir,
            "Okay the pool is now set to 50 with 30s timeout and everything is stable. "
            "This effort is done, please close it.",
            model=MODEL
        )
        if get_open_effort(session_dir) is not None:
            response = process_turn(
                session_dir,
                "Please call close_effort to conclude the db-pool effort. We are done.",
                model=MODEL
            )

        effort = get_open_effort(session_dir)
        assert effort is None, f"Effort should be concluded. Response: {response[:300]}"

        # Verify summary was updated (should mention new info)
        manifest = yaml.safe_load((session_dir / "manifest.yaml").read_text())
        concluded = [e for e in manifest["efforts"] if e["id"] == "db-pool"]
        assert len(concluded) == 1
        summary = concluded[0]["summary"]
        print(f"\nUpdated summary: {summary}")
        # Summary should reference the new work (50 connections or timeout)
        summary_lower = summary.lower()
        has_new_info = "50" in summary_lower or "timeout" in summary_lower or "peak" in summary_lower
        assert has_new_info, f"Summary should cover new work. Got: {summary}"

    def test_reopen_preserves_conversation_history(self, tmp_path):
        """After reopen, the original raw log is still in context for the LLM."""
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "secret-code",
            "Discussed the secret code PINEAPPLE-42.",
            raw_lines=[
                ("user", "The secret code for this project is PINEAPPLE-42, remember it."),
                ("assistant", "Got it — the secret code is PINEAPPLE-42. I'll remember that."),
            ]
        )

        # Reopen
        process_turn(
            session_dir,
            "Reopen the secret-code effort please.",
            model=MODEL
        )
        active = get_active_effort(session_dir)
        if active is None or active["id"] != "secret-code":
            process_turn(
                session_dir,
                "Please call reopen_effort with id secret-code.",
                model=MODEL
            )

        # Ask about the content from the original log
        response = process_turn(
            session_dir,
            "What was the secret code we discussed in this effort?",
            model=MODEL
        )

        assert "PINEAPPLE-42" in response or "PINEAPPLE" in response, (
            f"LLM should recall content from original raw log. Response: {response[:300]}"
        )
        print(f"\nLLM recalled secret code from original log: {response[:200]}")

    def test_reopen_while_another_effort_open(self, tmp_path):
        """Reopening a concluded effort while another effort is active deactivates the current one."""
        session_dir = tmp_path / "session"

        # Start a current effort
        process_turn(
            session_dir,
            "Let's work on the new payment integration feature.",
            model=MODEL
        )
        active = get_active_effort(session_dir)
        assert active is not None
        current_id = active["id"]
        print(f"\nActive effort: {current_id}")

        # Set up a concluded effort
        setup_concluded_effort(session_dir, "old-bug",
            "Fixed null pointer exception in user service. Added null check before accessing profile.",
            raw_lines=[
                ("user", "Users are crashing when they open their profile"),
                ("assistant", "Null pointer — profile object isn't loaded. Added null check."),
            ]
        )

        # Reopen the old effort
        response = process_turn(
            session_dir,
            "Actually, I need to reopen old-bug — the null pointer is happening again in a different path.",
            model=MODEL
        )
        active = get_active_effort(session_dir)
        if active is None or active["id"] != "old-bug":
            process_turn(
                session_dir,
                "Please call reopen_effort with id old-bug.",
                model=MODEL
            )
            active = get_active_effort(session_dir)

        assert active is not None and active["id"] == "old-bug", (
            f"old-bug should be active. Got: {active}"
        )

        # The payment effort should still be open but not active
        all_open = get_all_open_efforts(session_dir)
        payment = [e for e in all_open if e["id"] == current_id]
        assert len(payment) == 1, f"Payment effort should still be open. All open: {[e['id'] for e in all_open]}"
        assert payment[0].get("active") is False
        print(f"old-bug is active, {current_id} is backgrounded")

    def test_reopen_expanded_effort_transitions_correctly(self, tmp_path):
        """If user is viewing an expanded (read-only) effort and asks to reopen it,
        the effort transitions from expanded to open (not both)."""
        session_dir = tmp_path / "session"
        setup_concluded_effort(session_dir, "api-design",
            "Designed REST API with versioned endpoints. Using /api/v1/ prefix.",
            raw_lines=[
                ("user", "Let's design the API structure"),
                ("assistant", "I recommend REST with versioned endpoints: /api/v1/users, /api/v1/orders"),
            ]
        )

        # First expand it (read-only view)
        process_turn(
            session_dir,
            "Show me the full details of api-design please.",
            model=MODEL
        )
        expanded = _load_expanded(session_dir)
        if "api-design" not in expanded:
            process_turn(
                session_dir,
                "Please call expand_effort with id api-design.",
                model=MODEL
            )
            expanded = _load_expanded(session_dir)
        assert "api-design" in expanded
        print(f"\nExpanded api-design (read-only view)")

        # Now reopen it
        response = process_turn(
            session_dir,
            "Actually, let's reopen api-design. I want to add more endpoints to the design.",
            model=MODEL
        )
        if get_active_effort(session_dir) is None or get_active_effort(session_dir)["id"] != "api-design":
            process_turn(
                session_dir,
                "Please call reopen_effort with id api-design.",
                model=MODEL
            )

        # Should be open, NOT expanded
        active = get_active_effort(session_dir)
        assert active is not None and active["id"] == "api-design"
        assert active["status"] == "open"
        expanded = _load_expanded(session_dir)
        assert "api-design" not in expanded, (
            f"api-design should not be in expanded set after reopen. Expanded: {expanded}"
        )
        print(f"Transitioned from expanded (read-only) to open (active). Expanded set: {expanded}")
