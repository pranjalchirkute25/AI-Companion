"""
Security validation utilities: sanitization, injection tag stripping, and length enforcement.
"""

import html
import re


def sanitize_text_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitizes user input string:
    - Strips leading/trailing whitespace
    - Limits string length
    - Neutralizes internal prompt framing delimiters
    - Strips control characters
    """
    if not text:
        return ""

    # Strip control characters (except newline, tab, carriage return)
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Neutralize potential system delimiter injections
    cleaned = cleaned.replace("<USER_DECISION_DATA>", "[USER_DATA_START]")
    cleaned = cleaned.replace("</USER_DECISION_DATA>", "[USER_DATA_END]")
    cleaned = cleaned.replace("<QUESTION_PROBED>", "[QUESTION_START]")
    cleaned = cleaned.replace("</QUESTION_PROBED>", "[QUESTION_END]")
    cleaned = cleaned.replace("<USER_RESPONSE_DATA>", "[RESPONSE_START]")
    cleaned = cleaned.replace("</USER_RESPONSE_DATA>", "[RESPONSE_END]")

    # Truncate to max length
    return cleaned[:max_length].strip()


def escape_html_entities(text: str) -> str:
    """Converts special HTML characters to safe HTML entities."""
    return html.escape(text, quote=True)
