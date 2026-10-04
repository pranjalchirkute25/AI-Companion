"""
Gemini API integration service implementing structured JSON generation,
asynchronous execution, exponential backoff retries, and multi-layer verdict validation.
"""

import asyncio
import json
import logging
from typing import Any

from app.config import get_settings
from app.prompts.system_prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
    REGENERATION_SAFETY_INSTRUCTION,
)
from app.prompts.templates import build_analysis_prompt, build_followup_prompt
from app.schemas.request_schemas import FollowupRequest, IntakeRequest
from app.schemas.response_schemas import (
    BlindSpotAnalysisResponse,
    FollowupResponse,
    InternalConflict,
    OverlookedFactor,
    UnstatedAssumption,
)
from app.services.cache_service import get_cache_service
from app.validators.verdict_validator import (
    generate_safe_neutral_analysis_fallback,
    generate_safe_neutral_followup_fallback,
    validate_analysis_payload,
    validate_followup_payload,
)

logger = logging.getLogger("blindspot.gemini_service")


class GeminiService:
    """Encapsulates all generative AI operations via Google GenAI SDK."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = settings.GEMINI_MAX_RETRIES
        self.initial_backoff = settings.GEMINI_INITIAL_BACKOFF_SECONDS
        self.cache = get_cache_service()
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initializes the official google-genai Client."""
        if self._client is None:
            if not self.api_key:
                logger.warning("GEMINI_API_KEY is not set. Real AI requests will fallback to safe responses.")
                return None
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google.genai Client: {e}")
                return None
        return self._client

    async def analyze_decision(
        self,
        request: IntakeRequest,
        session_id: str,
    ) -> BlindSpotAnalysisResponse:
        """
        Performs Socratic blind-spot analysis with retry backoff, caching, and verdict validation.
        """
        cache_key = self.cache._generate_key(
            "analysis",
            {
                "desc": request.decision_description,
                "drawing": request.drawing_factors,
                "options": request.options_considered,
                "deadline": request.deadline_or_stakes,
            },
        )

        cached_response = self.cache.get(cache_key)
        if cached_response:
            logger.info("Serving analysis from TTL cache.")
            cached_data = dict(cached_response)
            cached_data["session_id"] = session_id
            return BlindSpotAnalysisResponse(**cached_data)

        user_prompt = build_analysis_prompt(
            decision_description=request.decision_description,
            drawing_factors=request.drawing_factors,
            options_considered=request.options_considered,
            deadline_or_stakes=request.deadline_or_stakes,
        )

        # Call Gemini model
        raw_result = await self._call_gemini_with_retry(
            system_instruction=ANALYSIS_SYSTEM_PROMPT,
            prompt=user_prompt,
            response_schema=BlindSpotAnalysisResponse,
        )

        # Layer 2 Validator: Check for verdict or recommendation language
        parsed_data = None
        if raw_result:
            try:
                if isinstance(raw_result, str):
                    parsed_data = json.loads(raw_result)
                elif isinstance(raw_result, dict):
                    parsed_data = raw_result
            except Exception as parse_err:
                logger.warning(f"JSON parse error on initial generation: {parse_err}")

        # Check verdict violation
        is_violation, matched = validate_analysis_payload(parsed_data) if parsed_data else (True, ["Invalid output"])

        if is_violation and parsed_data:
            logger.warning(
                f"Verdict language detected in initial response: {matched}. Attempting single regeneration with safety instruction."
            )
            # Re-call once with explicit safety regeneration prompt
            regeneration_prompt = f"{user_prompt}\n\n{REGENERATION_SAFETY_INSTRUCTION}"
            regen_result = await self._call_gemini_with_retry(
                system_instruction=ANALYSIS_SYSTEM_PROMPT,
                prompt=regeneration_prompt,
                response_schema=BlindSpotAnalysisResponse,
            )
            if regen_result:
                try:
                    if isinstance(regen_result, str):
                        parsed_data = json.loads(regen_result)
                    elif isinstance(regen_result, dict):
                        parsed_data = regen_result
                    is_violation, _ = validate_analysis_payload(parsed_data)
                except Exception:
                    is_violation = True

        if is_violation or not parsed_data:
            logger.info("Using safe neutral fallback analysis response.")
            response = generate_safe_neutral_analysis_fallback(
                decision_description=request.decision_description,
                drawing_factors=request.drawing_factors,
                session_id=session_id,
                options_considered=request.options_considered,
            )
        else:
            # Build Pydantic response
            try:
                response = BlindSpotAnalysisResponse(
                    session_id=session_id,
                    what_you_emphasized=parsed_data.get("what_you_emphasized", []),
                    overlooked_factors=[
                        OverlookedFactor(**f) if isinstance(f, dict) else OverlookedFactor(factor=str(f), why_it_matters="")
                        for f in parsed_data.get("overlooked_factors", [])
                    ],
                    unstated_assumptions=[
                        UnstatedAssumption(**a) if isinstance(a, dict) else UnstatedAssumption(assumption=str(a), how_to_test="")
                        for a in parsed_data.get("unstated_assumptions", [])
                    ],
                    internal_conflicts=[
                        InternalConflict(**c) if isinstance(c, dict) else InternalConflict(conflict_description=str(c), user_quotes=[])
                        for c in parsed_data.get("internal_conflicts", [])
                    ],
                    other_perspective=parsed_data.get("other_perspective", ""),
                    probing_questions=parsed_data.get("probing_questions", []),
                    disclaimer=get_settings().DISCLAIMER_NOTE,
                )
            except Exception as build_err:
                logger.error(f"Error constructing response model: {build_err}. Falling back to safe response.")
                response = generate_safe_neutral_analysis_fallback(
                    decision_description=request.decision_description,
                    drawing_factors=request.drawing_factors,
                    session_id=session_id,
                    options_considered=request.options_considered,
                )

        # Cache successful analysis
        self.cache.set(cache_key, response.model_dump())
        return response

    async def reflect_followup(
        self,
        request: FollowupRequest,
        session_context_summary: str,
        reflection_history: list | None = None,
        reflection_step: int = 1,
    ) -> FollowupResponse:
        """
        Processes a Socratic reflection follow-up response and produces deeper inquiries.
        """
        user_prompt = build_followup_prompt(
            original_context_summary=session_context_summary,
            question=request.question,
            user_answer=request.user_answer,
            reflection_history=reflection_history,
        )

        raw_result = await self._call_gemini_with_retry(
            system_instruction=FOLLOWUP_SYSTEM_PROMPT,
            prompt=user_prompt,
            response_schema=FollowupResponse,
        )

        parsed_data = None
        if raw_result:
            try:
                if isinstance(raw_result, str):
                    parsed_data = json.loads(raw_result)
                elif isinstance(raw_result, dict):
                    parsed_data = raw_result
            except Exception as e:
                logger.warning(f"Error parsing follow-up output: {e}")

        is_violation, _ = validate_followup_payload(parsed_data) if parsed_data else (True, ["Invalid output"])

        if is_violation or not parsed_data:
            return generate_safe_neutral_followup_fallback(
                session_id=request.session_id,
                user_answer=request.user_answer,
                reflection_step=reflection_step,
            )

        try:
            return FollowupResponse(
                session_id=request.session_id,
                user_answer_summary=parsed_data.get("user_answer_summary", f"Reflection on: {request.question}"),
                deeper_questions=parsed_data.get(
                    "deeper_questions",
                    ["What other assumptions underpin that reasoning?"],
                ),
                newly_exposed_blind_spots=parsed_data.get("newly_exposed_blind_spots", []),
                reflection_step=reflection_step,
            )
        except Exception:
            return generate_safe_neutral_followup_fallback(
                session_id=request.session_id,
                user_answer=request.user_answer,
                reflection_step=reflection_step,
            )

    async def _call_gemini_with_retry(
        self,
        system_instruction: str,
        prompt: str,
        response_schema: Any,
    ) -> str | None:
        """
        Invokes Gemini API asynchronously with timeout and exponential backoff retry.
        """
        client = self._get_client()
        if not client:
            return None

        for attempt in range(1, self.max_retries + 1):
            try:
                # Run synchronous client in async executor with timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._sync_generate,
                        client,
                        system_instruction,
                        prompt,
                    ),
                    timeout=self.timeout,
                )
                return result
            except TimeoutError:
                logger.warning(f"Gemini API timed out on attempt {attempt}/{self.max_retries}.")
            except Exception as exc:
                logger.warning(f"Gemini API error on attempt {attempt}/{self.max_retries}: {exc}")

            if attempt < self.max_retries:
                backoff_time = self.initial_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(backoff_time)

        logger.error("All Gemini API retry attempts exhausted.")
        return None

    def _sync_generate(
        self,
        client: Any,
        system_instruction: str,
        prompt: str,
    ) -> str:
        """Synchronous wrapper for google.genai generation."""
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            temperature=0.7,
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        return response.text


_gemini_service_instance: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    """Singleton getter for GeminiService."""
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
