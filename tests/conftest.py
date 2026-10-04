"""
Pytest configuration, fixtures, and mocked Gemini clients.
"""

from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app, reset_rate_limiter
from app.services.cache_service import get_cache_service
from app.services.session_service import get_session_service


@pytest.fixture(autouse=True)
def clean_services():
    """Cleans in-memory caches, sessions, and rate limits before each test."""
    reset_rate_limiter()
    cache = get_cache_service()
    cache.clear()
    session_service = get_session_service()
    session_service.clear()
    yield
    reset_rate_limiter()
    cache.clear()
    session_service.clear()


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for FastAPI."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def internship_example_payload():
    """Official student internship dilemma fixture."""
    return {
        "decision_description": (
            "I am a college student considering taking a 6-month software engineering internship offer. "
            "The internship pays a great stipend ($4,500/month), is only 15 minutes away from my home, "
            "and provides real industry experience with a known fintech company. However, it requires 40 hours "
            "per week during the upcoming spring academic semester when I have 4 core engineering courses and a "
            "final senior capstone project scheduled."
        ),
        "drawing_factors": (
            "The very good stipend to help pay tuition, the super convenient location close to home, "
            "and having a prestigious company brand name on my resume."
        ),
        "options_considered": (
            "Accept the full-time internship offer vs. Decline and stay full-time at university vs. Negotiate part-time hours (20 hrs/week)."
        ),
        "deadline_or_stakes": (
            "Offer acceptance deadline is in 5 days; if I accept full-time, I may risk delaying graduation by a semester."
        ),
    }


@pytest.fixture
def mock_gemini_clean_analysis_dict():
    """Clean structured JSON mock adhering strictly to non-verdict guidelines."""
    return {
        "session_id": "test-session-123",
        "what_you_emphasized": [
            "Competitive stipend ($4,500/month) to alleviate tuition expenses",
            "Convenient 15-minute commute proximity to home",
            "Resume brand value and industry exposure at a prominent fintech firm",
        ],
        "overlooked_factors": [
            {
                "factor": "Impact on academic GPA and senior capstone project deliverables",
                "why_it_matters": "Balancing 40 hours of workplace demands with 4 core courses could severely compress study time and capstone quality.",
            },
            {
                "factor": "Mentorship depth vs. transactional task allocation",
                "why_it_matters": "Brand prestige does not always correlate with dedicated engineering mentorship or meaningful code ownership.",
            },
            {
                "factor": "Long-term graduation delay financial and career compounding costs",
                "why_it_matters": "Delaying graduation by a semester postpones full-time salaried earnings and career progression by six months.",
            },
        ],
        "unstated_assumptions": [
            {
                "assumption": "The employer will be strictly rigid about the 40 hours/week requirement without room for flexible scheduling.",
                "how_to_test": "Inquire with the recruiter or hiring manager if they accommodate flexible hours, remote days, or a 20-30 hour adjusted student track.",
            },
            {
                "assumption": "Managing 4 heavy technical courses alongside full-time employment is sustainable without severe burnout.",
                "how_to_test": "Map out an hourly schedule of class attendance, study blocks, commute, and work hours to inspect buffer time.",
            },
        ],
        "internal_conflicts": [
            {
                "conflict_description": "Tension between advancing long-term academic milestones vs. capturing immediate financial and resume gains.",
                "user_quotes": [
                    "4 core engineering courses and a final senior capstone project scheduled",
                    "very good stipend to help pay tuition... prestigious company brand name",
                ],
            }
        ],
        "other_perspective": (
            "Focusing entirely on finishing your final academic semester and excelling in your capstone project could maximize "
            "your academic standing, prevent burnout, and allow you to pursue immediate full-time software engineering roles with higher compensation."
        ),
        "probing_questions": [
            "If accepting this internship resulted in a lower GPA or a delayed capstone, how would you evaluate the trade-off one year from now?",
            "What specific skills or mentorship experiences do you expect to gain that you cannot acquire during university projects?",
            "What would happen if you proposed a part-time arrangement of 20 hours per week?",
            "How does the immediate $4,500/month compare against the opportunity cost of entering the full-time job market one semester later?",
            "What would your professors and academic advisors observe if they saw your proposed weekly schedule?",
        ],
        "disclaimer": "The Blind Spot is a thinking aid and does not provide decisions or recommendations.",
    }


@pytest.fixture
def mock_gemini_verdict_analysis_dict():
    """Mock containing forbidden verdict language to trigger validator failure/regeneration."""
    return {
        "session_id": "test-session-verdict",
        "what_you_emphasized": ["High stipend", "Location"],
        "overlooked_factors": [
            {
                "factor": "Academics",
                "why_it_matters": "You should definitely accept the offer because money is important.",
            }
        ],
        "unstated_assumptions": [
            {
                "assumption": "Workload is manageable",
                "how_to_test": "I recommend you take the job and go with option A.",
            }
        ],
        "internal_conflicts": [
            {
                "conflict_description": "Academics vs internship",
                "user_quotes": ["capstone project", "high stipend"],
            }
        ],
        "other_perspective": "The best option is to stay in school.",
        "probing_questions": ["What will you do?"],
        "disclaimer": "Thinking aid only.",
    }


@pytest.fixture
def mock_gemini_followup_dict():
    """Clean mock response for follow-up question reflection."""
    return {
        "session_id": "test-session-123",
        "user_answer_summary": "You noted that graduation timeline is flexible if the real-world experience provides tangible production codebase access.",
        "deeper_questions": [
            "How will you verify whether the team assigns production feature development versus internal tooling maintenance?",
            "What milestone during the first month would confirm you made an intentional trade-off?",
        ],
        "newly_exposed_blind_spots": [
            "Assuming production access is guaranteed on day one without team placement confirmation.",
        ],
        "reflection_step": 1,
    }
