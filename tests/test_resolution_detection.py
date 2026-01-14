"""Tests for resolution detection (Stories 5, 6, 12)."""

import pytest
from oi.detection import ResolutionDetector


class TestResolutionDetector:
    """Tests for ResolutionDetector class interface."""

    @pytest.fixture
    def detector(self):
        """Create a ResolutionDetector instance."""
        return ResolutionDetector()


class TestAcceptancePhrases:
    """Story 3: Test detection of acceptance phrases that trigger resolution."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_detects_thanks(self, detector):
        assert detector.is_resolution("Thanks!") is True

    def test_detects_makes_sense(self, detector):
        assert detector.is_resolution("That makes sense") is True

    def test_detects_got_it(self, detector):
        assert detector.is_resolution("Got it") is True

    def test_detects_youre_right(self, detector):
        assert detector.is_resolution("You're right") is True

    def test_detects_that_fixed_it(self, detector):
        assert detector.is_resolution("That fixed it") is True

    def test_detects_perfect_thanks(self, detector):
        assert detector.is_resolution("Perfect, thanks") is True

    def test_detects_ah_makes_sense(self, detector):
        assert detector.is_resolution("Ah, that makes sense") is True


class TestDisagreementPhrases:
    """Story 5: Test detection of disagreement phrases that keep effort open."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_detects_no_thats_not_it(self, detector):
        assert detector.is_disagreement("No, that's not it") is True

    def test_detects_i_dont_think_so(self, detector):
        assert detector.is_disagreement("I don't think so") is True

    def test_detects_but_what_about(self, detector):
        assert detector.is_disagreement("But what about...") is True

    def test_detects_that_doesnt_work(self, detector):
        assert detector.is_disagreement("That doesn't work") is True

    def test_detects_i_already_tried_that(self, detector):
        assert detector.is_disagreement("I already tried that") is True

    def test_detects_not_quite(self, detector):
        assert detector.is_disagreement("Not quite") is True

    def test_detects_are_you_sure(self, detector):
        assert detector.is_disagreement("Are you sure?") is True


class TestDisagreementDoesNotTriggerResolution:
    """Story 5: Verify disagreement prevents artifact extraction."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_disagreement_is_not_resolution(self, detector):
        """Disagreement phrases should return False for is_resolution."""
        message = "No, that's not right"
        assert detector.is_disagreement(message) is True
        assert detector.is_resolution(message) is False

    def test_pushback_is_not_resolution(self, detector):
        message = "But what about the edge cases?"
        assert detector.is_disagreement(message) is True
        assert detector.is_resolution(message) is False


class TestConfidenceScores:
    """Test confidence scoring for resolution/disagreement detection."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_confidence_returns_float_between_0_and_1(self, detector):
        confidence = detector.confidence("Thanks!")
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_clear_acceptance_has_high_confidence(self, detector):
        """Clear acceptance phrases should have confidence > 0.8."""
        assert detector.confidence("Thanks!") > 0.8
        assert detector.confidence("That makes sense") > 0.8
        assert detector.confidence("Got it") > 0.8

    def test_clear_disagreement_has_high_confidence(self, detector):
        """Clear disagreement phrases should have confidence > 0.8."""
        assert detector.confidence("No, that's not it") > 0.8
        assert detector.confidence("I don't think so") > 0.8

    def test_ambiguous_message_has_lower_confidence(self, detector):
        """Ambiguous messages should have confidence < 0.7."""
        assert detector.confidence("ok") < 0.7
        assert detector.confidence("hmm") < 0.7


