"""
Tests for the Socratic reflection loop endpoint (/api/followup)
and server-side session history management.
"""

import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.services.session_service import get_session_service
from app.validators.verdict_validator import validate_followup_payload


class TestFollowupEndpoint:
    """Tests reflection follow-up loop and session memory boundaries."""

    def test_followup_success(
        self,
        client: TestClient,
        mock_gemini_followup_dict,
    ):
        with patch(
            "app.services.gemini_service.GeminiService._call_gemini_with_retry",
            new_callable=AsyncMock,
        ) as mock_gemini_call:
            mock_gemini_call.return_value = json.dumps(mock_gemini_followup_dict)

            payload = {
                "session_id": "session-test-flow",
                "question": "What happens if the workload exceeds 40 hours?",
                "user_answer": "I would negotiate strict boundaries or request study leave during midterms.",
            }

            response = client.post("/api/followup", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert data["session_id"] == "session-test-flow"
            assert "deeper_questions" in data
            assert len(data["deeper_questions"]) >= 1
            assert "newly_exposed_blind_spots" in data

            has_verdict, violations = validate_followup_payload(data)
            assert has_verdict is False, f"Verdict found in follow-up: {violations}"

    def test_followup_session_size_cap_enforcement(
        self,
        client: TestClient,
        mock_gemini_followup_dict,
    ):
        """
        Submits 15 consecutive reflection steps to verify the server-side
        session history is capped at MAX_SESSION_HISTORY (10).
        """
        session_id = "session-cap-test"
        session_service = get_session_service()

        with patch(
            "app.services.gemini_service.GeminiService._call_gemini_with_retry",
            new_callable=AsyncMock,
        ) as mock_gemini_call:
            mock_gemini_call.return_value = json.dumps(mock_gemini_followup_dict)

            for i in range(15):
                payload = {
                    "session_id": session_id,
                    "question": f"Probing question {i}?",
                    "user_answer": f"User reflection answer {i}.",
                }
                res = client.post("/api/followup", json=payload)
                assert res.status_code == 200

            session = session_service.get_session(session_id)
            assert session is not None
            # Verify history length is capped at 10
            assert len(session["reflection_steps"]) <= 10
            # Verify the most recent step is present
            assert session["reflection_steps"][-1]["question"] == "Probing question 14?"

    def test_followup_gemini_failure_fallback(self, client: TestClient):
        with patch(
            "app.services.gemini_service.GeminiService._call_gemini_with_retry",
            new_callable=AsyncMock,
        ) as mock_gemini_call:
            mock_gemini_call.return_value = None  # Simulate Gemini failure

            payload = {
                "session_id": "session-fallback",
                "question": "What is the biggest risk?",
                "user_answer": "Balancing study time.",
            }

            response = client.post("/api/followup", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert len(data["deeper_questions"]) >= 1
            has_verdict, _ = validate_followup_payload(data)
            assert has_verdict is False
