"""
Unit tests for the Layer 2 Verdict and Advice Language Validator.
Proves the validator strictly flags all prescriptive and advisory phrases.
"""

import pytest

from app.validators.verdict_validator import (
    contains_verdict_language,
    generate_safe_neutral_analysis_fallback,
    generate_safe_neutral_followup_fallback,
    validate_analysis_payload,
    validate_followup_payload,
)


class TestVerdictValidator:
    """Proves the non-negotiable rule enforcement at validator layer."""

    @pytest.mark.parametrize(
        "forbidden_phrase",
        [
            "You should take the internship offer immediately.",
            "You shouldn't decline this opportunity.",
            "I recommend opting for the higher stipend.",
            "My recommendation is to delay graduation.",
            "My advice to you is to stay in school.",
            "I advise you to speak to the manager.",
            "I strongly suggest that you decline.",
            "The best option for you is obvious.",
            "The best choice is to accept.",
            "The better option is clear.",
            "The right decision is before you.",
            "The correct decision depends on this.",
            "The optimal choice would be option A.",
            "The superior option provides more money.",
            "Go with the fintech company.",
            "Choose the full-time role.",
            "Pick the internship over coursework.",
            "Opt for the academic semester.",
            "You'd be better off taking the stipend.",
            "You are better off graduating on time.",
            "You must prioritize your career.",
            "You need to take this offer.",
            "You have to choose one.",
            "You ought to reflect on this.",
            "Definitely take the position.",
        ],
    )
    def test_catches_all_forbidden_verdict_phrases(self, forbidden_phrase: str):
        has_violation, matched = contains_verdict_language(forbidden_phrase)
        assert has_violation is True, f"Validator failed to catch forbidden phrase: '{forbidden_phrase}'"
        assert len(matched) > 0

    @pytest.mark.parametrize(
        "clean_socratic_phrase",
        [
            "What criteria are most important to your long-term career goals?",
            "How might balancing 40 hours with 4 courses affect your energy levels?",
            "Examining this assumption could clarify your baseline priorities.",
            "A potential tension exists between immediate stipend gains and senior capstone time.",
            "What would happen if you explored a flexible or part-time schedule?",
            "The alternative perspective emphasizes the compounding value of graduating on schedule.",
        ],
    )
    def test_allows_neutral_socratic_phrases(self, clean_socratic_phrase: str):
        has_violation, matched = contains_verdict_language(clean_socratic_phrase)
        assert has_violation is False, f"Validator incorrectly flagged clean Socratic phrase: '{clean_socratic_phrase}' (matched: {matched})"
        assert len(matched) == 0

    def test_validate_nested_payload_with_verdict(self, mock_gemini_verdict_analysis_dict):
        has_violation, violations = validate_analysis_payload(mock_gemini_verdict_analysis_dict)
        assert has_violation is True
        assert len(violations) >= 3

    def test_validate_clean_nested_payload(self, mock_gemini_clean_analysis_dict):
        has_violation, violations = validate_analysis_payload(mock_gemini_clean_analysis_dict)
        assert has_violation is False
        assert len(violations) == 0

    def test_safe_neutral_analysis_fallback_is_verdict_free(self):
        fallback = generate_safe_neutral_analysis_fallback(
            decision_description="Deciding between internship and college courses",
            drawing_factors="High stipend and brand prestige",
            session_id="session-fallback-test",
        )
        has_violation, violations = validate_analysis_payload(fallback)
        assert has_violation is False
        assert len(violations) == 0
        assert fallback.overlooked_factors == []
        assert fallback.unstated_assumptions == []
        assert "could not be generated" in fallback.disclaimer
        assert len(fallback.probing_questions) >= 5

    def test_safe_neutral_followup_fallback_is_verdict_free(self):
        fallback = generate_safe_neutral_followup_fallback(
            session_id="session-fallback-followup",
            user_answer="I care deeply about finishing my senior capstone project on time.",
            reflection_step=2,
        )
        has_violation, violations = validate_followup_payload(fallback)
        assert has_violation is False
        assert len(violations) == 0
        assert len(fallback.deeper_questions) >= 1
