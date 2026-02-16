"""Unit tests for salience decay logic."""

import pytest

from helpers import setup_concluded_effort
from oi.decay import (
    extract_keywords, is_referenced, check_decay, DECAY_THRESHOLD,
    update_summary_references, get_evicted_summary_ids,
    SUMMARY_EVICTION_THRESHOLD,
)
from oi.state import (
    _load_expanded, _load_expanded_state, _save_expanded,
    _load_session_state, _save_session_state,
    _load_summary_references,
)
from oi.tools import expand_effort


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


# === Keyword extraction ===

class TestExtractKeywords:
    def test_basic(self):
        keywords = extract_keywords("Fixed 401 errors: refresh tokens never auto-called. Added axios interceptor.")
        assert "fixed" in keywords
        assert "401" in keywords
        assert "refresh" in keywords
        assert "tokens" in keywords
        assert "interceptor" in keywords
        assert "axios" in keywords
        # Stopwords excluded
        assert "the" not in keywords

    def test_empty(self):
        assert extract_keywords("") == set()
        assert extract_keywords(None) == set()

    def test_filters_short_words(self):
        keywords = extract_keywords("I am ok to go do it")
        # All words are <=2 chars or stopwords
        assert len(keywords) == 0

    def test_strips_punctuation(self):
        keywords = extract_keywords("(auth-bug) fixed! errors, tokens.")
        assert "auth-bug" in keywords
        assert "fixed" in keywords
        assert "errors" in keywords
        assert "tokens" in keywords


# === Reference detection ===

class TestIsReferenced:
    def test_by_effort_id(self):
        assert is_referenced("What about auth-bug?", "auth-bug", set()) is True

    def test_by_effort_id_space_separated(self):
        assert is_referenced("Tell me about the auth bug details", "auth-bug", set()) is True

    def test_by_keywords(self):
        keywords = {"refresh", "tokens", "interceptor", "401", "axios"}
        assert is_referenced("The refresh tokens are expiring", "auth-bug", keywords) is True

    def test_single_keyword_not_enough(self):
        keywords = {"refresh", "tokens", "interceptor", "401", "axios"}
        assert is_referenced("The refresh rate is fine", "auth-bug", keywords) is False

    def test_not_referenced(self):
        keywords = {"refresh", "tokens", "interceptor", "401", "axios"}
        assert is_referenced("How's the weather today?", "auth-bug", keywords) is False

    def test_case_insensitive(self):
        assert is_referenced("WHAT ABOUT AUTH-BUG?", "auth-bug", set()) is True

    def test_keyword_match_case_insensitive(self):
        keywords = {"refresh", "tokens"}
        assert is_referenced("The REFRESH TOKENS need fixing", "auth-bug", keywords) is True


# === Decay check ===