class TestTopicChangeDetection:
    """Story 12: Test detection of topic changes that trigger resolution."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_unrelated_question_after_answer_triggers_resolution(self, detector):
        """Asking a completely new question should trigger resolution of previous topic."""
        previous_context = "AI just explained how to debug auth bug"
        new_message = "How do I optimize database queries?"

        assert detector.is_topic_change(new_message, previous_context) is True

    def test_related_followup_is_not_topic_change(self, detector):
        """Related follow-up questions should not trigger topic change."""
        previous_context = "AI just explained how to debug auth bug"
        new_message = "What if the token is valid but permissions are wrong?"

        assert detector.is_topic_change(new_message, previous_context) is False

    def test_topic_change_counts_as_resolution(self, detector):
        """Topic change should be treated as implicit resolution."""
        previous_context = "AI explained database optimization"
        new_message = "How do I deploy to AWS?"

        # Topic change implies resolution of previous topic
        assert detector.is_topic_change(new_message, previous_context) is True
        # This should count as resolution for the previous effort
        assert detector.is_implicit_resolution(new_message, previous_context) is True


class TestMultiTurnDisagreement:
    """Story 6: Test multiple disagreements followed by final acceptance."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_multiple_disagreements_then_acceptance(self, detector):
        """Multiple disagreements in a row, then final acceptance."""
        messages = [
            "No, that's not it",
            "Still not working",
            "I don't think that's right",
            "Thanks! That fixed it"
        ]

        # First three should be disagreements
        assert detector.is_disagreement(messages[0]) is True
        assert detector.is_disagreement(messages[1]) is True
        assert detector.is_disagreement(messages[2]) is True

        # Final message should be resolution
        assert detector.is_resolution(messages[3]) is True
        assert detector.is_disagreement(messages[3]) is False

    def test_alternating_disagreement_and_clarification(self, detector):
        """Back and forth with disagreements and clarifying questions."""
        disagreement = "That doesn't work though"
        clarification = "What about this other approach?"
        acceptance = "Got it, thanks"

        assert detector.is_disagreement(disagreement) is True
        # Clarifying question might be neutral or slight disagreement
        # but should not trigger resolution
        assert detector.is_resolution(clarification) is False
        # Final acceptance triggers resolution
        assert detector.is_resolution(acceptance) is True


class TestEdgeCases:
    """Edge cases and ambiguous inputs."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_ambiguous_ok(self, detector):
        """Test handling of ambiguous 'ok'."""
        # "ok" could be acceptance or just acknowledgment
        # Confidence should be low
        confidence = detector.confidence("ok")
        assert confidence < 0.7

    def test_question_within_acceptance(self, detector):
        """Acceptance with a follow-up question."""
        message = "Thanks! But one more thing..."

        # Should detect the acceptance part
        assert detector.is_resolution(message) is True
        # But might have moderate confidence due to "but"
        confidence = detector.confidence(message)
        assert 0.5 <= confidence <= 0.9

    def test_sarcastic_thanks(self, detector):
        """Sarcastic thanks detection (difficult case)."""
        message = "Oh great, thanks for nothing"

        # This is hard to detect without tone, but "for nothing" suggests sarcasm
        # Should NOT be detected as resolution
        assert detector.is_resolution(message) is False

    def test_empty_message(self, detector):
        """Empty or whitespace-only messages."""
        assert detector.is_resolution("") is False
        assert detector.is_resolution("   ") is False
        assert detector.is_disagreement("") is False

    def test_case_insensitive_detection(self, detector):
        """Detection should be case-insensitive."""
        assert detector.is_resolution("THANKS!") is True
        assert detector.is_resolution("thanks!") is True
        assert detector.is_disagreement("NO, THAT'S WRONG") is True
        assert detector.is_disagreement("no, that's wrong") is True


class TestContextAwareDetection:
    """Test detection with conversation context."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_resolution_with_context(self, detector):
        """Detection can use conversation context for better accuracy."""
        context = {
            "last_ai_message": "Try clearing your cache and restarting.",
            "topic": "debugging auth bug"
        }

        user_message = "That worked!"

        # Should detect resolution even with context
        assert detector.is_resolution(user_message, context=context) is True

    def test_disagreement_with_context(self, detector):
        """Context helps disambiguate borderline cases."""
        context = {
            "last_ai_message": "The issue is likely your API key.",
            "topic": "API authentication"
        }

        user_message = "But I already checked that"

        assert detector.is_disagreement(user_message, context=context) is True


class TestResolutionTypes:
    """Test different types of resolution detection."""

    @pytest.fixture
    def detector(self):
        return ResolutionDetector()

    def test_explicit_acceptance(self, detector):
        """Explicit acceptance like 'thanks', 'got it'."""
        assert detector.is_explicit_resolution("Thanks!") is True
        assert detector.is_explicit_resolution("Got it") is True

    def test_implicit_acceptance(self, detector):
        """Implicit acceptance like topic change."""
        previous_context = "Discussed database indexing"
        new_message = "How do I set up CI/CD?"

        assert detector.is_implicit_resolution(new_message, previous_context) is True

    def test_no_resolution(self, detector):
        """Messages that are neither explicit nor implicit resolution."""
        assert detector.is_explicit_resolution("What about X?") is False
        assert detector.is_implicit_resolution("Can you clarify?", "same topic") is False
