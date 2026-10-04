"""
Follow-up reflection router: handles Socratic exploration steps.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.request_schemas import FollowupRequest
from app.schemas.response_schemas import FollowupResponse
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.session_service import SessionService, get_session_service
from app.validators.security import sanitize_text_input

logger = logging.getLogger("blindspot.routers.followup")

router = APIRouter(prefix="/api", tags=["Reflection Loop"])


@router.post(
    "/followup",
    response_model=FollowupResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit reflection on a Socratic question to deepen inquiry",
)
async def followup_reflection_endpoint(
    request: FollowupRequest,
    req: Request,
    gemini_service: GeminiService = Depends(get_gemini_service),
    session_service: SessionService = Depends(get_session_service),
) -> FollowupResponse:
    """
    Submits user reflection for a probing question. Returns 1-3 deeper questions
    and newly exposed blind spots. Keeps session history server-side with size cap.
    """
    try:
        sanitized_question = sanitize_text_input(request.question, max_length=1000)
        sanitized_answer = sanitize_text_input(request.user_answer, max_length=3000)

        cleaned_request = FollowupRequest(
            session_id=request.session_id.strip(),
            question=sanitized_question,
            user_answer=sanitized_answer,
        )

        session = session_service.get_session(cleaned_request.session_id)
        context_summary = ""
        reflection_history = []
        step_number = 1

        if session:
            intake = session.get("intake_data", {})
            context_summary = (
                f"Decision: {intake.get('decision_description', '')}\n"
                f"Drawing Factors: {intake.get('drawing_factors', '')}"
            )
            reflection_history = session.get("reflection_steps", [])
            step_number = len(reflection_history) + 1
        else:
            context_summary = f"Reflecting on query: {cleaned_request.question}"

        # Get follow-up response from Gemini
        response = await gemini_service.reflect_followup(
            request=cleaned_request,
            session_context_summary=context_summary,
            reflection_history=reflection_history,
            reflection_step=step_number,
        )

        # Record step in session service
        session_service.add_reflection_step(
            session_id=cleaned_request.session_id,
            question=cleaned_request.question,
            user_answer=cleaned_request.user_answer,
            response_data=response.model_dump(),
        )

        return response

    except ValueError as ve:
        logger.warning(f"Validation error in follow-up endpoint: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        ) from ve
    except Exception as exc:
        logger.error(f"Error in follow-up endpoint: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your reflection follow-up.",
        ) from exc
