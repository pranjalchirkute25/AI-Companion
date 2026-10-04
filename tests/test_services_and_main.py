"""
Supplementary tests covering CacheService, SessionService,
GeminiService fallbacks, and FastAPI main handlers to maximize coverage (90%+).
"""

import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.schemas.request_schemas import IntakeRequest
from app.schemas.response_schemas import BlindSpotAnalysisResponse
from app.services.cache_service import CacheService
from app.services.gemini_service import GeminiService
from app.services.session_service import SessionService
from app.validators.security import escape_html_entities, sanitize_text_input


class TestCacheAndSessionServices:
    """Tests edge cases, evictions, and TTL in services."""

    def test_cache_service_expiration(self):
        cache = CacheService(default_ttl_seconds=1, max_entries=5)
        cache.set("short_lived", {"data": "test"}, ttl_seconds=1)
        assert cache.get("short_lived") == {"data": "test"}

        # Simulate expiration
        cache._cache["short_lived"] = (time.time() - 10, {"data": "expired"})
        assert cache.get("short_lived") is None

    def test_cache_service_capacity_eviction(self):
        cache = CacheService(default_ttl_seconds=300, max_entries=3)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        assert len(cache._cache) == 3

        # Adding 4th item triggers eviction
        cache.set("k4", "v4")
        assert len(cache._cache) <= 3
        assert cache.get("k4") == "v4"

    def test_session_service_expiration_and_cleanup(self):
        session_svc = SessionService(max_history=5, session_ttl_seconds=10)
        sid = session_svc.create_or_update_session(
            session_id="exp-session",
            intake_data={"decision_description": "test", "drawing_factors": "stipend"},
        )
        assert session_svc.get_session(sid) is not None

        # Expire session artificially
        session_svc._sessions[sid]["last_accessed"] = time.time() - 100
        assert session_svc.get_session(sid) is None

    def test_escape_html_entities_helper(self):
        raw = "<script>alert('hello & welcome')</script>"
        escaped = escape_html_entities(raw)
        assert "&lt;script&gt;" in escaped
        assert "&amp;" in escaped


class TestGeminiServiceInternals:
    """Tests GeminiService retry loops, client initialization, and timeouts."""

    @patch("google.genai.Client")
    def test_gemini_service_client_initialization(self, mock_client_cls):
        service = GeminiService(api_key="test_key", model_name="gemini-2.5-flash")
        client = service._get_client()
        assert client is not None

    def test_gemini_service_no_key_warning(self):
        service = GeminiService(api_key="")
        client = service._get_client()
        assert client is None

    def test_gemini_service_passes_response_schema_to_sdk(self):
        service = GeminiService(api_key="test_key", model_name="gemini-2.5-flash")
        client = MagicMock()

        service._sync_generate(
            client,
            system_instruction="system",
            prompt="prompt",
            response_schema=BlindSpotAnalysisResponse,
        )

        config = client.models.generate_content.call_args.kwargs["config"]
        assert config.response_schema is BlindSpotAnalysisResponse

    async def test_gemini_service_retry_and_timeout(self):
        service = GeminiService(api_key="test_key", model_name="gemini-2.5-flash")
        service._client = MagicMock()

        with patch.object(service, "_sync_generate", side_effect=Exception("API failure")):
            req = IntakeRequest(
                decision_description="Long enough decision description to pass validation",
                drawing_factors="Drawing factor",
            )
            # Should safely fallback without raising
            response = await service.analyze_decision(req, session_id="test-retry-session")
            assert response is not None
            assert response.overlooked_factors == []
            assert response.unstated_assumptions == []
            assert "could not be generated" in response.disclaimer


class TestMainEndpointsAndStatic:
    """Tests static file serving and index page."""

    def test_serve_index_page(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        assert "blind spot" in response.text
        assert "Decision canvas" in response.text

    def test_empty_input_sanitizer(self):
        assert sanitize_text_input("") == ""
        assert sanitize_text_input(None) == ""
