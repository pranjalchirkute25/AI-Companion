"""
Unit tests for Pydantic request and response schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.request_schemas import (
    FollowupRequest,
    IntakeRequest,
    ReasoningMapRequest,
)
from app.schemas.response_schemas import (
    BlindSpotAnalysisResponse,
    FollowupResponse,
    HealthResponse,
    InternalConflict,
    OverlookedFactor,
    UnstatedAssumption,
)


class TestRequestSchemas:
    """Tests input validation schemas."""

    def test_valid_intake_request(self, internship_example_payload):
        req = IntakeRequest(**internship_example_payload)
        assert req.decision_description == internship_example_payload["decision_description"]
        assert req.drawing_factors == internship_example_payload["drawing_factors"]
        assert req.options_considered == internship_example_payload["options_considered"]
        assert req.deadline_or_stakes == internship_example_payload["deadline_or_stakes"]

    def test_intake_request_strip_whitespace(self):
        req = IntakeRequest(
            decision_description="   This is a valid decision description text.   ",
            drawing_factors="   High stipend and proximity   ",
            options_considered="   Option A vs Option B   ",
        )
        assert req.decision_description == "This is a valid decision description text."
        assert req.drawing_factors == "High stipend and proximity"
        assert req.options_considered == "Option A vs Option B"

    def test_intake_request_too_short(self):
        with pytest.raises(ValidationError):
            IntakeRequest(
                decision_description="Too short",
                drawing_factors="Stipend",
            )

    def test_intake_request_blank_raises_error(self):
        with pytest.raises(ValidationError):
            IntakeRequest(
                decision_description="                ",
                drawing_factors="                ",
            )

    def test_intake_request_oversized_text(self):
        with pytest.raises(ValidationError):
            IntakeRequest(
                decision_description="a" * 5001,
                drawing_factors="drawing",
            )

    def test_valid_followup_request(self):
        req = FollowupRequest(
            session_id="session-123",
            question="What is the biggest risk?",
            user_answer="The biggest risk is failing my capstone project.",
        )
        assert req.session_id == "session-123"
        assert "capstone" in req.user_answer

    def test_followup_request_blank_validation(self):
        with pytest.raises(ValidationError):
            FollowupRequest(
                session_id="",
                question="Valid question here?",
                user_answer="Valid answer",
            )

    def test_reasoning_map_request_defaults(self):
        req = ReasoningMapRequest(session_id="session-456")
        assert req.session_id == "session-456"
        assert req.confirmed_assumptions == []
        assert req.acknowledged_conflicts == []
        assert req.open_questions == []
        assert req.user_notes is None


class TestResponseSchemas:
    """Tests response model construction and integrity."""

    def test_blind_spot_analysis_response_model(self, mock_gemini_clean_analysis_dict):
        resp = BlindSpotAnalysisResponse(**mock_gemini_clean_analysis_dict)
        assert resp.session_id == "test-session-123"
        assert len(resp.what_you_emphasized) == 3
        assert len(resp.overlooked_factors) == 3
        assert len(resp.unstated_assumptions) == 2
        assert len(resp.internal_conflicts) == 1
        assert len(resp.probing_questions) == 5
        assert isinstance(resp.overlooked_factors[0], OverlookedFactor)
        assert isinstance(resp.unstated_assumptions[0], UnstatedAssumption)
        assert isinstance(resp.internal_conflicts[0], InternalConflict)

    def test_followup_response_model(self, mock_gemini_followup_dict):
        resp = FollowupResponse(**mock_gemini_followup_dict)
        assert resp.session_id == "test-session-123"
        assert len(resp.deeper_questions) == 2
        assert len(resp.newly_exposed_blind_spots) == 1

    def test_health_response_model(self):
        health = HealthResponse(
            status="ok",
            app_name="The Blind Spot",
            version="1.0.0",
            model="gemini-2.5-flash",
            gemini_configured=True,
        )
        assert health.status == "ok"
        assert health.gemini_configured is True
