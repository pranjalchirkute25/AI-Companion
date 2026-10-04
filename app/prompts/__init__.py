"""
System prompts and prompt generation templates for The Blind Spot.
"""

from app.prompts.system_prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
    REGENERATION_SAFETY_INSTRUCTION,
)
from app.prompts.templates import (
    build_analysis_prompt,
    build_followup_prompt,
)

__all__ = [
    "ANALYSIS_SYSTEM_PROMPT",
    "FOLLOWUP_SYSTEM_PROMPT",
    "REGENERATION_SAFETY_INSTRUCTION",
    "build_analysis_prompt",
    "build_followup_prompt",
]