class TestCheckDecay:
    def test_collapses_after_threshold(self, session_dir):
        """Effort auto-collapses after DECAY_THRESHOLD turns without reference."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        # Expand it at turn 1
        _save_session_state(session_dir, {"turn_count": 1})
        expand_effort(session_dir, "auth-bug")
        assert "auth-bug" in _load_expanded(session_dir)

        # Simulate turns without reference
        # Turn 2, 3: no reference, not yet at threshold
        for turn in range(2, 2 + DECAY_THRESHOLD - 1):
            decayed = check_decay(session_dir, turn, "unrelated weather chat", "It's sunny today!")
            assert decayed == []
            assert "auth-bug" in _load_expanded(session_dir)

        # Turn at threshold: should decay
        decay_turn = 1 + DECAY_THRESHOLD
        decayed = check_decay(session_dir, decay_turn, "unrelated topic again", "Sure thing!")
        assert "auth-bug" in decayed
        assert "auth-bug" not in _load_expanded(session_dir)

    def test_reference_resets_counter(self, session_dir):
        """Referencing an effort resets the decay counter."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        _save_session_state(session_dir, {"turn_count": 1})
        expand_effort(session_dir, "auth-bug")

        # Turn 2-3: no reference
        check_decay(session_dir, 2, "unrelated", "unrelated")
        check_decay(session_dir, 3, "unrelated", "unrelated")

        # Turn 4: reference by mentioning auth-bug
        decayed = check_decay(session_dir, 4, "What about auth-bug details?", "Here they are.")
        assert decayed == []
        assert "auth-bug" in _load_expanded(session_dir)

        # Verify last_referenced_turn was updated
        state = _load_expanded_state(session_dir)
        assert state["last_referenced_turn"]["auth-bug"] == 4

        # Now 3 more turns without reference from turn 4
        check_decay(session_dir, 5, "unrelated", "unrelated")
        check_decay(session_dir, 6, "unrelated", "unrelated")
        decayed = check_decay(session_dir, 7, "unrelated", "unrelated")
        assert "auth-bug" in decayed

    def test_multiple_efforts_independent(self, session_dir):
        """Each expanded effort decays independently."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        setup_concluded_effort(
            session_dir, "perf-fix",
            "Fixed N+1 query in dashboard. Batched with JOIN."
        )

        _save_session_state(session_dir, {"turn_count": 1})
        expand_effort(session_dir, "auth-bug")
        expand_effort(session_dir, "perf-fix")

        # Turn 2: reference only perf-fix
        decayed = check_decay(session_dir, 2, "The dashboard query is faster now", "Great, the JOIN fixed it.")
        assert decayed == []

        # Turn 3-4: reference neither
        check_decay(session_dir, 3, "unrelated", "unrelated")
        decayed = check_decay(session_dir, 4, "unrelated", "unrelated")
        # auth-bug should decay (last referenced at turn 1, now turn 4 = 3 turns)
        assert "auth-bug" in decayed
        # perf-fix should NOT decay (last referenced at turn 2, now turn 4 = 2 turns)
        assert "perf-fix" not in decayed
        assert "perf-fix" in _load_expanded(session_dir)

        # Turn 5: perf-fix decays now (turn 5 - turn 2 = 3)
        decayed = check_decay(session_dir, 5, "unrelated", "unrelated")
        assert "perf-fix" in decayed
        assert _load_expanded(session_dir) == set()

    def test_does_not_affect_open_efforts(self, session_dir):
        """Only expanded (concluded) efforts can decay. Open efforts are unaffected."""
        from oi.tools import open_effort as tool_open_effort
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )

        # Open effort exists alongside expanded concluded
        tool_open_effort(session_dir, "active-work")

        _save_session_state(session_dir, {"turn_count": 1})
        expand_effort(session_dir, "auth-bug")

        # Run turns without reference, stopping just before threshold
        for turn in range(2, 1 + DECAY_THRESHOLD):
            check_decay(session_dir, turn, "unrelated", "unrelated")

        # This turn triggers decay
        decayed = check_decay(session_dir, 1 + DECAY_THRESHOLD, "unrelated", "unrelated")
        assert "auth-bug" in decayed

        # Open effort should be unaffected
        from oi.tools import get_all_open_efforts
        open_efforts = get_all_open_efforts(session_dir)
        assert any(e["id"] == "active-work" for e in open_efforts)

    def test_no_expanded_returns_empty(self, session_dir):
        """No expanded efforts means nothing to check."""
        session_dir.mkdir(parents=True, exist_ok=True)
        decayed = check_decay(session_dir, 5, "hello", "hi")
        assert decayed == []

    def test_assistant_response_counts_as_reference(self, session_dir):
        """Reference in assistant response (not just user message) prevents decay."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        _save_session_state(session_dir, {"turn_count": 1})
        expand_effort(session_dir, "auth-bug")

        # Turn 2-3: no reference
        check_decay(session_dir, 2, "unrelated", "unrelated")
        check_decay(session_dir, 3, "unrelated", "unrelated")

        # Turn 4: assistant mentions it (not user)
        decayed = check_decay(
            session_dir, 4,
            "Tell me about recent work",
            "We fixed the refresh tokens and 401 errors in auth-bug."
        )
        assert decayed == []
        assert "auth-bug" in _load_expanded(session_dir)


# === Summary eviction ===

class TestSummaryEviction:
    def test_update_summary_references_tracks_referenced_effort(self, session_dir):
        """Referenced concluded efforts get their turn tracked."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        update_summary_references(session_dir, 5, "What about auth-bug?", "Here's the info.")
        refs = _load_summary_references(session_dir)
        assert refs["auth-bug"] == 5

    def test_update_summary_references_ignores_unreferenced(self, session_dir):
        """Unreferenced efforts still get initialized (grace period) but at current turn."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        update_summary_references(session_dir, 5, "How's the weather?", "It's sunny!")
        refs = _load_summary_references(session_dir)
        # Grace period: initialized to current turn even without reference
        assert refs["auth-bug"] == 5

    def test_get_evicted_returns_old_efforts(self, session_dir):
        """Efforts not referenced for SUMMARY_EVICTION_THRESHOLD turns are evicted."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        # Initialize reference at turn 1
        update_summary_references(session_dir, 1, "auth-bug is done", "Great.")

        # Check at turn 1 + threshold
        evicted = get_evicted_summary_ids(session_dir, 1 + SUMMARY_EVICTION_THRESHOLD)
        assert "auth-bug" in evicted

    def test_get_evicted_excludes_recently_referenced(self, session_dir):
        """Recently referenced efforts are not evicted."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        # Reference at turn 10
        update_summary_references(session_dir, 10, "What about auth-bug?", "Here's info.")

        # Check at turn 15 — not yet at threshold
        evicted = get_evicted_summary_ids(session_dir, 15)
        assert "auth-bug" not in evicted

    def test_get_evicted_grace_period_for_untracked(self, session_dir):
        """Efforts with no entry in summary_last_referenced_turn are NOT evicted."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        # Don't call update_summary_references — no entry exists
        evicted = get_evicted_summary_ids(session_dir, 100)
        assert "auth-bug" not in evicted

    def test_eviction_threshold_boundary(self, session_dir):
        """Exactly at threshold = evicted."""
        setup_concluded_effort(
            session_dir, "auth-bug",
            "Fixed 401 errors: refresh tokens never auto-called."
        )
        update_summary_references(session_dir, 10, "auth-bug done", "Yep.")

        # Exactly at threshold: turn 30, last_ref=10, diff=20=threshold
        evicted = get_evicted_summary_ids(session_dir, 10 + SUMMARY_EVICTION_THRESHOLD)
        assert "auth-bug" in evicted

        # One turn before threshold: diff=19 < 20
        evicted = get_evicted_summary_ids(session_dir, 10 + SUMMARY_EVICTION_THRESHOLD - 1)
        assert "auth-bug" not in evicted
