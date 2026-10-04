"""
Verdict and Advice Language Validator (Layer 2 of Non-Negotiable Rule).
Scans all generated model outputs for directive, advisory, and verdict-rendering phrases.
"""

import re
from typing import Any

from app.schemas.response_schemas import (
    BlindSpotAnalysisResponse,
    FollowupResponse,
)

# Regex patterns matching prescriptive or verdict language
FORBIDDEN_VERDICT_PATTERNS = [
    r"\byou\s+should\b",
    r"\byou\s+shouldn'?t\b",
    r"\byou\s+ought\s+to\b",
    r"\byou\s+must\b",
    r"\byou\s+need\s+to\b",
    r"\byou\s+have\s+to\b",
    r"\bi\s+recommend\b",
    r"\bmy\s+recommendation\b",
    r"\bmy\s+advice\b",
    r"\bi\s+advise\b",
    r"\bi\s+strongly\s+suggest\b",
    r"\bthe\s+best\s+option\b",
    r"\bthe\s+best\s+choice\b",
    r"\bthe\s+better\s+option\b",
    r"\bthe\s+better\s+choice\b",
    r"\bthe\s+right\s+decision\b",
    r"\bthe\s+correct\s+decision\b",
    r"\bthe\s+optimal\s+choice\b",
    r"\bthe\s+superior\s+option\b",
    r"\bgo\s+with\b",
    r"\bchoose\s+the\b",
    r"\bpick\s+the\b",
    r"\bopt\s+for\b",
    r"\byou'd\s+be\s+better\s+off\b",
    r"\byou\s+are\s+better\s+off\b",
    r"\bdefinitely\s+take\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_VERDICT_PATTERNS]


def contains_verdict_language(text: str) -> tuple[bool, list[str]]:
    """
    Checks if the provided text contains any forbidden verdict or recommendation phrases.
    Returns (has_violation, list_of_matched_phrases).
    """
    if not text or not isinstance(text, str):
        return False, []

    matches = []
    for pattern in COMPILED_PATTERNS:
        found = pattern.findall(text)
        if found:
            matches.extend(found)

    return len(matches) > 0, matches


def _extract_all_strings(data: Any) -> list[str]:
    """Recursively extracts all strings from a nested structure (dict, list, object)."""
    strings: list[str] = []
    if isinstance(data, str):
        strings.append(data)
    elif isinstance(data, dict):
        for val in data.values():
            strings.extend(_extract_all_strings(val))
    elif isinstance(data, (list, tuple, set)):
        for item in data:
            strings.extend(_extract_all_strings(item))
    elif hasattr(data, "model_dump"):
        strings.extend(_extract_all_strings(data.model_dump()))
    elif hasattr(data, "__dict__"):
        strings.extend(_extract_all_strings(data.__dict__))
    return strings


def validate_analysis_payload(payload: Any) -> tuple[bool, list[str]]:
    """
    Scans an entire analysis response payload for any verdict language.
    """
    all_texts = _extract_all_strings(payload)
    violations: list[str] = []

    for text in all_texts:
        has_verdict, matches = contains_verdict_language(text)
        if has_verdict:
            violations.extend(matches)

    return len(violations) > 0, violations


def validate_followup_payload(payload: Any) -> tuple[bool, list[str]]:
    """
    Scans a follow-up response payload for any verdict language.
    """
    return validate_analysis_payload(payload)


def generate_safe_neutral_analysis_fallback(
    decision_description: str,
    drawing_factors: str,
    session_id: str,
    options_considered: str | None = None,
) -> BlindSpotAnalysisResponse:
    """
    Safe fallback response if model output fails secondary safety verification.
    Guaranteed to be 100% neutral and free of verdict language.
    """
    return BlindSpotAnalysisResponse(
        session_id=session_id,
        what_you_emphasized=[drawing_factors.strip()[:100]] if drawing_factors.strip() else [],
        # A service failure is not evidence that these particular blind spots
        # exist. Keep inferred fields empty and let the interface say analysis
        # is unavailable instead of presenting generic speculation as tailored.
        overlooked_factors=[],
        unstated_assumptions=[],
        internal_conflicts=[],
        other_perspective="A tailored counter-case is unavailable while the analysis service is offline.",
        probing_questions=[
            "What critical information, if discovered next week, would completely invert your current thinking?",
            "If neither option were available, what third path would you construct from scratch?",
            "What assumption are you most hesitant to test or discuss with a mentor?",
            "How does this choice align with your priorities 24 months from now?",
            "What would a neutral observer say is the biggest risk you are currently downplaying?",
        ],
        disclaimer=(
            "A tailored analysis could not be generated right now. No assumptions or blind spots are being attributed "
            "to your situation. You can still use the questions below to reflect; try again later for a tailored analysis."
        ),
    )


def generate_safe_neutral_followup_fallback(
    session_id: str,
    user_answer: str,
    reflection_step: int = 1,
) -> FollowupResponse:
    """
    Safe fallback for follow-up reflection if model output fails verification.
    """
    return FollowupResponse(
        session_id=session_id,
        user_answer_summary=f"You wrote: {user_answer[:120]}",
        deeper_questions=[
            "What remains uncertain in that line of reasoning?",
            "What evidence would challenge this perspective?",
            "How would your evaluation change if the timeline were doubled?",
        ],
        newly_exposed_blind_spots=[],
        reflection_step=reflection_step,
    )
