"""
Request validation schemas for The Blind Spot API.
"""


from pydantic import BaseModel, Field, field_validator


class IntakeRequest(BaseModel):
    """
    Intake form payload for analyzing a decision.
    All text fields are validated for length and content.
    """
    decision_description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Describe the decision and all the details you have.",
    )
    drawing_factors: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="What is drawing you toward it or what feels most salient?",
    )
    options_considered: str | None = Field(
        default=None,
        max_length=2000,
        description="Options currently being considered (optional).",
    )
    deadline_or_stakes: str | None = Field(
        default=None,
        max_length=1000,
        description="Timeline, deadline, or stakes involved (optional).",
    )
    session_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional client-provided or existing session ID.",
    )

    @field_validator("decision_description", "drawing_factors")
    @classmethod
    def validate_non_empty_stripped(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 3:
            raise ValueError("Input cannot be blank or only whitespace.")
        return stripped

    @field_validator("options_considered", "deadline_or_stakes")
    @classmethod
    def validate_optional_text(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class FollowupRequest(BaseModel):
    """
    Payload for Socratic question reflection follow-up.
    """
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Active session ID for contextual thread tracking.",
    )
    question: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The probing or Socratic question being answered.",
    )
    user_answer: str = Field(
        ...,
        min_length=2,
        max_length=3000,
        description="The user's direct reflection or answer to the question.",
    )

    @field_validator("session_id", "question", "user_answer")
    @classmethod
    def validate_stripped(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or solely whitespace.")
        return stripped


class ReasoningMapRequest(BaseModel):
    """
    Payload for generating 'My Reasoning Map' summary.
    Constructed ONLY from the user's confirmed acknowledgments.
    """
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Active session ID.",
    )
    confirmed_assumptions: list[str] = Field(
        default_factory=list,
        description="List of unstated assumptions confirmed or recognized by user.",
    )
    acknowledged_conflicts: list[str] = Field(
        default_factory=list,
        description="List of internal reasoning conflicts acknowledged by user.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="List of probing questions remaining open for exploration.",
    )
    user_notes: str | None = Field(
        default=None,
        max_length=3000,
        description="Optional additional reflection notes typed directly by the user.",
    )
