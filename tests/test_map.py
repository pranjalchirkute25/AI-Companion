"""
Tests for Reasoning Map generation and Markdown export endpoint (/api/reasoning-map).
"""

from fastapi.testclient import TestClient

from app.services.session_service import get_session_service


class TestReasoningMapEndpoint:
    """Tests 'My Reasoning Map' generation strictly built from user's own confirmed inputs."""

    def test_generate_reasoning_map_with_all_sections(self, client: TestClient):
        session_id = "test-session-map"
        session_service = get_session_service()
        session_service.create_or_update_session(
            session_id=session_id,
            intake_data={
                "decision_description": "Deciding between 6-month internship offer and university courses",
                "drawing_factors": "Stipend and resume brand",
            },
        )

        payload = {
            "session_id": session_id,
            "confirmed_assumptions": [
                "The employer will not accommodate flexible hours.",
                "I can maintain a high GPA with a 40-hour work week.",
            ],
            "acknowledged_conflicts": [
                "Tension between immediate financial earnings and senior capstone time.",
            ],
            "open_questions": [
                "Can I negotiate a 20-hour/week student arrangement?",
                "What is the financial compounding cost of delaying graduation?",
            ],
            "user_notes": "I plan to speak with my academic advisor before signing the contract.",
        }

        response = client.post("/api/reasoning-map", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["confirmed_assumptions_count"] == 2
        assert data["acknowledged_conflicts_count"] == 1
        assert data["open_questions_count"] == 2

        md_content = data["markdown_content"]

        # Assert all user items are present in markdown
        assert "# My Reasoning Map:" in md_content
        assert "Confirmed Unstated Assumptions" in md_content
        assert "The employer will not accommodate flexible hours." in md_content
        assert "Acknowledged Internal Conflicts & Tensions" in md_content
        assert "Tension between immediate financial earnings" in md_content
        assert "Open Probing Questions to Keep in Mind" in md_content
        assert "Can I negotiate a 20-hour/week student arrangement?" in md_content
        assert "Personal Reflection Notes" in md_content
        assert "I plan to speak with my academic advisor" in md_content

        # Non-negotiable rule check: ends with empty decision space
        assert "My decision: __________________________________________________" in md_content
        assert "(This line is intentionally left blank. The system never decides for you.)" in md_content

    def test_generate_reasoning_map_empty_selections(self, client: TestClient):
        payload = {
            "session_id": "session-empty-map",
            "confirmed_assumptions": [],
            "acknowledged_conflicts": [],
            "open_questions": [],
            "user_notes": None,
        }

        response = client.post("/api/reasoning-map", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["confirmed_assumptions_count"] == 0
        assert data["acknowledged_conflicts_count"] == 0
        assert data["open_questions_count"] == 0
        assert "My decision: __________________________________________________" in data["markdown_content"]
